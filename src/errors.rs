use pyo3::exceptions::{PyFileNotFoundError, PyIOError, PyPermissionError, PyValueError};
use pyo3::PyErr;
use std::io::ErrorKind;

pub enum ParseError {
    Io(std::io::Error),
    Parse(String),
}

pub fn parse_error_to_py(e: ParseError) -> PyErr {
    match e {
        ParseError::Io(err) => {
            // ^ ErrorKind 기반 분기 — OS 별 메시지 차이에 의존하지 않도록 예외 계층 보존
            let msg = err.to_string();
            match err.kind() {
                ErrorKind::NotFound => PyFileNotFoundError::new_err(msg),
                ErrorKind::PermissionDenied => PyPermissionError::new_err(msg),
                _ => PyIOError::new_err(msg),
            }
        }
        ParseError::Parse(msg) => PyValueError::new_err(format!("parse failed: {msg}")),
    }
}
