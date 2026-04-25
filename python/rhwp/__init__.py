"""rhwp — HWP/HWPX parser and renderer (Korean word processor format)."""

from rhwp._rhwp import rhwp_core_version, version
from rhwp.document import Document, aparse, parse

__all__ = [
    "Document",
    "aparse",
    "parse",
    "rhwp_core_version",
    "version",
]
