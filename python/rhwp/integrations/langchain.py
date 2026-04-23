"""LangChain DocumentLoader — HWP / HWPX 를 Document 리스트로 로딩.

설치:
    pip install rhwp[langchain]

사용:
    from rhwp.integrations.langchain import HwpLoader

    loader = HwpLoader("report.hwp", mode="paragraph")
    docs = loader.load()
"""

from collections.abc import Iterator
from typing import Literal

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

import rhwp

LoadMode = Literal["single", "paragraph"]


class HwpLoader(BaseLoader):
    """HWP / HWPX 파일을 LangChain Document 리스트로 로딩.

    Args:
        path: HWP5 또는 HWPX 파일 경로.
        mode: 로딩 전략.
            - ``"single"``    : 전체 문서를 단일 Document 로 (기본)
            - ``"paragraph"`` : 문단별 Document (RAG 청킹에 유용)

    Raises:
        ValueError: ``mode`` 값이 유효하지 않거나, 파일 포맷이 유효하지 않을 때
            (``.load()`` 호출 시).
        FileNotFoundError: 파일이 존재하지 않을 때 (``.load()`` 호출 시).
        OSError: 그 외 I/O 오류 (``.load()`` 호출 시).
    """

    def __init__(self, path: str, *, mode: LoadMode = "single") -> None:
        if mode not in ("single", "paragraph"):
            raise ValueError(f"mode 는 'single' 또는 'paragraph' 여야 합니다: {mode!r}")
        self.path = path
        self.mode: LoadMode = mode

    def load(self) -> list[Document]:
        # ^ lazy_load 를 전량 수집 — 결과 list 제공이 필요한 호출자용
        return list(self.lazy_load())

    def lazy_load(self) -> Iterator[Document]:
        """문서를 파싱한 뒤 Document 객체를 순차 yield.

        파싱 자체는 ``rhwp.parse()`` 특성상 한 번에 완료되지만, Document 객체
        생성은 지연된다. ``paragraph`` 모드에서 전체 문단 리스트를 메모리에
        쌓지 않고 벡터DB 색인 등 스트리밍 소비자에게 바로 전달 가능.
        """
        doc = rhwp.parse(self.path)
        base_metadata = {
            "source": self.path,
            "section_count": doc.section_count,
            "paragraph_count": doc.paragraph_count,
            "page_count": doc.page_count,
            "rhwp_version": rhwp.rhwp_core_version(),
        }

        if self.mode == "single":
            yield Document(
                page_content=doc.extract_text(),
                metadata=base_metadata,
            )
            return

        # * paragraph 모드 — 빈 문단 제외 + 원본 인덱스 보존하며 lazy yield
        for idx, para in enumerate(doc.paragraphs()):
            if para.strip():
                yield Document(
                    page_content=para,
                    metadata={**base_metadata, "paragraph_index": idx},
                )
