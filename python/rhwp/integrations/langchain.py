"""LangChain DocumentLoader — HWP / HWPX 를 Document 리스트로 로딩.

설치:
    pip install rhwp[langchain]

사용:
    from rhwp.integrations.langchain import HwpLoader

    # 기본 — 전체 문서 하나로
    HwpLoader("report.hwp", mode="single").load()

    # 문단 단위 — 기본 텍스트만
    HwpLoader("report.hwp", mode="paragraph").load()

    # IR 블록 단위 — 구조화 정보 포함 (표/단락 혼합, Provenance 메타데이터)
    HwpLoader("report.hwp", mode="ir-blocks").load()
"""

from collections.abc import Iterator
from typing import Any, Literal

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

import rhwp
from rhwp.ir.nodes import Block, ParagraphBlock, TableBlock, UnknownBlock

LoadMode = Literal["single", "paragraph", "ir-blocks"]


class HwpLoader(BaseLoader):
    """HWP / HWPX 파일을 LangChain Document 리스트로 로딩.

    Args:
        path: HWP5 또는 HWPX 파일 경로.
        mode: 로딩 전략.
            - ``"single"``   : 전체 문서를 단일 Document 로 (기본)
            - ``"paragraph"``: 문단 텍스트별 Document (RAG 청킹용)
            - ``"ir-blocks"``: Document IR 의 Block 단위 — 표 구조 보존 + Provenance 메타데이터

    Raises:
        ValueError: ``mode`` 값이 유효하지 않거나, 파일 포맷이 유효하지 않을 때
            (``.load()`` 호출 시).
        FileNotFoundError: 파일이 존재하지 않을 때 (``.load()`` 호출 시).
        OSError: 그 외 I/O 오류 (``.load()`` 호출 시).
    """

    def __init__(self, path: str, *, mode: LoadMode = "single") -> None:
        if mode not in ("single", "paragraph", "ir-blocks"):
            raise ValueError(
                f"mode 는 'single' / 'paragraph' / 'ir-blocks' 중 하나여야 합니다: {mode!r}"
            )
        self.path = path
        self.mode: LoadMode = mode

    def load(self) -> list[Document]:
        # ^ lazy_load 를 전량 수집 — 결과 list 제공이 필요한 호출자용
        return list(self.lazy_load())

    def lazy_load(self) -> Iterator[Document]:
        """문서를 파싱한 뒤 Document 객체를 순차 yield.

        파싱 자체는 ``rhwp.parse()`` 특성상 한 번에 완료되지만, Document 객체
        생성은 지연된다. ``paragraph`` / ``ir-blocks`` 모드에서 전체 블록 리스트를
        메모리에 쌓지 않고 벡터DB 색인 등 스트리밍 소비자에게 바로 전달 가능.
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

        if self.mode == "paragraph":
            # * paragraph 모드 — 빈 문단 제외 + 원본 인덱스 보존
            for idx, para in enumerate(doc.paragraphs()):
                if para.strip():
                    yield Document(
                        page_content=para,
                        metadata={**base_metadata, "paragraph_index": idx},
                    )
            return

        # * ir-blocks 모드 — Document IR Block 을 LangChain Document 로 매핑
        ir = doc.to_ir()
        for block in ir.iter_blocks(scope="body", recurse=True):
            content, extra_meta = _block_to_content_and_meta(block)
            if not content.strip():
                # ^ 공백만 있는 블록도 RAG 노이즈이므로 제외
                continue
            yield Document(
                page_content=content,
                metadata={**base_metadata, **extra_meta},
            )


def _block_to_content_and_meta(block: Block) -> tuple[str, dict[str, Any]]:
    """Block → (page_content, block-specific metadata)."""
    if isinstance(block, ParagraphBlock):
        return block.text, {
            "kind": "paragraph",
            "section_idx": block.prov.section_idx,
            "para_idx": block.prov.para_idx,
            "char_start": block.prov.char_start,
            "char_end": block.prov.char_end,
        }
    if isinstance(block, TableBlock):
        # ^ HtmlRAG 전략 — LLM 에는 HTML, 검색 색인에는 text 가 들어가도록 둘 다 메타에 노출
        return block.html, {
            "kind": "table",
            "section_idx": block.prov.section_idx,
            "para_idx": block.prov.para_idx,
            "rows": block.rows,
            "cols": block.cols,
            "text": block.text,
            "caption": block.caption,
        }
    # 새 Block variant 가 추가되면 그 variant 의 elif 를 이 assert 보다 위에 먼저
    # 추가해야 한다. 그러지 않으면 AssertionError 로 fail-fast (silent fallback 방지)
    assert isinstance(block, UnknownBlock)
    return "", {
        "kind": block.kind,
        "section_idx": block.prov.section_idx,
        "para_idx": block.prov.para_idx,
    }
