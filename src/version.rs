use pyo3::prelude::*;

#[pyfunction]
pub fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[pyfunction]
pub fn rhwp_core_version() -> String {
    rhwp::version()
}
