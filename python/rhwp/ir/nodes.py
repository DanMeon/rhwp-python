"""rhwp.ir.nodes — Document IR Pydantic 모델 (schema_version "1.0").

재귀 구조 (``TableCell.blocks`` → ``Block`` → ``TableBlock.cells`` → ``TableCell``)
는 문자열 전방 참조 + 파일 하단 ``model_rebuild()`` 로 해소한다.
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
    "DocumentSource",
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


CURRENT_SCHEMA_VERSION: Final = "1.0"
_SCHEMA_VERSION_PATTERN: Final = r"^\d+\.\d+(\.\d+)?$"

SchemaVersion = Annotated[
    str,
    StringConstraints(pattern=_SCHEMA_VERSION_PATTERN, strict=True),
]


class Provenance(BaseModel):
    """블록의 원본 문서 내 위치. 다운스트림 청커가 원본을 역추적 가능하게 한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_idx: int
    para_idx: int
    char_start: int | None = Field(
        default=None,
        description=(
            "Start character index (Unicode codepoints, 0-indexed). "
            "Compatible with Python str slicing: text[char_start:char_end]."
        ),
    )
    char_end: int | None = Field(
        default=None,
        description="End character index (Unicode codepoints, 0-indexed, exclusive).",
    )
    page_range: tuple[int, int] | None = Field(
        default=None,
        description=(
            "Inclusive (start_page, end_page). 렌더 단계에서만 계산되므로 파싱 경로는 None 을 출고한다."
        ),
    )


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
    href: str | None = None
    ruby: str | None = None
    raw_style_id: int | None = Field(
        default=None,
        description=(
            "Upstream doc_info 스타일 인덱스. 폰트/크기/색상 등 non-binary 서식을 escape 한다. "
            "None 은 char_shape 레코드가 없는 손상/비정상 입력 방어 경로 — "
            "정상 HWP 는 모든 런이 char_shape 에 대응되어 항상 값이 채워진다."
        ),
    )


class DocumentSource(BaseModel):
    """문서 출처 — RAG 응답 역추적 시 "이 답이 어느 파일에서 나왔나" 에 응답한다.

    스키마는 ``uri`` 형식을 강제하지 않으므로 소비자가 file://, https://, 혹은
    ``mem://{hash}`` 같은 custom 스킴으로 정규화할 수 있다. 향후 ``format``,
    ``bytes_size``, ``sha256`` 등 재현성 필드는 기본값 있는 옵셔널로만 추가 —
    이 경로는 기존 JSON 과 MINOR 호환 유지.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    uri: str = Field(
        description=(
            "파일 시스템 경로, URL, 혹은 소비자 정의 식별자. "
            "RFC 3986 URI reference 로 해석 가능한 문자열이면 충분하다."
        ),
    )


class DocumentMetadata(BaseModel):
    """문서 레벨 메타데이터. 시각은 ISO 8601 문자열로 출고한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str | None = None
    author: str | None = None
    creation_time: str | None = None
    modification_time: str | None = None


class Section(BaseModel):
    """HWP 구역 식별자. 용지·단·헤더 레퍼런스 등 상세 속성은 향후 추가된다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_idx: int


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


class UnknownBlock(BaseModel):
    """Forward-compatibility catch-all.

    Pydantic V2 의 기본 string discriminator 는 미지의 ``kind`` 를 만나면
    ``union_tag_invalid`` 로 문서 전체 파싱을 거부한다. callable Discriminator
    로 미지 ``kind`` 를 본 variant 로 라우팅하여, 나중에 새로운 블록 타입이
    추가되어도 구 버전 소비자가 읽기-불가 상태가 되지 않게 한다.

    소비자는 ``case UnknownBlock(): skip`` 패턴을 사용한다. ``assert_never``
    패턴은 새 variant 추가 시 빌드가 깨지므로 **사용 금지**.
    """

    # ^ extra="allow" — 미지 variant 의 payload 를 보존해 소비자가 최소한 로그/raw 접근 가능
    model_config = ConfigDict(extra="allow", frozen=True)

    kind: str
    prov: Provenance


class TableCell(BaseModel):
    """표 셀. ``blocks`` 가 재귀 ``Block`` 리스트라 중첩 표를 자연 지원한다.

    ``role`` 어휘는 DocLayNet 파생. ``"layout"`` 은 구조 유지용 비의미 셀
    (병합된 빈 영역 등) — LLM 이 "데이터 없음이 아닌 레이아웃 요소" 로 인식하도록 태깅한다.
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
            "DocLayNet-derived cell role. Current producer maps HWP 'is_header' to "
            "'column_header' and tags merged-empty cells as 'layout'; 'row_header' "
            "is reserved for producers that can distinguish row vs column headers."
        ),
    )
    blocks: list["Block"] = Field(default_factory=list)


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
    caption: str | None = None
    prov: Provenance


_KNOWN_KINDS: Final = frozenset({"paragraph", "table"})


def _block_discriminator(v: Any) -> str:
    """dict/모델 어느 쪽에서도 ``kind`` 를 추출해 known/unknown 분기.

    새 블록 타입을 추가할 때는 ``_KNOWN_KINDS`` 에 등록하고 ``Block`` 유니온에
    ``Annotated[NewBlock, Tag("new")]`` 를 추가한다.
    """
    kind = v.get("kind") if isinstance(v, dict) else getattr(v, "kind", None)
    return kind if kind in _KNOWN_KINDS else "unknown"


Block = Annotated[
    Annotated[ParagraphBlock, Tag("paragraph")]
    | Annotated[TableBlock, Tag("table")]
    | Annotated[UnknownBlock, Tag("unknown")],
    Discriminator(_block_discriminator),
]


class Furniture(BaseModel):
    """장식 노드 컨테이너 — RAG 가 임베딩에서 필터링 가능.

    현재 파서는 본문 블록을 넣지 않으므로 세 리스트는 기본적으로 비어있다.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    page_headers: list["Block"] = Field(default_factory=list)
    page_footers: list["Block"] = Field(default_factory=list)
    footnotes: list["Block"] = Field(default_factory=list)


class HwpDocument(BaseModel):
    """Document IR 루트.

    ``schema_name`` / ``schema_version`` 으로 인스턴스 자기-기술. body 와
    furniture 를 분리해 RAG 가 장식 노드를 필터링할 수 있다.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_name: Annotated[str, StringConstraints(pattern=r"^HwpDocument$")] = "HwpDocument"
    schema_version: SchemaVersion = CURRENT_SCHEMA_VERSION
    source: DocumentSource | None = None
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    sections: list[Section] = Field(default_factory=list)
    body: list["Block"] = Field(default_factory=list)
    furniture: Furniture = Field(default_factory=Furniture)

    @field_validator("schema_version")
    @classmethod
    def _warn_forward_version(cls, v: str) -> str:
        """major 상향 시 UserWarning — 외부 파일 읽기 경계는 forward-compat 을 위해 완화한다."""
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
        """블록을 순서대로 스트리밍한다.

        Args:
            scope: 순회 대상.

                - ``"body"`` (기본, RAG-safe): 본문 블록만
                - ``"furniture"``: 머리글 → 꼬리말 → 각주 순
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


# 재귀 유니온 (Block ↔ TableCell ↔ TableBlock) forward reference 해소
TableCell.model_rebuild()
Furniture.model_rebuild()
HwpDocument.model_rebuild()
