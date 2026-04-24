"""HwpLoader 타입 스텁 — ``rhwp[langchain]`` extras."""

from collections.abc import Iterator
from typing import Literal

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

LoadMode = Literal["single", "paragraph", "ir-blocks"]

class HwpLoader(BaseLoader):
    path: str
    mode: LoadMode

    def __init__(self, path: str, *, mode: LoadMode = "single") -> None: ...
    def load(self) -> list[Document]: ...
    def lazy_load(self) -> Iterator[Document]: ...
