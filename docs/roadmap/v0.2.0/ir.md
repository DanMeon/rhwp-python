# 0.2.0 — Document IR v1 (JSON 직렬화형 문서 모델)

**Status**: Frozen · **GA**: v0.2.0 · **Last updated**: 2026-04-25

`rhwp-python` 을 단순 텍스트 추출기에서 **RAG/LLM 파이프라인이 직접 소비 가능한 구조화 문서 라이브러리** 로 전환하는 첫 단계. Pydantic V2 기반 공개 데이터 모델과 JSON 스키마를 고정하고, Rust 코어가 보유한 구조 정보를 Python 사용자에게 타입-안전하게 노출한다.

## 방향 전환 배경 — CLI 계획의 폐기

v0.2.0 의 원안은 `rhwp` 커맨드라인 도구 제공이었으나(`docs/roadmap/v0.2.0/cli.md`, 제거됨), 업스트림 `edwardkim/rhwp` 의 Rust 크레이트가 **이미 동일 이름의 바이너리** 를 제공하고 있다.

업스트림 바이너리가 제공하는 서브커맨드(근거: `external/rhwp/src/main.rs`, `external/rhwp/CLAUDE.md`):

| 커맨드 | 용도 |
|---|---|
| `export-svg` | SVG 추출 (`--font-style`, `--embed-fonts`, `--debug-overlay` 등 풍부한 옵션) |
| `export-pdf` | PDF 추출 |
| `info` / `dump` / `dump-pages` | 메타데이터·조판부호·페이지 배치 덤프 |
| `diag` / `ir-diff` | 라운드트립 진단 (HWPX↔HWP IR 비교) |
| `convert` | 포맷 변환 |
| `thumbnail` | 썸네일 생성 |

`pip install rhwp-python` 이 동일한 `rhwp` 커맨드를 PATH 에 설치하면 **직접 충돌** 한다. 기능 중복 유지보수 부담에 더해, `parse`/`render` 계열은 네이티브 Rust 바이너리가 성능·일관성 면에서 항상 우위다. Python 쪽 고유 가치는 **LangChain/LlamaIndex/Haystack 통합** 과 **RAG-친화적 구조화 출력** 이며, 이것이 Document IR 의 본질적 영역이다.

따라서 v0.2.0 은 CLI 대신 IR 을 도입하고, CLI 는 영구 비범위는 아니되 **업스트림이 커버하지 않는 Python 고유 기능이 충분히 축적된 이후에만** 재검토한다(예: `rhwp-py chunks` — LangChain 청킹, `--json` 출력 등. 네임스페이스는 업스트림과 구분).

## 용어 정리 — 상류 IR 과의 구분

`IR` 이라는 용어는 상류 Rust 크레이트가 이미 사용한다. 혼동 방지를 위해 본 문서는 두 개념을 구분한다.

| 용어 | 범위 | 형태 | 소비자 |
|---|---|---|---|
| **Parser IR** (상류) | Rust `rhwp::model::*` — `Document`, `Section`, `Paragraph`, `Table` 등 파서 내부 타입 | 인메모리 Rust 값, 비직렬화 | 상류 내부 — 렌더러·`ir-diff` 라운드트립 검증 |
| **Document IR** (본 문서) | Python/JSON 으로 노출되는 **의미 계층 투영** | Pydantic V2 모델 + JSON Schema (Draft 2020-12) | Python 사용자 — RAG 파이프라인, LLM Structured Output, 인터체인지 |

본 문서의 "IR" 은 달리 명시되지 않는 한 **Document IR** 을 가리킨다. Document IR 은 Parser IR 의 상위 구조를 보존하되 파서 내부 식별자(예: `char_shape_id` 인덱스, 바이트 오프셋)를 해소하여 **자기-완결적** 으로 만든다.

## 목표와 비목표

### v0.2.0 목표 (최소 가용 RAG IR)

1. HWP/HWPX 문서의 **구역(Section) → 블록(Paragraph/Table) → 셀/런** 3-계층을 Pydantic 모델로 노출
2. 표는 `rowspan`/`colspan`/중첩을 손실 없이 보존 (셀 배열 + HTML 직렬화 **양쪽** 제공)
3. 단락 내 서식 런(bold/italic/hyperlink 등) 을 InlineRun 단위로 표현 (플레인 텍스트 평탄화 금지)
4. 모든 노드가 `Provenance` (section_idx, para_idx, char_start, char_end) 를 보유 — 다운스트림 청커가 원본 위치를 역추적 가능
5. 본문(`body`) 과 장식(`furniture`, 머리글·꼬리말·쪽번호) 분리 — RAG 가 장식 노드를 필터링 가능
6. JSON Schema (Draft 2020-12) 공개 — `$id` URL + 인스턴스 루트에 `schema_version` 필드 고정
7. `doc.to_ir()` → `HwpDocument` Pydantic 모델, `doc.to_ir_json()` → JSON 문자열, `doc.iter_blocks()` → 동기 제너레이터

### v0.2.0 비목표 (v0.3.0 으로 이월)

- 이미지(Picture)·수식(Formula)·각주(Footnote)·미주(Endnote) 노드 — 타입만 예약, 파싱 미구현 (`Literal["picture"]` 등만 enum 에 선언)
- 머리글/꼬리말 **본문** 노드 — v0.2.0 은 존재 여부만 `furniture.page_headers[]` 에 빈 컨테이너로 표시
- HWP 고유 노드 — `TocEntry` (목차), `Field` (상호참조/변수), `RevisionMark` (변경이력)
- 페이지 경계 — 현재 상류 코어는 렌더 시점에만 계산, IR 에는 `page_range: (int, int) | None` 만 선택적 포함 (채우지 않음)
- Markdown/HTML 전체 문서 뷰 변환 — Phase 3 (v0.4.0)
- LlamaIndex/Haystack 어댑터 — Phase 3 (v0.5.0 이후)
- 역직렬화(IR → HWP writeback) — Phase 4 (v1.0.0)

### 영구 비목표

- IR 내 청킹 전략 내장 — RAG 청킹은 소비자 책임. IR 은 *경계 힌트* (section/paragraph boundary) 를 제공할 뿐
- 명제(proposition) 수준 자동 분해 — LLM 의존성이 파서에 유입됨. `TextNode.propositions: list[str] | None` 슬롯만 예약 (항상 `None` 로 출고)
- 픽셀 좌표 제공 — rhwp 는 OCR/이미지 파서가 아님. bounding box 는 렌더 단계 이후에만 의미

## 선행 조사 요약 — 참조한 설계

본 설계를 뒷받침한 4개 영역의 조사 결과 (IR 업계 패턴 / RAG 연구 / Pydantic·JSON Schema / 상류 Rust 코어 노출 타입). 1차 소스 URL 은 문서 말미 § 참조 섹션에 수록.

### 업계 현행 IR 비교

| 시스템 | 본 설계에 채택 여부 | 이유 |
|---|---|---|
| **Docling (IBM, arXiv:2408.09869)** | **1차 참조** | Pydantic V2 공개 모델, `version` 필드 루트 고정, body/furniture 분리, offset 기반 테이블 span — HWP 와 구조적으로 가장 근접 |
| **DocLayNet 11 labels (KDD 2022)** | 어휘로 채택 | Caption/Footnote/Formula/ListItem/PageFooter/PageHeader/Picture/SectionHeader/Table/Text/Title — 업계 de-facto, Docling·Unstructured 파생 |
| **Pandoc AST (pandoc-types 1.23)** | 재귀 구조 아이디어 채택 | `Cell Attr Alignment RowSpan ColSpan [Block]` — 셀 안에 블록 허용 → 중첩 표 자연스럽게 표현 |
| **Azure Document Intelligence v4.0** | span 패턴 채택 | `spans: [{offset, length}]` — rhwp 의 문서 내부 텍스트 오프셋과 직접 매핑 가능 |
| **LlamaIndex `BaseNode`** | NodeRelationship 아이디어 일부 | `PREVIOUS/NEXT/PARENT/CHILD` 개념 — 단, v0.2.0 은 단순 `parent_id` + 자식 리스트만 |
| **Unstructured.io `Element`** | **반면교사** | 플랫 리스트 + 메타데이터 중복(`text_as_html` vs `table_as_cells`) → 구조 보존 실패 |
| **LangChain `Document`** | 어댑터로만 노출 | `(page_content, metadata)` 최소주의 — IR 에서 변환해 내보내는 어댑터만 제공, 주력 타입 아님 |

### RAG 연구로부터

- **2-레이어 검색 (parent-document / auto-merging) 이 지배적 패턴** — LangChain `ParentDocumentRetriever`, LlamaIndex `AutoMergingRetriever`, Anthropic Contextual Retrieval(2024) 모두 문서 구조 보존에 의존. IR 이 `section/paragraph` 경계를 보존하지 않으면 이 패턴을 지원 불가.
- **HtmlRAG (arXiv:2411.02959, WWW 2025)** — 테이블을 plain text 로 평탄화하면 "테이블이 무너진다". HTML 직렬화 + block-tree pruning 이 현재 가장 강력한 테이블 RAG 전략. rowspan/colspan 을 의미 있게 표현하는 유일한 주류 포맷이 HTML.
- **Semantic chunking 은 구조적 chunking 보다 열등** (arXiv:2410.13070, Vectara, NAACL 2025) — HWP 처럼 단락 경계가 명확한 문서에서는 구조적 chunking 이 실용적 최적.
- **Late chunking (Jina, arXiv:2409.04701)** 은 임베딩 레이어의 기법이지 파서 문제가 아님 — IR 은 경계 힌트만 노출하면 됨.
- **명제 수준 분해 (Dense X Retrieval, arXiv:2312.06648, EMNLP 2024)** 는 LLM 전처리 — IR 은 슬롯만 예약.
- **생산 환경 반패턴 3종** — 테이블 중간 분리, 페이지 경계 무시, 과도 세분화. 셋 모두 IR 메타데이터(`TableBlock` 원자화, `page_range`, paragraph-level granularity) 로 방지 가능.

### Pydantic V2 / JSON Schema 제약

- `from __future__ import annotations` **금지** (프로젝트 규칙 재확인) — Pydantic V2 런타임 타입 해소 파괴. 재귀는 문자열 전방 참조 + `model_rebuild()`.
- `Field(ge=, le=, gt=, lt=)` **금지** (프로젝트 규칙) — OpenAI strict mode 가 400 반환. 범위는 `description` 문자열에 서술.
- `abi3-py39` 제약 — PEP 695 `type` 문은 런타임 코드 불가. 타입 alias 는 `Annotated[Union[...], Field(discriminator="kind")]` 형식.
- `extra="forbid"` 를 모든 IR 노드에 — `additionalProperties: false` 자동 생성으로 LLM strict mode 직접 호환. 메타데이터 bag 은 **별도의** `dict[str, Any]` 필드로 명시 분리.
- JSON Schema 출력은 `model_json_schema(mode='serialization')` — `to_ir()` 반환값의 직렬화 형태가 소비자 계약이므로.
- Pydantic V2 는 `$id` 를 자동 주입하지 않음 — CI 단계에서 수동 주입 필요.

## 스키마 설계

### 타입 계층 개요

```
HwpDocument (root)
├── schema_name: Literal["HwpDocument"]
├── schema_version: Literal["1.0"]             # 인스턴스 버전 추적
├── source: DocumentSource | None              # 문서 출처 (uri) — RAG 역추적
├── metadata: DocumentMetadata                 # 제목/작성자/생성일 등
├── sections: list[Section]                    # 구역(용지·단 정의 포함)
│
├── body: list[Block]                          # RAG 청킹 대상 본문
│   └── Block = ParagraphBlock | TableBlock | ...
│           (discriminator="kind", Annotated Union)
│
└── furniture: Furniture                       # 장식 — RAG 필터링 대상
    ├── page_headers: list[Block]              # v0.2.0: 빈 리스트만 출고
    ├── page_footers: list[Block]              # v0.2.0: 빈 리스트만 출고
    └── footnotes: list[Block]                 # v0.2.0: 빈 리스트만 출고
```

### 노드 타입 (`rhwp.ir.nodes`)

v0.2.0 에서 구현 완료되는 구체 타입:

- `HwpDocument` — 문서 루트 (`schema_name`/`schema_version`/`source?`/`metadata`/`sections`/`body`/`furniture`)
- `DocumentSource` — 문서 출처. `uri: str` 만 필수 (파일 경로·URL·custom 식별자). `format`/`bytes_size`/`sha256` 등 재현성 필드는 기본값 있는 옵셔널로 향후 MINOR 확장. `rhwp.parse(path)` 경로는 `uri` 에 원본 path 를 그대로 기록 (normalize 미수행 — 소비자 책임). **LLM Strict-mode 주의**: `HwpDocument.source` 는 기본값 `null` 을 가지므로 Pydantic 이 root `required` 에 올리지 않는다. OpenAI Structured Outputs `strict=true` 소비자는 (a) `source` 를 root `required` 에 명시 추가 + (b) `anyOf: [$ref, null]` → 동일 형태 유지하되 `required` 재계산, 후처리가 필요하다. 옵셔널 필드가 추가될수록 동일 패턴이 반복된다
- `DocumentMetadata` — `title`/`author`/`creation_time`/`modification_time` — 전부 `str | None`. S2 에서 `datetime` 교체는 MINOR 호환 (optional 필드 타입 확장)
- `Section` — v0.2.0 S1 은 `section_idx: int` 만. 용지·단·헤더 레퍼런스는 S2 Rust 매핑 시점에 MINOR 확장
- `ParagraphBlock` — 단락, `kind="paragraph"` + `text`/`inlines: list[InlineRun]`/`prov`
- `InlineRun` — 서식이 동일한 텍스트 런 (bold/italic/underline/strikethrough/href/ruby + `raw_style_id`)
- `TableBlock` — 표, `kind="table"` + `rows/cols/cells/html/text/caption?/prov`. `caption: str | None` — 복합 캡션(캡션 안의 블록)은 v0.3.0+ 로 이월
- `TableCell` — 셀, `row/col/row_span=1/col_span=1/grid_index/role/blocks: list[Block]`
- `Provenance` — 원본 위치 (`section_idx`, `para_idx`, `char_start?`, `char_end?`, `page_range?` — 모두 codepoint 단위)

v0.2.0 에서 enum 에만 선언하고 v0.3.0+ 에서 구현:

- `PictureBlock` / `FormulaBlock` / `FootnoteBlock` / `ListItemBlock` / `CaptionBlock` / `TocEntryBlock` / `FieldBlock`

### 블록 태그드 유니온

**Callable Discriminator 패턴** — `UnknownBlock` catch-all variant 를 v1.0 부터 포함. 이유: Pydantic V2 의 string discriminator 는 미지의 `kind` 를 만나면 `union_tag_invalid` 로 **문서 전체 파싱을 거부**한다. v0.3.0 에서 `PictureBlock` 이 추가될 때 v0.2.0 소비자가 **읽기 불가 상태** 가 되는 것을 방지. 상세 근거: [ir-design-research.md § 1](../../design/v0.2.0/ir-design-research.md#1-block-유니온-확장--minor-bump--unknownblock-안전장치).

```python
from typing import Annotated, Any, Literal, Union
from pydantic import BaseModel, ConfigDict, Discriminator, Tag

_KNOWN_KINDS = {"paragraph", "table"}  # v0.3.0 에서 확장

def _block_discriminator(v: Any) -> str:
    kind = v.get("kind") if isinstance(v, dict) else getattr(v, "kind", None)
    return kind if kind in _KNOWN_KINDS else "unknown"

class UnknownBlock(BaseModel):
    """Forward-compatibility catch-all. Consumers should `case _: skip(block)`."""
    model_config = ConfigDict(extra="allow", frozen=True)
    kind: str              # ^ 실제 값은 "picture" 등 미지 문자열
    prov: Provenance

Block = Annotated[
    Union[
        Annotated[ParagraphBlock, Tag("paragraph")],
        Annotated[TableBlock, Tag("table")],
        Annotated[UnknownBlock, Tag("unknown")],
        # ^ v0.3.0+ 에서 새 블록 추가 시 _KNOWN_KINDS 에 등록 + Union 에 Tag 추가
    ],
    Discriminator(_block_discriminator),
]
```

각 블록 타입은 `kind: Literal["paragraph" | "table" | ...]` 를 보유. `UnknownBlock` 은 `kind: str` (Literal 아님) — 미지의 값을 수용. `pyright` 는 `isinstance` narrowing 을 지원한다.

**권장 소비 패턴** (README 에 기재):

```python
# * OK — graceful unknown handling
match block:
    case ParagraphBlock():
        process_paragraph(block)
    case TableBlock():
        process_table(block)
    case UnknownBlock():
        logger.info("Skipping unknown block kind=%s", block.kind)
    case _:
        # unreachable given the above, but mypy/pyright safety
        pass

# * NO — assert_never 패턴 금지 (새 variant 추가 시 builds break)
```

**셀 안의 블록**: `TableCell.blocks: list[Block]` — 재귀 허용으로 중첩 표 자연 지원. 문자열 전방 참조 + `model_rebuild()` 필수.

### 테이블 표현 — 이중화 전략

**연구 결과 (HtmlRAG + Docling + TableRAG)**: 단일 표현으로 RAG 품질을 최대화할 수 없다. 셋 중 어느 것도 포기하면 손실.

1. **구조화 셀 배열** (`TableBlock.cells: list[TableCell]`) — 프로그래매틱 접근 (SQL 생성, TabRAG 패턴, 셀 순회)
2. **HTML 직렬화** (`TableBlock.html: str`) — LLM 에 제공, rowspan/colspan 보존. 정규화된 HTML (sorted attrs, no-whitespace)
3. **평문 폴백** (`TableBlock.text: str`) — 단순 검색·diff 용. 행은 개행, 셀은 탭 구분

`TableCell.row/col/row_span/col_span` (Azure 패턴, 이해 쉬움) + `TableCell.grid_index: int` (Docling `cell_grid` 대응, O(1) 공간 조회) 병기.

`role: Literal["data" | "column_header" | "row_header" | "layout"]` — DocLayNet 파생 어휘. `"layout"` 은 간격용 빈 셀 등 비의미 셀(연구 결과의 반패턴 5 방지).

**Role 매핑 heuristic** (Rust 매퍼):

| 조건 | role |
|---|---|
| `Cell.is_header == true` | `"column_header"` |
| 병합 (`row_span > 1` 또는 `col_span > 1`) AND 모든 paragraph 텍스트가 공백 | `"layout"` |
| 그 외 | `"data"` |

병합 + empty 조합만 `"layout"` 으로 분류하는 보수적 기준 — 병합되지 않은 빈 셀은 "아직 채워지지 않은 데이터 칸" 일 가능성을 배제할 수 없어 `"data"` 를 유지한다. 더 정교한 detection (주변 context, fill ratio 등) 은 상위 시맨틱 레이어에서 확장할 수 있다. HWP 스펙상 row vs column header 구분이 없어 `"row_header"` 는 현재 출고되지 않지만 enum 값은 예약되어 있다.

### 단락 내 InlineRun

상류 `Paragraph.char_shapes: Vec<CharShapeRef>` 를 UTF-16 위치 기준으로 런으로 변환하되, **의미 있는 속성만** 노출:

```python
class InlineRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    # ^ 하이퍼링크·루비는 상류 Control 트리에서 별도 노출됨 — 후속 단계
    href: str | None = None
    ruby: str | None = None
    # ^ 폰트·크기·색 등 나머지는 raw_style_id 로 에스케이프 (상류 doc_info 인덱스)
    raw_style_id: int | None = None
```

RAG 에서 서식 정보는 대부분 무의미하므로 LLM 에 넘기는 평문화 경로 `ParagraphBlock.text` (런을 이어붙인 결과, 파생 필드) 를 별도 제공. 원본 서식 보존이 필요한 소비자만 `inlines` 를 사용.

### Provenance

```python
class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    section_idx: int
    para_idx: int
    char_start: int | None = Field(
        default=None,
        description="Start character index (Unicode codepoints, 0-indexed). "
                    "Compatible with Python str slicing: text[char_start:char_end]",
    )
    char_end: int | None = Field(
        default=None,
        description="End character index (Unicode codepoints, 0-indexed, exclusive).",
    )
    page_range: tuple[int, int] | None = None  # ^ v0.2.0 은 None 출고
```

모든 `Block` 노드가 `prov: Provenance` 를 보유.

**단위는 Unicode codepoint** — Python `str[i]` 인덱싱과 직접 호환. 상류 `ir-diff` 는 UTF-16 기준이지만 Python 사용자 ergonomics 가 더 중요 (이모지·SMP CJK 혼용 시 UTF-16 오프셋으로 `text[a:b]` 하면 off-by-one 발생). Rust 바인딩 레이어가 상류 `char_offsets` (UTF-16) → codepoint 변환을 `to_ir()` 시점 1회 수행. LSP/JS interop 수요가 생기면 v0.3.0+ 에서 `char_start_utf16` 병렬 필드 추가 (backward-compatible). 상세 근거: [ir-design-research.md § 3](../../design/v0.2.0/ir-design-research.md#3-char-오프셋-단위--unicode-codepoint).

### 스키마 버저닝

**Docling 패턴 채택** (`Annotated[str, StringConstraints]` + validator): `$id` URL + 루트 `schema_version` 필드 병용. **`Literal` 은 사용하지 않음** — forward-read 가 원천 차단되어 라이브러리 목적 (기존 파일 읽기) 에 반함. 상세 근거: [ir-design-research.md § 4](../../design/v0.2.0/ir-design-research.md#4-schema_version-필드-타입--annotatedstr-stringconstraints--validator).

```python
from typing import Annotated, Final
from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

CURRENT_SCHEMA_VERSION: Final = "1.0"
_SCHEMA_VERSION_PATTERN: Final = r"^\d+\.\d+(\.\d+)?$"

SchemaVersion = Annotated[
    str,
    StringConstraints(pattern=_SCHEMA_VERSION_PATTERN, strict=True),
]

class HwpDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_name: Annotated[str, StringConstraints(pattern=r"^HwpDocument$")] = "HwpDocument"
    schema_version: SchemaVersion = CURRENT_SCHEMA_VERSION

    @field_validator("schema_version")
    @classmethod
    def _warn_forward_version(cls, v: str) -> str:
        import warnings
        major = int(v.split(".")[0])
        current_major = int(CURRENT_SCHEMA_VERSION.split(".")[0])
        if major > current_major:
            warnings.warn(
                f"schema_version {v!r} is newer than supported "
                f"{CURRENT_SCHEMA_VERSION!r}. Upgrade rhwp-python.",
                UserWarning, stacklevel=2,
            )
        return v
```

- `$id` URL: `https://danmeon.github.io/rhwp-python/schema/hwp_ir/v1/schema.json` — **불변 경로 정책** (v1 은 영구, breaking change 는 `v2/schema.json` 새 URL)
- In-package JSON 이 1차 배포 (§ JSON Schema 공개), 위 URL 은 외부 도구 편의용
- `$schema`: `https://json-schema.org/draft/2020-12/schema`
- Pydantic 은 `$id` 를 자동 주입하지 않음 → CI 빌드 단계에서 `export_schema()` 스크립트가 주입
- Pattern 은 `"1.0" / "1.1" / "2.0.3"` 등 허용, `"banana"` 같은 잘못된 값 거부
- Validator 는 major 상향 시 UserWarning 만 — reject 아님 (외부 경계 예외: 읽기 경계는 완화)

**버전 증가 규칙**:

| 변경 종류 | 예시 | SchemaVersion | rhwp-python MINOR |
|---|---|---|---|
| 선택 필드 추가 | `TableBlock.caption` 추가 | `1.0` 유지 | 증가 |
| 새 블록 타입 추가 | `PictureBlock` 도입 | `1.0` → `1.1` | 증가 |
| 필수 필드 추가, 열거값 제거 | 파괴적 변경 | `1.0` → `2.0` (새 `$id` URL `v2/`) | MAJOR |

패키지 버전(`rhwp.__version__`) 과 스키마 버전은 **독립** 증가 — 스키마 동결이 패키지 릴리스보다 느릴 수 있음.

## Python API

### 엔트리 포인트 (기존 `rhwp.Document` 확장)

기존 `rhwp.Document` (PyO3 `#[pyclass(unsendable)]` 핸들) 은 그대로 유지. 아래 메서드 추가:

```python
# python/rhwp/__init__.pyi 추가분
from typing import Iterator, Literal

class Document:
    # ... 기존 메서드 생략 ...
    def to_ir(self) -> "rhwp.ir.HwpDocument":
        """구조화 IR 을 Pydantic 모델로 반환.

        첫 호출 시 문서 트리를 순회하며 IR 을 구성한다 (10MB HWP 기준 50-200ms).
        결과는 인스턴스 내부에 캐싱되어 재호출은 즉시 반환된다. IR 모델은
        frozen=True 이므로 반환된 객체 수정 시 ValidationError 가 발생한다.
        독립 사본이 필요하면 ir.model_copy(deep=True) 를 사용한다.
        """

    def to_ir_json(self, *, indent: int | None = None) -> str:
        """IR 을 JSON 문자열로 반환. to_ir() 캐시를 공유한다."""

    def iter_blocks(
        self,
        *,
        scope: Literal["body", "furniture", "all"] = "body",
        recurse: bool = True,
    ) -> Iterator["rhwp.ir.Block"]:
        """블록을 순서대로 스트리밍.

        scope="body" (기본, RAG-safe): 본문 블록만.
        scope="furniture": 머리글 → 꼬리말 → 각주 순.
        scope="all": 전체 — 본문 먼저, 이어서 장식 (furniture 내부 순서와 동일).
        recurse=True: TableCell.blocks 까지 재귀.
        """
```

**Furniture 내부 순서 계약**: `scope="furniture"` 및 `scope="all"` 의 장식 구간은 항상 `page_headers → page_footers → footnotes` 순으로 yield 한다. 소비자가 "어느 furniture 유형에서 나왔는지" 를 `metadata.kind` 대신 순서로도 식별할 수 있도록 고정한다 (v0.3.0 에서 새 furniture 유형이 추가되더라도 기존 세 항목의 상대 순서는 유지).

**속성 직접 접근** — 구조 기반 작업에는 아래가 더 간결:

```python
ir = doc.to_ir()
for blk in ir.body:               # 본문 리스트 직접 순회
    ...
headers = ir.furniture.page_headers  # 장식 요소 직접 접근
```

`iter_blocks` 는 scope+recurse 조합이 필요한 경우용 (`sum(1 for b in doc.iter_blocks(scope="all") if isinstance(b, TableBlock))`). 설계 배경: [ir-design-research.md § 5](../../design/v0.2.0/ir-design-research.md#5-iter-api--docbody--docfurniture-속성--iter_blocksscope-recurse).

**Breaking change 없음** — 기존 `Document.paragraphs()`/`extract_text()` 는 변경 없이 유지.

### 모듈 구조

```
python/rhwp/
├── __init__.py(.pyi)           # 기존 — Document, parse, version 등
├── py.typed                     # 기존
├── ir/                          # 신규
│   ├── __init__.py              # 빈 파일 (CLAUDE.md 규칙)
│   ├── __init__.pyi             # __all__ 만 — HwpDocument/Block 등 재노출
│   ├── nodes.py                 # 모든 Pydantic 모델 (단일 파일, 재귀 해소 용이)
│   ├── schema.py                # export_schema(), $id 주입, JSON 파일 출력
│   └── _build.py                # Rust dict → HwpDocument 어댑터 (model_validate)
└── integrations/
    └── langchain.py             # 기존 — IR → Document 어댑터 추가 (선택)
```

**`ir/` 단일 모듈 선택 이유**: 재귀 유니온(`Block` ↔ `TableCell` ↔ `Block`) 이 동일 파일에 있을 때 `model_rebuild()` 호출 순서를 파일 하단에서 일괄 처리 가능. 파일을 쪼개면 import 순환 + `ForwardRef` 해소 실패 위험.

### Rust 경계 패턴 + 캐싱

**Rust → Python dict → Pydantic `model_validate`** 경로 채택. `pyo3-pydantic` 크레이트(실험적) 는 배제. **캐싱은 Rust `OnceCell<PyObject>` 필드로 구현** — `#[pyclass(dict)]` 불필요 (abi3 limited API 호환 우려 회피). `unsendable` 덕분에 단일 스레드 보장 → lock 불필요. 상세 근거: [ir-design-research.md § 7](../../design/v0.2.0/ir-design-research.md#7-to_ir-캐싱--rust-oncecellpyobject--frozen-ir).

```rust
// src/document.rs
use std::cell::OnceCell;

#[pyclass(name = "Document", module = "rhwp", unsendable)]
pub struct PyDocument {
    pub(crate) inner: rhwp::document_core::DocumentCore,
    // ^ 첫 to_ir() 호출 시 1회 구성, 이후 재사용. Document 수명과 동일
    ir_cache: OnceCell<PyObject>,
}

#[pymethods]
impl PyDocument {
    fn to_ir(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.ir_cache
            .get_or_try_init(|| ir::build_hwp_document(py, &self.inner))
            .map(|obj| obj.clone_ref(py))
    }

    fn to_ir_json(&self, py: Python<'_>, indent: Option<usize>) -> PyResult<String> {
        let ir = self.to_ir(py)?;  // ^ 캐시 재사용
        // Pydantic model_dump_json 호출
        ...
    }
}

// python/rhwp/ir/_build.py
def build_document(raw: dict) -> HwpDocument:
    return HwpDocument.model_validate(raw)
```

**Aliasing 안전성**: IR Pydantic 모델은 모두 `model_config = ConfigDict(extra="forbid", frozen=True)` — 반환된 IR 수정 시도는 `ValidationError` 발생. 캐시된 객체가 공유되어도 변조 불가. 독립 사본은 `ir.model_copy(deep=True)`.

**메모리 회수**: `del doc` 하면 `PyDocument` drop → `OnceCell` 해제 → Python heap 의 IR GC 대상. 배치 워크플로우(`for hwp in glob: ...`) 는 Python 루프 변수 재할당으로 자연 회수.

**파라미터 확장 대비**: 현재 `to_ir()` 는 인자 없음. 미래에 `to_ir(include_*=...)` 가 필요해지면 그 시점에 캐시를 내부 메서드로 격리하고 `to_ir()` 는 매번 새로 생성 (행동 보존, 성능 특성만 변화 — breaking 아님).

**대안** (대형 문서 전용, v0.3.0 이후 검토): Rust 가 JSON bytes 로 직접 직렬화 → Python `HwpDocument.model_validate_json(bytes)`. 중간 dict 생성 생략으로 100MB+ 병리적 문서에서 유리.

### JSON Schema 공개

**4축 배포** (1차 In-package · 2차 GitHub Pages · 3차 content-addressed · 4차 SchemaStore 카탈로그). 근거: [ir-design-research.md § 8](../../design/v0.2.0/ir-design-research.md#8-json-schema-id-호스팅--github-pages--불변-경로--schemastore--in-package).

```python
# python/rhwp/ir/schema.py
_SCHEMA_ID = "https://danmeon.github.io/rhwp-python/schema/hwp_ir/v1/schema.json"

def export_schema() -> dict:
    schema = HwpDocument.model_json_schema(mode="serialization")
    schema["$id"] = _SCHEMA_ID
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return schema

def load_schema() -> dict:
    """In-package schema 로드 — 네트워크 불필요."""
    import json, importlib.resources as pkg_resources
    return json.loads(pkg_resources.read_text("rhwp.ir.schema", "hwp_ir_v1.json"))
```

**1. In-package (1차)** — `python/rhwp/ir/schema/hwp_ir_v1.json`, `pyproject.toml [tool.maturin] include` 에 포함. 모든 `jsonschema.validate()` 경로는 이 파일 사용. 공개 URL 이 다운되어도 사용자 영향 없음.

**2. GitHub Pages (`$id` 편의용)** — `danmeon.github.io/rhwp-python/schema/hwp_ir/v1/schema.json`. CI 배포:

```yaml
# .github/workflows/publish-schema.yml (신규)
- uses: peaceiris/actions-gh-pages@v4
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./python/rhwp/ir/schema
    destination_dir: schema/hwp_ir/v1
    keep_files: true  # ^ 이전 버전 보존 (v1 경로 불변)
```

**3. Content-addressed alias** — `schema/hwp_ir/v1-sha256-<hash>.json` 병행 발행. pin 하고 싶은 소비자용. CI 가 자동 계산·배포.

**4. SchemaStore catalog 등록** — v0.2.0 GA 직후 `SchemaStore/schemastore` 에 PR:

```json
{
  "description": "HWP/HWPX document intermediate representation",
  "fileMatch": ["*.hwp_ir.json"],
  "name": "rhwp Document IR",
  "url": "https://danmeon.github.io/rhwp-python/schema/hwp_ir/v1/schema.json"
}
```

외부 URL 방식이라 스키마 수정 시 SchemaStore 재승인 불필요.

**불변 경로 정책** — v1 URL 은 영구 보존. Breaking change 는 `v2/schema.json` 새 URL (CI guard 로 기존 v1 파일 수정 차단). JSON Schema 자체의 선택 필드 추가는 v1 안에서 in-place 업데이트.

**개인 계정 리스크 수용 근거**: In-package 가 1차이므로 URL 다운은 외부 도구 편의 손상만 유발. GitHub org 이전 (`rhwp-python.github.io`) 은 프로젝트 성장 시 검토 — v0.2.0 블로커 아님.

## 테스트 전략

### 단위 테스트 (`tests/test_ir_schema.py` — 신규)

- `HwpDocument` / `ParagraphBlock` / `TableBlock` 직렬화 왕복 — `model_dump_json()` → `model_validate_json()` 결과 동등성
- discriminator 분기 — 잘못된 `kind` 값은 `ValidationError` 발생
- 재귀 TableCell → Block → TableCell 구조 검증 (중첩 표 3단)
- `extra="forbid"` 실효성 — 정의되지 않은 필드 삽입 시 `ValidationError`
- `export_schema()` 출력의 JSON Schema Draft 2020-12 호환 (`jsonschema` 라이브러리로 meta-validation)
- `schema_version: Literal["1.0"]` 위반 값은 거부

### 통합 테스트 (`tests/test_ir_roundtrip.py` — 신규)

`external/rhwp/samples/aift.hwp` 및 `table-vpos-01.hwpx` 고정 샘플로:

- `Document.to_ir()` 반환 구조 — 구역 수·단락 수가 기존 `section_count`/`paragraph_count` 와 일치
- 텍스트 평탄화 결과 — `"".join(para.text for para in iter_paragraphs(ir))` 가 `extract_text()` 와 일치
- 표 있는 샘플에서 `TableBlock.cells` 개수 = `rows × cols − merged_spans`
- `Provenance.section_idx`/`para_idx` 오름차순 단조 증가

### LLM Strict-mode 호환 테스트 (`tests/test_ir_strict_schema.py` — 신규)

- `export_schema()` 출력에 `additionalProperties: false` 전체 적용 확인
- 모든 `properties` 가 `required` 에 포함 (nullable 은 `T | null` union)
- `minimum`/`maximum`/`exclusiveMinimum`/`exclusiveMaximum` 키워드 **부재** 확인
- `$ref` 순환 참조(TableCell → Block → TableCell) 가 OpenAI 가이드대로 루트 기준 상대 참조로 해소되는지 확인

### 성능 벤치 (`benches/bench_ir.py` — 신규, 선택)

- `to_ir()` + `model_validate()` 비용 측정 — 1000문단·100표 샘플 대비 50ms 목표
- `to_ir_json()` 대비 `model_validate_json()` 왕복 비용

### CI 보강

- `.github/workflows/ci.yml` 에 스키마 conformance job 추가 — 타 Draft 버전 충돌 조기 발견
- `tests/test_ir_schema.py` 를 default 실행 경로에 포함 (`-m "not slow"` 에 유지)

## 구현 스테이지 분할

규모가 커서 `docs/implementation/v0.2.0/stages/` 하위로 스테이지 문서를 분리한다(`docs/roadmap/README.md` 의 "Stage 분할 기준" 재적용).

| Stage | 내용 | 산출물 |
|---|---|---|
| **S1 — Pydantic 모델 초안** | `rhwp.ir.nodes` 단일 파일에 HwpDocument/Section/ParagraphBlock/TableBlock/TableCell/InlineRun/Provenance 구현. `model_rebuild()` 호출. discriminator 설정 | `python/rhwp/ir/nodes.py`, `tests/test_ir_schema.py` |
| **S2 — Rust → dict 매퍼** | `src/document.rs` 에 `to_ir_dict()` 추가. Section/Paragraph 순회, InlineRun 변환 (char_shapes → runs), Provenance 채움. GIL 해제 | `src/document.rs`, `src/ir.rs` (신규) |
| **S3 — Table 통합** | `TableBlock` 생성 로직 — Rust `Table` → cells 배열, HTML 직렬화, 중첩 표 재귀 | S2 확장, `tests/test_ir_roundtrip.py` 의 table-vpos-01 케이스 |
| **S4 — JSON Schema 공개** | `export_schema()`, `$id` 주입, GitHub Pages 배포 파이프라인, `importlib.resources` 경로 | `python/rhwp/ir/schema.py`, `python/rhwp/ir/schema/hwp_ir_v1.json`, `.github/workflows/publish-schema.yml` |
| **S5 — iter_blocks + LangChain 어댑터** | 제너레이터, IR→LangChain `Document` 변환, `HwpDocumentLoader` 가 IR 을 사용하도록 확장 | `python/rhwp/integrations/langchain.py` 확장 |

각 스테이지는 완료 시점에 `docs/implementation/v0.2.0/stages/stage-N.md` 작성. Phase 2 구현 시 동일 패턴.

## 결정 사항 (리서치 기반 확정)

초안 작성 시점의 미결 8건 중 #6 은 사용자 결정으로 스킵, 나머지 7건은 **수행자 + 검증자 2인 1조 × 7 팀 병렬 리서치** 로 확정. 세부 증거·대안 비교·실패 시나리오는 [docs/design/v0.2.0/ir-design-research.md](../../design/v0.2.0/ir-design-research.md) 참조.

| # | 이슈 | 결정 | 핵심 근거 |
|---|---|---|---|
| 1 | Block 유니온 확장 정책 | **MINOR bump + `UnknownBlock` catch-all variant v1.0 부터 포함** | Pydantic V2 discriminated union 은 미지 tag 에 hard-fail — forward-compat 위해 callable Discriminator 로 미지 `kind` 를 `UnknownBlock` 으로 라우팅. `assert_never` 패턴 금지 |
| 2 | HTML 직렬화 위치 | **Python layer (잠정) + 상류 `rhwp::export::html` PR 동시 추진** | Unstructured·Docling 모두 Python, 상류 workflow lag 수용 불가. dedup hash 안정성은 "동일 패키지 버전 내" 로 스코프 제한 |
| 3 | `char_start`/`char_end` 단위 | **Unicode codepoint** (Python `str[i]` 호환) | Docling `charspan`, Azure DI `stringIndexType=unicodeCodePoint` 권장값. UTF-16 은 이모지/SMP CJK 에서 off-by-one. LSP 3.17 교훈 |
| 4 | `schema_version` 필드 타입 | **`Annotated[str, StringConstraints(pattern=...)]` + `field_validator` for UserWarning** | Literal 은 forward-read 차단 (v0.3.0 문서를 v0.2.0 소비자가 읽을 수 없음). OpenAPI·Kubernetes·pip·protobuf 모두 permissive-with-range |
| 5 | iter API 설계 | **`doc.body` / `doc.furniture` 속성 + `iter_blocks(*, scope, recurse)` 병설** | 구조 접근은 속성, 필터링 스트리밍은 메서드. lxml `iter()`+`iterchildren()`, docx-python 속성 패턴 결합 |
| 6 | 중첩 테이블 깊이 | **(skipped)** — 소프트 제한 없음, 문서화만 | 사용자 결정 |
| 7 | `to_ir()` 캐싱 | **Rust `OnceCell<PyObject>` lazy cache + 모든 IR 모델 `frozen=True`** | abi3 호환 (`#[pyclass(dict)]` 불필요), unsendable 덕에 lock 불필요. frozen 이 aliasing 실패 모드 원천 차단 |
| 8 | JSON Schema `$id` 호스팅 | **In-package 1차 + GitHub Pages 공개 URL + content-addressed alias + SchemaStore catalog 등록** | URL 다운시 패키지 내부 사용자 무영향. 불변 경로 정책 (v1 forever, v2 는 새 URL) |

### Breaking change 로 전환된 사항

초안 대비 아래 항목이 v0.2.0 본문 사양 변경:

1. `Provenance.char_start_utf16` → `char_start` (codepoint), 필드명 접미사 제거
2. `schema_version: Literal["1.0"]` → `Annotated[str, StringConstraints]` + validator
3. Block 유니온에 `UnknownBlock` variant 추가 (v1.0 스키마에 포함)
4. 모든 IR Pydantic 모델에 `ConfigDict(frozen=True)` 추가
5. `iter_blocks` 시그니처에 `scope` + `recurse` 파라미터 추가
6. `PyDocument` 구조체에 `ir_cache: OnceCell<PyObject>` 필드 추가
7. `$id` URL 을 `hwp_ir_v1.json` → `schema/hwp_ir/v1/schema.json` 디렉토리 구조로 변경

위 변경은 아직 구현 착수 전이므로 "계획 교정" — 실제 breaking 아님.

## 다른 로드맵 문서에의 파급

- `docs/roadmap/README.md` — 버전 계획 표에서 v0.2.0 = CLI → v0.2.0 = Document IR 로 교체. Phase 2 범위 축소 반영
- `docs/roadmap/phase-2.md` — 대상 버전을 `v0.3.0 ~ v0.4.0` → `v0.3.0` 단일로 축소 (IR 확장만). "선행 조건" 에 v0.2.0 IR GA 명시
- `docs/roadmap/phase-3.md` — v0.4.0 view 렌더러 / v0.5.0 LlamaIndex / v0.6.0 Haystack 으로 버전 한 번 씩 당김
- `docs/roadmap/phase-4.md` — 대상 버전 그대로 (`v1.0.0`) — writeback 은 rhwp Rust 쓰기 API 성숙도에 의존하므로 앞당김 없음
- `docs/roadmap/v0.2.0/cli.md` — 삭제 (git 히스토리 보존)

## 참조

### 1차 소스 (스키마 · 코드 · 스펙)

- Docling core: [docling-project/docling-core — `document.py`](https://github.com/docling-project/docling-core/blob/main/docling_core/types/doc/document.py)
- Pandoc AST: [pandoc-types 1.23.1 — Text.Pandoc.Definition](https://hackage.haskell.org/package/pandoc-types-1.23.1/docs/Text-Pandoc-Definition.html)
- Azure Doc Intelligence Layout (v4.0, 2024-11-30 GA): [공식 문서](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/layout)
- JSON Schema Draft 2020-12: [릴리스 노트](https://json-schema.org/draft/2020-12/release-notes)
- Pydantic V2 JSON Schema: [공식 가이드](https://docs.pydantic.dev/latest/concepts/json_schema/)
- OpenAI Structured Outputs — strict mode 제약: [platform.openai.com/docs/guides/structured-outputs](https://platform.openai.com/docs/guides/structured-outputs)

### 연구 논문

- Docling Technical Report — [arXiv:2408.09869](https://arxiv.org/abs/2408.09869)
- DocLayNet (KDD 2022) — [arXiv:2206.01062](https://arxiv.org/abs/2206.01062)
- Dense X Retrieval (EMNLP 2024) — [arXiv:2312.06648](https://arxiv.org/abs/2312.06648)
- HtmlRAG (WWW 2025) — [arXiv:2411.02959](https://arxiv.org/abs/2411.02959)
- Late Chunking (Jina, 2024) — [arXiv:2409.04701](https://arxiv.org/abs/2409.04701)
- Is Semantic Chunking Worth the Cost? (Vectara, NAACL 2025) — [arXiv:2410.13070](https://arxiv.org/abs/2410.13070)
- Anthropic Contextual Retrieval (2024) — [블로그 포스트](https://www.anthropic.com/news/contextual-retrieval)
- TableRAG (NeurIPS 2024) — [논문 PDF](https://www.csie.ntu.edu.tw/~htlin/paper/doc/neurips24tablerag.pdf)

### 상류 컨텍스트

- `external/rhwp/CLAUDE.md` — 상류 프로젝트 빌드·워크플로우
- `external/rhwp/mydocs/manual/ir_diff_command.md` — 상류 Parser IR 개념 및 라운드트립 검증
- `external/rhwp/src/serializer/hwpx/roundtrip.rs` — 상류 `IrDiff` 구조체
- `external/rhwp/src/model/` — Parser IR 타입 (Document, Section, Paragraph, Table, CharShape 등)
