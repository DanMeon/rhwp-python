use std::cell::OnceCell;

use pyo3::exceptions::{PyIOError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};

use crate::errors::{parse_error_to_py, ParseError};
use crate::ir;

// ^ unsendable: DocumentCore 내부 RefCell 필드로 !Sync — 다른 스레드 접근 시 런타임 패닉 방어
#[pyclass(name = "Document", module = "rhwp", unsendable)]
pub struct PyDocument {
    pub(crate) inner: rhwp::document_core::DocumentCore,
    // ^ 첫 to_ir() 호출 시 1회 구성, 이후 재사용. unsendable 덕에 lock 불필요 (ir.md §7)
    ir_cache: OnceCell<Py<PyAny>>,
}

fn load_document(path: String) -> Result<rhwp::document_core::DocumentCore, ParseError> {
    let bytes = std::fs::read(&path).map_err(ParseError::Io)?;
    rhwp::document_core::DocumentCore::from_bytes(&bytes)
        .map_err(|e| ParseError::Parse(format!("{e:?}")))
}

#[pymethods]
impl PyDocument {
    #[new]
    fn new(py: Python<'_>, path: &str) -> PyResult<Self> {
        // ^ py.detach 로 파일 I/O + 파싱 동안 GIL 해제 (DocumentCore 는 클로저 내부에서만 생성)
        let path_owned = path.to_owned();
        let doc = py
            .detach(move || load_document(path_owned))
            .map_err(parse_error_to_py)?;
        Ok(PyDocument {
            inner: doc,
            ir_cache: OnceCell::new(),
        })
    }

    #[getter]
    fn section_count(&self) -> usize {
        self.inner.document().sections.len()
    }

    #[getter]
    fn paragraph_count(&self) -> usize {
        self.inner
            .document()
            .sections
            .iter()
            .map(|s| s.paragraphs.len())
            .sum()
    }

    #[getter]
    fn page_count(&self) -> u32 {
        self.inner.page_count()
    }

    fn extract_text(&self) -> String {
        self.inner
            .document()
            .sections
            .iter()
            .flat_map(|s| s.paragraphs.iter())
            .map(|p| p.text.as_str())
            .filter(|t| !t.is_empty())
            .collect::<Vec<_>>()
            .join("\n")
    }

    fn paragraphs(&self) -> Vec<String> {
        self.inner
            .document()
            .sections
            .iter()
            .flat_map(|s| s.paragraphs.iter())
            .map(|p| p.text.clone())
            .collect()
    }

    fn render_svg(&self, page: u32) -> PyResult<String> {
        self.inner
            .render_page_svg_native(page)
            .map_err(|e| PyValueError::new_err(format!("render page {page} failed: {e:?}")))
    }

    fn render_all_svg(&self) -> PyResult<Vec<String>> {
        self.render_all_svg_internal()
    }

    #[pyo3(signature = (output_dir, prefix=None))]
    fn export_svg(&self, output_dir: &str, prefix: Option<&str>) -> PyResult<Vec<String>> {
        let out_dir = std::path::Path::new(output_dir);
        std::fs::create_dir_all(out_dir).map_err(|e| PyIOError::new_err(e.to_string()))?;

        let page_count = self.inner.page_count();
        let stem = prefix.unwrap_or("page");
        let mut written = Vec::with_capacity(page_count as usize);
        for page in 0..page_count {
            let svg = self
                .inner
                .render_page_svg_native(page)
                .map_err(|e| PyValueError::new_err(format!("render page {page} failed: {e:?}")))?;
            let filename = if page_count == 1 {
                format!("{stem}.svg")
            } else {
                format!("{stem}_{:03}.svg", page + 1)
            };
            let path = out_dir.join(&filename);
            std::fs::write(&path, &svg).map_err(|e| PyIOError::new_err(e.to_string()))?;
            written.push(path.to_string_lossy().into_owned());
        }
        Ok(written)
    }

    fn render_pdf<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        // ^ SVG 렌더링은 GIL 유지 (&self.inner 필요). PDF 변환만 py.detach 로 GIL 해제 —
        //   소유권 있는 Vec<String> 전달로 !Sync/!Send 경계 회피 (가이드 §12.3)
        let svgs = self.render_all_svg_internal()?;
        let bytes = py
            .detach(move || rhwp::renderer::pdf::svgs_to_pdf(&svgs))
            .map_err(|e| PyValueError::new_err(format!("PDF conversion failed: {e}")))?;
        Ok(PyBytes::new(py, &bytes))
    }

    fn export_pdf(&self, py: Python<'_>, output_path: &str) -> PyResult<usize> {
        let svgs = self.render_all_svg_internal()?;
        let output_path = output_path.to_owned();
        py.detach(move || -> PyResult<usize> {
            let bytes = rhwp::renderer::pdf::svgs_to_pdf(&svgs)
                .map_err(|e| PyValueError::new_err(format!("PDF conversion failed: {e}")))?;
            std::fs::write(&output_path, &bytes).map_err(|e| PyIOError::new_err(e.to_string()))?;
            Ok(bytes.len())
        })
    }

    /// 문서를 Document IR (Pydantic `HwpDocument`) 로 변환하여 반환한다.
    ///
    /// 첫 호출 시 문서 트리를 순회하며 IR 을 구성하고 결과를 인스턴스에 캐시한다.
    /// 재호출은 캐시된 객체를 반환. IR 모델은 `frozen=True` 이므로 반환 객체 수정
    /// 시 Pydantic `ValidationError` 가 발생한다. 독립 사본이 필요하면
    /// `ir.model_copy(deep=True)` 를 사용한다.
    fn to_ir(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        // ^ OnceCell::get_or_try_init 은 nightly-only — 수동 get/set 으로 대체.
        //   unsendable → 단일 스레드 접근이라 get() → set() 사이 경쟁 없음
        if let Some(cached) = self.ir_cache.get() {
            return Ok(cached.clone_ref(py));
        }
        let ir = ir::build_hwp_document(py, self.inner.document())?;
        self.ir_cache
            .set(ir)
            .expect("ir_cache was empty just above");
        Ok(self
            .ir_cache
            .get()
            .expect("ir_cache was just set")
            .clone_ref(py))
    }

    /// IR 을 JSON 문자열로 반환한다. `to_ir()` 캐시를 공유한다.
    ///
    /// `indent` 를 주면 Pydantic `model_dump_json(indent=...)` 으로 들여쓰기.
    #[pyo3(signature = (*, indent = None))]
    fn to_ir_json(&self, py: Python<'_>, indent: Option<usize>) -> PyResult<String> {
        let ir_obj = self.to_ir(py)?;
        let bound = ir_obj.bind(py);
        let kwargs = PyDict::new(py);
        if let Some(n) = indent {
            kwargs.set_item("indent", n)?;
        }
        let result = bound.call_method("model_dump_json", (), Some(&kwargs))?;
        result.extract::<String>()
    }

    fn __repr__(&self) -> String {
        format!(
            "Document(sections={}, paragraphs={}, pages={})",
            self.section_count(),
            self.paragraph_count(),
            self.page_count()
        )
    }
}

// * Python 에 노출되지 않는 내부 헬퍼
impl PyDocument {
    fn render_all_svg_internal(&self) -> PyResult<Vec<String>> {
        let page_count = self.inner.page_count();
        (0..page_count)
            .map(|p| {
                self.inner
                    .render_page_svg_native(p)
                    .map_err(|e| PyValueError::new_err(format!("render page {p} failed: {e:?}")))
            })
            .collect()
    }
}

#[pyfunction]
pub fn parse(py: Python<'_>, path: &str) -> PyResult<PyDocument> {
    PyDocument::new(py, path)
}
