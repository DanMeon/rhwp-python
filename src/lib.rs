use pyo3::prelude::*;

mod document;
mod errors;
mod ir;
mod version;

use document::PyDocument;

// ^ gil_used = true: DocumentCore 내부 RefCell 캐시가 !Sync 이므로 free-threaded Python 비활성
#[pymodule(gil_used = true)]
fn _rhwp(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version::version, m)?)?;
    m.add_function(wrap_pyfunction!(version::rhwp_core_version, m)?)?;
    m.add_function(wrap_pyfunction!(document::parse, m)?)?;
    m.add_class::<PyDocument>()?;
    Ok(())
}
