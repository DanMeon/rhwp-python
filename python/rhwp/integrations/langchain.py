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

async 사용은 :meth:`aload` / :meth:`alazy_load` — 내부적으로 :func:`rhwp.aparse`
(aiofiles 기반 파일 I/O) 를 호출하므로 ``pip install rhwp[async]`` 필요.
"""

from collections.abc import AsyncIterator, Iterator
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
        ValueError: ``mode`` 값이 유효하지 않거나, 파일 포맷이 유효하지 않을 때.
        FileNotFoundError: 파일이 존재하지 않을 때.
        OSError: 그 외 I/O 오류.
        ImportError: async 변형 사용 시 ``aiofiles`` 미설치.
    """

    def __init__(self, path: str, *, mode: LoadMode = "single") -> None:
        if mode not in ("single", "paragraph", "ir-blocks"):
            raise ValueError(
                f"mode 는 'single' / 'paragraph' / 'ir-blocks' 중 하나여야 합니다: {mode!r}"
            )
        self.path = path
        self.mode: LoadMode = mode

    # * Sync

    def load(self) -> list[Document]:
        # ^ lazy_load 를 전량 수집 — 결과 list 제공이 필요한 호출자용
        return list(self.lazy_load())

    def lazy_load(self) -> Iterator[Document]:
        """문서를 파싱한 뒤 Document 객체를 순차 yield.

        파싱 자체는 ``rhwp.parse()`` 특성상 한 번에 완료되지만, Document 객체
        생성은 지연된다. ``paragraph`` / ``ir-blocks`` 모드에서 전체 블록 리스트를
        메모리에 쌓지 않고 벡터DB 색인 등 스트리밍 소비자에게 바로 전달 가능.
        """
        yield from self._yield_documents(rhwp.parse(self.path))

    # * Async — rhwp.aparse (aiofiles 기반) 로 파일 I/O 만 async, 이후 yield 는 sync.
    #   Rust _Document 가 unsendable 이라 threadpool 오프로드 (to_thread) 는 panic —
    #   대신 event loop 스레드에서 Document 를 생성하여 같은 스레드 에서 소비한다.

    async def aload(self) -> list[Document]:
        """:meth:`load` 의 async 변형. ``aiofiles`` 로 파일 읽기만 async 처리."""
        return [doc async for doc in self.alazy_load()]

    async def alazy_load(self) -> AsyncIterator[Document]:
        """:meth:`lazy_load` 의 async 변형.

        파일 I/O 는 ``rhwp.aparse`` 가 aiofiles 로 async 처리, 이후 블록 순회는
        event loop 스레드에서 sync 실행 — 각 yield 사이에서 event loop 에 제어
        반환 (async for 는 자동으로 checkpoint 를 제공).
        """
        rhwp_doc = await rhwp.aparse(self.path)
        for doc in self._yield_documents(rhwp_doc):
            yield doc

    # * 공통 yield 로직 — sync/async 양쪽에서 공유

    def _yield_documents(self, rhwp_doc: rhwp.Document) -> Iterator[Document]:
        """이미 파싱된 rhwp.Document 에서 mode 별 LangChain Document 를 yield."""
        base_metadata = {
            "source": self.path,
            "section_count": rhwp_doc.section_count,
            "paragraph_count": rhwp_doc.paragraph_count,
            "page_count": rhwp_doc.page_count,
            "rhwp_version": rhwp.rhwp_core_version(),
        }

        if self.mode == "single":
            yield Document(
                page_content=rhwp_doc.extract_text(),
                metadata=base_metadata,
            )
            return

        if self.mode == "paragraph":
            # * paragraph 모드 — 빈 문단 제외 + 원본 인덱스 보존
            for idx, para in enumerate(rhwp_doc.paragraphs()):
                if para.strip():
                    yield Document(
                        page_content=para,
                        metadata={**base_metadata, "paragraph_index": idx},
                    )
            return

        # * ir-blocks 모드 — Document IR Block 을 LangChain Document 로 매핑
        ir = rhwp_doc.to_ir()
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
        # ^ HTML 을 page_content 로 — LLM 에 구조 정보 제공. 검색 색인용 평문은 메타로 노출
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
