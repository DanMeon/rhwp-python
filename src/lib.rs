use pyo3::prelude::*;

mod document;
mod errors;
mod ir;
mod version;

use document::PyDocument;

// ^ gil_used = true: DocumentCore 내부 RefCell 캐시가 !Sync 이므로 free-threaded Python 비활성
// ^ parse() 는 Python 레이어 (rhwp/__init__.py) 에서 재구현 — Rust 는 `_Document` 클래스만
//   노출하고 construction/wrapping 책임은 Python wrapper 가 담당한다
#[pymodule(gil_used = true)]
fn _rhwp(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version::version, m)?)?;
    m.add_function(wrap_pyfunction!(version::rhwp_core_version, m)?)?;
    m.add_class::<PyDocument>()?;
    Ok(())
}
