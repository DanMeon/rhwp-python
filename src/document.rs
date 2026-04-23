use pyo3::exceptions::{PyIOError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

use crate::errors::{parse_error_to_py, ParseError};

// ^ unsendable: DocumentCore 내부 RefCell 필드로 !Sync — 다른 스레드 접근 시 런타임 패닉 방어
#[pyclass(name = "Document", module = "rhwp", unsendable)]
pub struct PyDocument {
    pub(crate) inner: rhwp::document_core::DocumentCore,
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
        Ok(PyDocument { inner: doc })
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
