"""rhwp.ir.nodes — Document IR v1 Pydantic 모델 (schema_version "1.0").

v0.2.0 Stage S1: 공개 데이터 모델만 정의한다. Rust 바인딩 (``Document.to_ir()``)
은 S2, JSON Schema export 는 S4 에서 추가한다.

재귀 구조 (``TableCell.blocks`` → ``Block`` → ``TableBlock.cells`` → ``TableCell``)
는 문자열 전방 참조 + 파일 하단 ``model_rebuild()`` 로 해소한다.

설계 근거: ``docs/roadmap/v0.2.0/ir.md`` + ``docs/design/v0.2.0/ir-design-research.md``.
"""

import warnings
from collections.abc import Iterator
from typing import Annotated, Any, Final, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    StringConstraints,
    Tag,
    field_validator,
)

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "Block",
    "DocumentMetadata",
    "Furniture",
    "HwpDocument",
    "InlineRun",
    "ParagraphBlock",
    "Provenance",
    "SchemaVersion",
    "Section",
    "TableBlock",
    "TableCell",
    "UnknownBlock",
]


# * 스키마 버전 — Annotated[str, StringConstraints] (ir.md §4)
CURRENT_SCHEMA_VERSION: Final = "1.0"
_SCHEMA_VERSION_PATTERN: Final = r"^\d+\.\d+(\.\d+)?$"

SchemaVersion = Annotated[
    str,
    StringConstraints(pattern=_SCHEMA_VERSION_PATTERN, strict=True),
]


# * Provenance — 원본 위치 추적 (codepoint 기반, ir.md §3)
class Provenance(BaseModel):
    """블록의 원본 문서 내 위치. 다운스트림 청커가 원본을 역추적 가능하게 한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_idx: int
    para_idx: int
    char_start: Optional[int] = Field(
        default=None,
        description=(
            "Start character index (Unicode codepoints, 0-indexed). "
            "Compatible with Python str slicing: text[char_start:char_end]."
        ),
    )
    char_end: Optional[int] = Field(
        default=None,
        description="End character index (Unicode codepoints, 0-indexed, exclusive).",
    )
    page_range: Optional[tuple[int, int]] = Field(
        default=None,
        description=(
            "Inclusive (start_page, end_page). v0.2.0 은 None 출고 — "
            "페이지 경계는 상류 코어의 렌더 단계에서만 계산된다."
        ),
    )


# * InlineRun — 단락 내 서식이 동일한 연속 텍스트 런 (ir.md §단락 내 InlineRun)
class InlineRun(BaseModel):
    """서식이 동일한 연속 문자 런.

    bold/italic/underline/strikethrough/href/ruby 외의 서식 속성 (폰트, 크기,
    색상 등) 은 ``raw_style_id`` 로 escape 된다 — 상류 ``doc_info`` 스타일 인덱스.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    href: Optional[str] = None
    ruby: Optional[str] = None
    raw_style_id: Optional[int] = None


# * DocumentMetadata — 문서 레벨 메타데이터
class DocumentMetadata(BaseModel):
    """문서 레벨 메타데이터. v0.2.0 은 ``str | None`` 으로만 노출한다.

    ``creation_time`` / ``modification_time`` 은 S2 Rust 매퍼에서 ISO 8601
    문자열로 출고한다. v0.3.0 에서 ``datetime`` 타입 교체는 MINOR 호환
    (optional 필드 타입 확장) 범위 — 현 시점은 JSON 직렬화 친화성이 우선.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: Optional[str] = None
    author: Optional[str] = None
    creation_time: Optional[str] = None
    modification_time: Optional[str] = None


# * Section — HWP 구역 (v0.2.0 S1 은 식별자만)
class Section(BaseModel):
    """HWP 구역.

    v0.2.0 S1 은 ``section_idx`` 만 노출. 용지 크기·방향·단 수·머리글/꼬리말
    레퍼런스는 S2 Rust 매핑 시점에 MINOR 호환 확장으로 추가한다.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_idx: int


# * ParagraphBlock — 단락
class ParagraphBlock(BaseModel):
    """단락 블록. 서식 런 리스트 + 평탄 텍스트 파생 필드를 병기한다.

    ``text`` 는 ``inlines`` 의 ``text`` 필드를 이어붙인 결과 — LLM 에 넘기는
    평문화 경로. 원본 서식 보존이 필요한 소비자만 ``inlines`` 를 직접 순회한다.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["paragraph"] = "paragraph"
    text: str = ""
    inlines: list[InlineRun] = Field(default_factory=list)
    prov: Provenance


# * UnknownBlock — v1.0 부터 포함되는 catch-all (ir.md §1)
class UnknownBlock(BaseModel):
    """Forward-compatibility catch-all.

    Pydantic V2 string discriminator 는 미지의 ``kind`` 를 만나면
    ``union_tag_invalid`` 로 문서 전체 파싱을 거부한다. v0.3.0 에서 ``PictureBlock``
    등 새 variant 가 추가될 때 v0.2.0 소비자가 읽기-불가 상태가 되는 것을
    방지하기 위해 callable Discriminator 로 미지 ``kind`` 를 본 variant 로 라우팅.

    소비자는 ``case UnknownBlock(): skip`` 패턴을 사용한다. ``assert_never``
    패턴은 새 variant 추가 시 builds 가 깨지므로 **사용 금지**.
    """

    # ^ extra="allow" — 미지 variant 의 payload 를 보존해 소비자가 최소한 로그/raw 접근 가능
    model_config = ConfigDict(extra="allow", frozen=True)

    kind: str
    prov: Provenance


# * TableCell — 재귀 (blocks: list["Block"])
class TableCell(BaseModel):
    """표 셀. ``blocks`` 가 재귀 ``Block`` 리스트라 중첩 표를 자연 지원한다.

    ``role`` 어휘는 DocLayNet 파생 — ``"layout"`` 은 간격용 빈 셀 등 비의미 셀
    로 RAG 가 필터링할 수 있도록 한다 (ir.md §테이블 표현).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    grid_index: int = Field(
        description=(
            "Anchor cell position in row-major flat index (row * table.cols + col). "
            "Not a reverse-lookup key; span-covered positions do not appear as separate cells."
        ),
    )
    role: Literal["data", "column_header", "row_header", "layout"] = Field(
        default="data",
        description=(
            "DocLayNet-derived role vocabulary. HWP does not distinguish column vs row "
            "headers, so v0.2.0 maps is_header → 'column_header' and leaves 'row_header' / "
            "'layout' as valid enum values for producers that can identify them "
            "(e.g. future heuristics or user annotation layers)."
        ),
    )
    blocks: list["Block"] = Field(default_factory=list)


# * TableBlock — 이중 표현 (구조화 cells + HTML + text), ir.md §테이블 표현
class TableBlock(BaseModel):
    """표 블록. 단일 표현으로 RAG 품질 최대화 불가 → 3중 표현 병기.

    - ``cells`` : 프로그래매틱 접근 (SQL 생성, 셀 순회)
    - ``html``  : LLM 에 제공, rowspan/colspan 보존 (HtmlRAG 호환)
    - ``text``  : 단순 검색·diff 용 폴백 (행은 개행, 셀은 탭 구분)
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["table"] = "table"
    rows: int
    cols: int
    cells: list[TableCell] = Field(default_factory=list)
    html: str = ""
    text: str = ""
    # ^ v0.2.0 은 단순 텍스트 캡션만 — 복합 캡션 (캡션 안의 블록) 은 v0.3.0+ 이월
    caption: Optional[str] = None
    prov: Provenance


# * Block tagged union — callable Discriminator (ir.md §블록 태그드 유니온)
_KNOWN_KINDS: Final = frozenset({"paragraph", "table"})


def _block_discriminator(v: Any) -> str:
    """dict/모델 어느 쪽에서도 ``kind`` 를 추출해 known/unknown 분기.

    v0.3.0+ 에서 새 블록 추가 시 ``_KNOWN_KINDS`` 에 등록 + ``Block`` Union
    에 ``Annotated[NewBlock, Tag("new")]`` 를 추가하면 된다.
    """
    kind = v.get("kind") if isinstance(v, dict) else getattr(v, "kind", None)
    return kind if kind in _KNOWN_KINDS else "unknown"


Block = Annotated[
    Union[
        Annotated[ParagraphBlock, Tag("paragraph")],
        Annotated[TableBlock, Tag("table")],
        Annotated[UnknownBlock, Tag("unknown")],
    ],
    Discriminator(_block_discriminator),
]


# * Furniture — 장식 (머리글/꼬리말/각주), ir.md §타입 계층 개요
class Furniture(BaseModel):
    """장식 노드 컨테이너 — RAG 가 임베딩에서 필터링 가능.

    v0.2.0 S1 은 빈 리스트만 출고 — 머리글/꼬리말 **본문** 노드 파싱은 v0.3.0+.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    page_headers: list["Block"] = Field(default_factory=list)
    page_footers: list["Block"] = Field(default_factory=list)
    footnotes: list["Block"] = Field(default_factory=list)


# * HwpDocument — 문서 루트
class HwpDocument(BaseModel):
    """Document IR 루트.

    ``schema_name`` / ``schema_version`` 으로 인스턴스 자기-기술. body 와
    furniture 를 분리해 RAG 가 장식 노드를 필터링할 수 있다.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # ^ schema_name 은 항상 "HwpDocument" — Literal 대신 pattern 으로 ir.md 스펙 일관
    schema_name: Annotated[str, StringConstraints(pattern=r"^HwpDocument$")] = "HwpDocument"
    schema_version: SchemaVersion = CURRENT_SCHEMA_VERSION
    source: Optional[Provenance] = None
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    sections: list[Section] = Field(default_factory=list)
    body: list["Block"] = Field(default_factory=list)
    furniture: Furniture = Field(default_factory=Furniture)

    @field_validator("schema_version")
    @classmethod
    def _warn_forward_version(cls, v: str) -> str:
        """major 상향 시 UserWarning — reject 아님.

        외부 파일 읽기 경계는 CLAUDE.md "fail-fast only at external
        boundaries" 예외: forward-compat 을 위해 완화한다.
        """
        major = int(v.split(".")[0])
        current_major = int(CURRENT_SCHEMA_VERSION.split(".")[0])
        if major > current_major:
            warnings.warn(
                f"schema_version {v!r} is newer than supported "
                f"{CURRENT_SCHEMA_VERSION!r}. Some fields may be ignored. "
                f"Upgrade rhwp-python.",
                UserWarning,
                stacklevel=2,
            )
        return v

    def iter_blocks(
        self,
        *,
        scope: Literal["body", "furniture", "all"] = "body",
        recurse: bool = True,
    ) -> Iterator["Block"]:
        """블록을 순서대로 스트리밍한다 (ir.md §엔트리 포인트).

        Args:
            scope: 순회 대상.

                - ``"body"`` (기본, RAG-safe): 본문 블록만
                - ``"furniture"``: 머리글 / 꼬리말 / 각주만 (v0.2.0 은 빈 리스트)
                - ``"all"``: 본문 먼저, 이어서 장식
            recurse: True 면 ``TableCell.blocks`` 재귀 진입 (중첩 표 내부까지).

        구조 기반 작업에는 ``doc.body`` / ``doc.furniture`` 속성 직접 접근이
        더 간결하다. 본 메서드는 scope + recurse 조합이 필요한 경우용
        (예: ``sum(1 for b in doc.iter_blocks(scope="all") if isinstance(b, TableBlock))``).
        """
        if scope in ("body", "all"):
            yield from _walk_blocks(self.body, recurse)
        if scope in ("furniture", "all"):
            yield from _walk_blocks(self.furniture.page_headers, recurse)
            yield from _walk_blocks(self.furniture.page_footers, recurse)
            yield from _walk_blocks(self.furniture.footnotes, recurse)


def _walk_blocks(blocks: list["Block"], recurse: bool) -> Iterator["Block"]:
    """블록 리스트 DFS 순회 — recurse=True 면 TableCell.blocks 내부까지 진입."""
    for block in blocks:
        yield block
        if recurse and isinstance(block, TableBlock):
            for cell in block.cells:
                yield from _walk_blocks(cell.blocks, recurse)


# * Forward reference 해소 — 재귀 유니온 (Block ↔ TableCell ↔ TableBlock) 위해 필수
TableCell.model_rebuild()
Furniture.model_rebuild()
HwpDocument.model_rebuild()
