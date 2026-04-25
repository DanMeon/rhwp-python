"""rhwp — HWP/HWPX parser and renderer (Korean word processor format)."""

from rhwp.document import Document as Document
from rhwp.document import aparse as aparse
from rhwp.document import parse as parse

__all__ = [
    "Document",
    "aparse",
    "parse",
    "rhwp_core_version",
    "version",
]

def version() -> str:
    """rhwp Python 패키지 버전 (예: "0.1.0")."""
    ...

def rhwp_core_version() -> str:
    """rhwp Rust 코어 버전 (예: "0.7.3")."""
    ...
