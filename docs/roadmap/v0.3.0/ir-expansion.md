# v0.3.0 — Document IR v1.1 (블록 타입 확장)

**Status**: Draft · **Target**: v0.3.0 · **Last updated**: 2026-04-26

v0.2.0 의 Document IR 위에 HWP 문서 고유 의미 요소를 더해 RAG/LLM 파이프라인이 표·단락 외에도 그림·수식·각주·목록·캡션·목차·필드를 구조화 형태로 직접 소비할 수 있게 한다. **`UnknownBlock` catch-all 안전장치 위에서 후방 호환을 유지하는 MINOR 증분** — v0.2.0 소비자는 새 `Block.kind` 를 만나도 `UnknownBlock` 으로 graceful skip 한다.

v0.3.0 의 다른 축 (`rhwp-py` CLI) 과의 연동은 [phase-2.md § v0.3.0 두 축의 연동](../phase-2.md) 에 SSOT — 본 spec 은 IR 확장 자체에 집중. 두 축은 같은 릴리스에 함께 GA 한다.

## 배경 — v0.2.0 에서 남긴 빈 자리

v0.2.0 Document IR 은 본문을 `Paragraph` + `Table` 두 종류로만 노출했다. `UnknownBlock` 은 단순 forward-compat 안전장치였고, `furniture.page_headers`/`page_footers`/`footnotes` 는 빈 리스트로 출고됐다. v0.2.0 GA 후 사용 사례에서 드러난 손실:

- **RAG 검색 정확도 저하** — 표 캡션은 `TableBlock.caption: str | None` 으로 들어 있지만 그림 캡션은 들어갈 곳이 없어 본문 단락에 흡수되거나 누락됨. 그림과 캡션이 분리되면 검색 시 문맥 단절
- **각주·미주 정보 손실** — 본문 인용 (`참고문헌 [3]`) 이 있어도 `[3]` 이 가리키는 실제 각주 본문은 IR 에 없어 LLM 이 답변 시 출처 확인 불가
- **목록 구조 무시** — 단락의 numbering/bullet metadata 가 무시되어 평문 단락으로 평탄화. 청킹 시 항목 경계가 사라짐
- **목차 (TOC) 와 cross-reference 가 plain 단락으로** — `FieldType::TableOfContents` / `FieldType::CrossRef` 는 무시되어 단순 텍스트로 흘러 옴
- **머리글/꼬리말 본문이 항상 빈 리스트** — RAG 가 머리글의 페이지 번호·기관명 등을 활용 (또는 명시적으로 필터링) 하려 해도 채워지지 않음

상류 `edwardkim/rhwp` Rust 코어는 위 요소를 **이미 first-class struct/enum 으로 파싱** 한다 (Picture, Equation, Footnote, Endnote, Caption, Field, FieldType, Header, Footer 모두 `external/rhwp/src/model/` 에 노출). 부족한 것은 rhwp-python 의 매핑 레이어 — v0.3.0 은 그 매핑을 채운다. 자세한 상류 노출 상태와 라이브러리 패턴 비교는 [ir-expansion-research.md](../../design/v0.3.0/ir-expansion-research.md) 참조.

## 용어 정리 — Schema v1.0 vs v1.1

v0.2.0 ir.md 의 § 스키마 버저닝 표에 따라:

| 변경 | SchemaVersion | rhwp-python 패키지 |
|---|---|---|
| 선택 필드 추가 (예: `TableBlock.caption_block`) | `1.0` 유지 | MINOR (v0.3.0) |
| 새 블록 타입 추가 (8 종) | `1.0` → **`1.1`** | MINOR (v0.3.0) |
| 필수 필드 추가·열거값 제거 (해당 없음) | (없음) | (해당 없음) |

따라서 **v0.3.0 = SchemaVersion 1.1 + rhwp-python 0.3.0**. JSON Schema `$id` URL 은 그대로 `…/schema/hwp_ir/v1/schema.json` 유지 (v1 major 안의 minor 추가) — v2 URL 은 만들지 않는다. SchemaVersion validator 의 forward-warn 정책상 v0.2.0 소비자가 v0.3.0 문서를 읽을 때 `UserWarning` 만 발생하고 본문은 그대로 흘러 옴 (UnknownBlock 폴백 + 미지 필드는 `extra="forbid"` 로 거부되므로 새 옵셔널 필드 추가는 피하고 새 블록 타입 추가로만 확장).

**JSON Schema 자체는 v1 URL 에 in-place 업데이트**. content-addressed alias `hwp_ir_v1-sha256-<hash>.json` 은 새 hash 로 신규 발행 (이전 v1.0 hash 는 영구 보존).

## 목표와 비목표

### v0.3.0 목표

1. 8 종 신규 블록 타입을 `rhwp.ir.nodes` 에 도입 — `PictureBlock` / `FormulaBlock` / `FootnoteBlock` / `EndnoteBlock` / `ListItemBlock` / `CaptionBlock` / `TocBlock` (+ 내부 `TocEntryBlock`) / `FieldBlock`
2. `furniture.page_headers` / `page_footers` 에 실제 머리글·꼬리말 본문 채움. `furniture.footnotes` / `endnotes` 에 각주·미주 본문 채움
3. SchemaVersion `1.1` GA — JSON Schema in-place 갱신 + content-addressed alias 발행
4. `Document.iter_blocks` 가 신규 kind 를 yield, `kind` 필터로 선택 가능
5. `HwpLoader(mode="ir-blocks")` 가 신규 블록을 LangChain `Document` 로 매핑 (예: `PictureBlock` → caption + alt + URI 메타)
6. `rhwp-py blocks --kind picture|formula|...` CLI 노출 ([cli.md](cli.md) §S2 확장)
7. v0.2.0 모든 공개 API 보존 — `Document.to_ir()` 시그니처 동일, 기존 필드 동일

### v0.3.0 비목표 (v0.4.0 이후)

- **이미지 binary 의 base64 inline 임베딩** — 기본은 placeholder/external 모드. `[embed-images]` extras 또는 `to_ir(image_mode="embedded")` 로 opt-in 검토 (Docling `ImageRefMode` 패턴)
- **HWP equation script → LaTeX/MathML 자동 변환** — 공개 변환기 미존재 (조사 결과 검증). 사용자 책임으로 위임. `script_kind: "hwp_eq"` 로 출고하고 사용자가 외부 도구로 LaTeX 변환
- **TocEntry → 헤딩 dereference** — `target_section_idx` 채우려면 상류 bookmark resolver 가 필요. v0.3.0 은 raw `target_bookmark_name: str | None` 만 노출하고 `target_section_idx` 는 항상 `None`
- **InlineRun ↔ FieldBlock cross-link** — 본문 내 인라인 필드 (예: `[페이지 5 참조]`) 의 위치를 InlineRun 에 표시하는 path 는 `Provenance` 만으로 충분. 별도 inline-field 타입은 도입 안 함
- **머리글/꼬리말의 master-page 분기** — `apply_to: even/odd/both` 차이는 v0.3.0 IR 에 노출 안 함 (full body 평탄화). RAG 사용처에서 거의 무의미

### 영구 비목표

- **`RevisionMark` (변경 이력)** — 상류 rhwp 코어가 미지원 (조사 결과 zero match). 우리가 먼저 IR 에 슬롯을 잡으면 미해결 의존성. 상류 구현이 도착하면 그 시점 재검토
- **픽셀 좌표 / bounding box** — rhwp 는 OCR/이미지 파서가 아님. 좌표는 렌더 단계에서만 의미
- **자동 alt-text 생성** — 이미지 의미 추론은 LLM 단계 책임. IR 은 `caption` / `description: str | None` 슬롯만 제공

## 선행 조사 요약 — 채택한 패턴

각 블록 타입에 대한 라이브러리별 패턴 비교, RAG 처리 합의, JSON Schema/strict-mode 영향은 별도 문서 [ir-expansion-research.md](../../design/v0.3.0/ir-expansion-research.md) 에 정리. 본 절은 채택된 패턴의 한 줄 요약만.

| 블록 | 채택 패턴 | 1차 참조 |
|---|---|---|
| **PictureBlock** | `image: ImageRef`, URI + mime + 선택 dimension. 임베딩 모드는 직렬화 시점 파라미터 | Docling `PictureItem` + `ImageRefMode` |
| **FormulaBlock** | `script: str` (raw HWP script) + `script_kind: Literal["hwp_eq", "latex", "mathml"]` + `text_alt: str | None` | Docling `FormulaItem` + Pandoc `Math` |
| **FootnoteBlock / EndnoteBlock** | 두 종류 분리 (HWP 가 분리). `blocks: list[Block]` 재귀, `marker_prov` 로 본문 마커 위치 별도 보존 | Pandoc `Note [Block]` |
| **ListItemBlock** | 평면 (`level: int` + `marker: str` + `enumerated: bool`) — group container 도입 안 함 | Docling `ListItem` |
| **CaptionBlock** | 컨테인먼트 — 부모 블록 (Picture/Table) 의 필드로 nested. ref-id 미도입 | Docling 와 Pandoc 모두 컨테인먼트형 |
| **TocBlock + TocEntryBlock** | derived/raw 마킹 — `is_stale: bool` 로 cached vs 현재 heading 일치 여부 노출 | DocLayNet 미정의 → HWP-specific 자체 설계 |
| **FieldBlock** | 닫힌 `Literal` 14 종 + `"unknown"` + `raw_instruction: str | None` | rhwp `FieldType` 직접 매핑 |
| **Furniture 채움** | `page_headers → page_footers → footnotes → endnotes` 순서 고정 | v0.2.0 furniture 순서 계약 확장 |

업계 IR 라이브러리 비교 (Docling / Pandoc / Unstructured / Azure Doc Intelligence v4 / Mistral OCR) 와 RAG 연구 (HtmlRAG / Contextual Retrieval / chunking 가이드) 는 [§ ir-expansion-research](../../design/v0.3.0/ir-expansion-research.md#1-per-element-라이브러리-survey) 에서 표 형태로.

## 추가되는 블록 타입

### 1. PictureBlock — 이미지

```python
class ImageRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    uri: str
    # ^ "bin://1234" — 상류 BinData 인덱스 (default; bytes_resolve() 로 해석)
    # ^ "data:image/png;base64,..." — embedded 모드 (opt-in)
    # ^ "file://path.png" — external 모드 (opt-in)
    mime_type: str                  # ^ "image/png", "image/jpeg", "image/bmp", ...
    width: int | None = None        # ^ 픽셀 (codepoint 아님 — 단위 다름)
    height: int | None = None
    dpi: int | None = None


class PictureBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["picture"] = "picture"
    image: ImageRef | None = None
    # ^ None: 상류가 binary 를 찾지 못했을 때 (broken reference)
    caption: "CaptionBlock | None" = None
    description: str | None = None  # ^ HWP 의 alt-text (기존 description 필드)
    prov: Provenance
```

**임베딩 모드 정책**:

- 기본 `uri = "bin://<bin_data_id>"` — 상류 `Picture.image_attr.bin_data_id` 그대로. binary 자체는 IR 에 inline 되지 않음
- `Document.bytes_for_image(picture: PictureBlock) -> bytes` 헬퍼 — `bin://` URI 를 받아 `Document.bin_data_content[id]` 에서 raw bytes 반환
- `Document.to_ir(image_mode="placeholder" | "embedded" | "external_dir")` (v0.3.0+) — 검토만, S1 출고 시점은 placeholder 단일 모드. embedded base64 inline 은 v0.4.0 옵트인 extras 후보

**caption 컨테인먼트**: `PictureBlock.caption: CaptionBlock | None`. `CaptionBlock.blocks: list[Block]` 으로 재귀 — 캡션 안의 인라인 수식·필드도 자연스럽게 표현.

**Schema strict-mode 호환**: ImageRef.uri 는 `str`. URL 검증은 Pydantic `AnyUrl` 대신 plain `str` — strict 가 `format` 키워드를 거부 가능성 + `bin://` / `data:` 모두 유효해야 하므로. 검증은 사용자 책임.

### 2. FormulaBlock — 수식

```python
class FormulaBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["formula"] = "formula"
    script: str                              # ^ raw HWP equation script (e.g. "1 over 2")
    script_kind: Literal["hwp_eq", "latex", "mathml"] = "hwp_eq"
    text_alt: str | None = None              # ^ 평문 근사 — RAG fallback
    inline: bool = False                     # ^ True: 본문 인라인, False: 별도 디스플레이
    prov: Provenance
```

**`script_kind` 가 닫힌 Literal 인 이유**: 미래 `to_ir(formula_target="latex")` 등 변환 옵트인 시 같은 필드명을 재사용하기 위해. v0.3.0 은 항상 `"hwp_eq"` 출고. LaTeX/MathML 변환기를 외부에서 적용한 사용자가 IR 을 재구성할 때 Pydantic frozen 모델 `model_copy(update={"script": tex, "script_kind": "latex"})` 패턴 자연 지원.

**`text_alt` 채움 정책**: 상류 Equation 의 `script` 가 `"1 over 2 + sqrt{x^2 + 1}"` 같이 사람이 어느 정도 읽을 수 있는 형태이므로 v0.3.0 S2 매퍼는 단순 정규화 (`over` → `/`, `sqrt{...}` → `√(...)`) 정도만 적용해 `text_alt` 에 채움. 실패 시 `None` — 상류 SVG 렌더 출력은 IR 에 포함 안 함 (binary 부담).

**자동 LaTeX 변환 부재 명시**: 본 IR 은 LaTeX 를 만들지 않는다. 상류 `external/rhwp/src/renderer/equation/` 은 SVG 렌더만 제공하며 LaTeX/MathML 변환기는 공개 도구가 없다 (조사 결과 검증 — `hwp5proc`, `pyhwpx`, `pyhwp` 모두 미지원). 사용자가 LaTeX 가 필요하면 외부 변환 + IR `model_copy(update=...)` 로 채워 넣어야 한다.

### 3. FootnoteBlock / EndnoteBlock — 각주 / 미주

```python
class FootnoteBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["footnote"] = "footnote"
    number: int                             # ^ 표시 번호 (1, 2, 3, ...)
    blocks: list["Block"]                   # ^ 각주 본문 — 재귀 (표/그림 가능)
    marker_prov: Provenance                 # ^ 본문 인용 마커 위치 (몇번째 단락 몇번째 글자)
    prov: Provenance                        # ^ 각주 자체 위치 (footnote_idx 인덱싱)


class EndnoteBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["endnote"] = "endnote"
    number: int
    blocks: list["Block"]
    marker_prov: Provenance
    prov: Provenance
```

**두 종류 분리 근거**: 상류 rhwp 가 `Footnote` / `Endnote` 를 별도 struct 로 노출. HWP 사용자도 의도가 다름 (각주 = 동일 페이지 하단, 미주 = 문서 끝). Docling 처럼 통합하면 정보 손실.

**body vs furniture 배치**: 각주·미주 본문은 **`furniture` 에 배치**, `body` 에는 **본문 인라인 마커만 단순 글자로** 보존 (`InlineRun.text` 에 `"…기존 연구[3] 에 따르면…"` 그대로). RAG 기본 검색 (`scope="body"`) 은 마커 텍스트만 보고, 인용 본문이 필요할 때 `iter_blocks(scope="furniture")` 로 명시 요청. 인라인 폴루션 회피 + 별도 검색 인덱스 가능.

**`marker_prov` 가 별도인 이유**: `prov` 는 각주 본문 자체의 위치 (`furniture.footnotes` 안의 인덱스), `marker_prov` 는 본문 인용 위치. 두 위치는 서로 다른 section/paragraph. RAG 가 "각주 N 이 본문 어디에서 인용됐는지" 역추적 가능.

### 4. ListItemBlock — 목록 항목

```python
class ListItemBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["list_item"] = "list_item"
    text: str                                # ^ 마커 제외 평문 (RAG fallback)
    inlines: list[InlineRun]                 # ^ 서식 보존 (ParagraphBlock 동일)
    enumerated: bool = False                 # ^ True: 번호, False: 글머리표
    marker: str = "-"                        # ^ "1.", "•", "가.", ...
    level: int = 0                           # ^ 0-indexed nesting depth
    prov: Provenance
```

**평면 (level + marker) 채택 이유**: 상류 rhwp 는 list group 컨테이너가 없다 — `ParaShape.numbering_id > 0` 인 단락이 곧 list item. group 으로 묶으려면 매퍼가 인접 list item 을 후처리로 묶어야 하는데, 다단 열거 (`1. → a. → 1.`) 의 경계 검출이 보수적으로 어렵다. Docling 도 같은 이유로 평면 + level 패턴.

**Pandoc 처럼 `BulletList`/`OrderedList` 컨테이너로 분리 안 한 이유**: 컨테이너 스타일은 HTML 라운드트립 (`<ul>`/`<ol>`) 시 유리하지만 v0.3.0 IR 의 1차 사용처는 RAG 청킹 — 항목 단위 검색에 평면이 직접 매핑. 컨테이너 필요 시 v0.4.0+ 에 `ListGroupBlock(items: list[ListItemBlock])` 추가 (MINOR 호환).

**텍스트 평탄화**: ParagraphBlock 과 동일하게 `text` (마커 제외) + `inlines` 동시 노출. 마커는 `marker` 필드로 별도 — `text` 에 합치지 않음 ("1. 제목" 이 아니라 `marker="1."`, `text="제목"`).

### 5. CaptionBlock — 캡션

```python
class CaptionBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["caption"] = "caption"
    blocks: list["Block"]                    # ^ 캡션 본문 (텍스트면 ParagraphBlock 1개)
    direction: Literal["top", "bottom", "left", "right"] = "bottom"
    prov: Provenance
```

**부모 블록의 필드로 컨테인먼트**: `PictureBlock.caption: CaptionBlock | None`, `TableBlock.caption_block: CaptionBlock | None` (v0.2.0 의 `caption: str | None` 은 보존 — 추가 필드만 신설).

**ref-id 패턴 미도입 근거**: Azure DI v4 / Docling 은 caption ↔ figure 를 string-ref 로 분리하지만 (1:N 주소 가능), HWP 는 항상 1:1 (`Picture.caption: Option<Caption>`, `Table.caption: Option<Caption>`). ref-id 시 소비자가 JSON-Pointer resolver 를 구현해야 하고 extra=forbid 위반. 컨테인먼트가 v0.3.0 RAG use case 에 충분.

**v0.2.0 호환**: `TableBlock.caption: str | None` 필드는 그대로 유지. 새 `caption_block: CaptionBlock | None` 만 옵셔널 추가. `caption` 은 `caption_block.blocks` 첫 번째 ParagraphBlock 의 평문이면 일관성 유지 (매퍼가 자동 채움). 사용자가 v0.2.0 시절 코드를 그대로 쓸 수 있음.

### 6. TocBlock / TocEntryBlock — 목차

```python
class TocEntryBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["toc_entry"] = "toc_entry"
    text: str
    level: int = 1                           # ^ 1-indexed (h1, h2, h3, ...)
    target_bookmark_name: str | None = None  # ^ HWP bookmark 이름 (raw)
    target_section_idx: int | None = None    # ^ resolved section idx (v0.3.0 은 None)
    cached_page: int | None = None           # ^ 저장 시점 페이지 번호 (HWP frozen)
    is_stale: bool = False                   # ^ cached info ≠ 현재 heading
    prov: Provenance


class TocBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["toc"] = "toc"
    entries: list[TocEntryBlock]
    prov: Provenance
```

**TocEntryBlock 이 Block union 멤버 아닌 이유**: TableCell 과 같은 패턴 — `TocBlock.entries` 안에서만 살아 있는 leaf type. `iter_blocks` 는 `TocBlock` 만 yield, `entries` 직접 접근으로 항목 순회.

**`is_stale` 이 v0.3.0 에서 항상 False 인 이유**: 정확한 stale detection 은 heading hierarchy 와 cached text 비교 + bookmark resolution 필요. v0.3.0 매퍼는 cached value 만 노출하고 stale 검출은 v0.4.0+ 또는 사용자 후처리에 위임. 그러나 필드 자체는 v1.1 스키마에 포함 — 후속 MINOR 에서 채울 수 있게.

**HWP TOC 이 frozen at save time** 임을 docstring 에 명시. 소비자가 신뢰할 수 있는 navigation 은 (있다면) heading hierarchy 쪽이며 TOC 는 사람이 마지막에 본 표시 그대로의 스냅샷.

### 7. FieldBlock — 필드 (cross-ref / 날짜 / 페이지번호 / 변수 등)

```python
FieldKind = Literal[
    "date", "doc_date", "path", "bookmark", "mailmerge", "crossref",
    "calc",
    # ^ HWP FieldType::Formula — "수식" 이 아닌 "계산 필드" (표 합계 등). 이름 충돌 회피
    "clickhere", "summary", "userinfo", "hyperlink", "memo",
    "private_info", "toc", "unknown",
]


class FieldBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["field"] = "field"
    field_kind: FieldKind = "unknown"
    cached_value: str | None = None          # ^ 저장 시점 표시 값
    raw_instruction: str | None = None       # ^ HWP field command (Word instrText 대응)
    field_type_code: int | None = None       # ^ 미지의 raw 코드 (forward-compat)
    prov: Provenance
```

**닫힌 Literal + `"unknown"` 안전판**: 상류 `FieldType` 14 종 + Unknown 을 그대로 매핑. 미래에 상류가 새 FieldType 추가 시 매퍼는 일단 `field_kind="unknown"` + `field_type_code=<raw>` 로 출고하고, 다음 MINOR (v0.4.0) 에서 Literal 확장. v0.3.0 소비자는 `field_kind="unknown"` 케이스를 항상 graceful skip 하는 패턴 권장.

**`InlineRun.href` 와의 중복 회피**: HWP `Hyperlink` / `Bookmark` 필드는 v0.2.0 InlineRun 의 `href: str | None` 으로 이미 표현 가능. 매퍼 정책: **side-effecting 한 cross-ref 만 FieldBlock 으로** (`crossref`, `date`, `mailmerge` 등 동적 값). 단순 inline 링크는 `InlineRun.href` 우선. ir.md 에 매퍼 분기표 추가.

**`raw_instruction` 의 역할**: Word `<w:instrText>` 와 같은 round-trip 보존용. v0.3.0 소비자는 보통 `cached_value` 만 사용하지만, 미래 writeback (Phase 4) 시 raw 가 필요. v0.3.0 에서는 채우기만 하고 사용은 안 함.

### 8. Furniture 채움

```python
class Furniture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    page_headers: list[Block] = []
    page_footers: list[Block] = []
    footnotes: list[FootnoteBlock] = []      # ^ v0.3.0 부터 채움
    endnotes: list[EndnoteBlock] = []        # ^ v0.3.0 신규 필드
```

**v0.2.0 furniture 순서 계약 확장**: `iter_blocks(scope="furniture")` 는 항상 `page_headers → page_footers → footnotes → endnotes` 순으로 yield. 새 endnotes 는 기존 세 항목 뒤에 추가되므로 v0.2.0 시절 첫 세 항목 순서는 보존. v0.4.0+ 에서 새 furniture 유형 (예: side-notes) 이 추가되면 그 끝에만 추가.

**`endnotes` 신규 필드의 v0.2.0 호환**: v0.2.0 IR JSON 에는 `endnotes` 키가 없다. v0.2.0 `Furniture(BaseModel)` 의 `extra="forbid"` 때문에 v0.3.0 JSON 을 v0.2.0 으로 읽으면 `ValidationError: extra forbidden`. **이는 의도적 — schema_version 1.0 ≠ 1.1 임을 강제한다**. SchemaVersion validator 의 forward-warn 만으로는 막을 수 없는 영역이므로 사용자가 schema_version 을 보고 분기해야 한다 (문서 § 호환성에 명시).

대안 (`extra="allow"` 로 완화) 은 거부 — frozen IR 의 보안 / aliasing 보장과 충돌. 새 옵셔널 필드보다 새 블록 추가가 forward-compat 친화 (블록은 UnknownBlock 라우팅).

**page_headers/page_footers 매퍼 정책**: 상류 `SectionDef.master_pages: Vec<MasterPage>` + section paragraph 안의 `Control::Header` / `Control::Footer` 를 모두 walk. 동일 section 안의 headers 는 `apply_to: even/odd/both` 무시하고 평탄화 (RAG 1차 사용처에서 불필요한 분기 회피).

## 스키마 버저닝 변경

```python
# python/rhwp/ir/nodes.py — v0.3.0
CURRENT_SCHEMA_VERSION: Final = "1.1"        # ^ v0.2.0 의 "1.0" 에서 minor bump

_KNOWN_KINDS = {
    # ^ v0.2.0
    "paragraph", "table",
    # ^ v0.3.0 신규
    "picture", "formula",
    "footnote", "endnote",
    "list_item", "caption",
    "toc",                                    # ^ TocEntryBlock 은 union 멤버 아님 (TocBlock.entries 안에)
    "field",
}

Block = Annotated[
    Union[
        Annotated[ParagraphBlock, Tag("paragraph")],
        Annotated[TableBlock, Tag("table")],
        Annotated[PictureBlock, Tag("picture")],
        Annotated[FormulaBlock, Tag("formula")],
        Annotated[FootnoteBlock, Tag("footnote")],
        Annotated[EndnoteBlock, Tag("endnote")],
        Annotated[ListItemBlock, Tag("list_item")],
        Annotated[CaptionBlock, Tag("caption")],
        Annotated[TocBlock, Tag("toc")],
        Annotated[FieldBlock, Tag("field")],
        Annotated[UnknownBlock, Tag("unknown")],
    ],
    Discriminator(_block_discriminator),
]
```

11 멤버 (10 known + UnknownBlock). Pydantic V2 callable Discriminator 는 직접 map lookup 이라 O(1) — 변형 수 증가에 따른 검증 비용 증가 없음 ([§ ir-expansion-research § C](../../design/v0.3.0/ir-expansion-research.md#3-스키마--strict-mode-implications-c) 참조).

**`UnknownBlock.kind` 의 `not.enum` 후처리** (`_harden_unknown_variant`) 도 11 known kinds 로 갱신 — `oneOf` 검증의 정확도 보존.

## Python API 영향

### `iter_blocks` 시그니처 — 변경 없음

```python
def iter_blocks(
    self,
    *,
    scope: Literal["body", "furniture", "all"] = "body",
    recurse: bool = True,
) -> Iterator[Block]:
```

**기존 시그니처 유지** — 새 kind 가 자동 yield 됨. 사용자가 추가로 필터링하고 싶으면:

```python
for blk in doc.iter_blocks(scope="body"):
    match blk:
        case PictureBlock() | FormulaBlock():
            handle_visual(blk)
        case FootnoteBlock() | EndnoteBlock():
            # ^ scope="body" 에는 안 옴 — furniture 스코프 명시 필요
            ...
        case _:
            ...
```

CLI `rhwp-py blocks --kind <kinds>` 가 본 메서드 위에서 필터링 (CLI 사양·연동 위치는 [phase-2.md § v0.3.0 두 축의 연동](../phase-2.md)).

### `recurse=True` 의 새 재귀 경로

v0.2.0: `TableCell.blocks` 만 재귀. v0.3.0 추가:

- `FootnoteBlock.blocks` / `EndnoteBlock.blocks` — 각주 본문 안의 표·그림
- `CaptionBlock.blocks` — 캡션 안의 인라인 수식·필드
- (새 컨테이너는 명시적으로 `iter_blocks` 가 yield 하지 않는 leaf — `TocEntryBlock`, `InlineRun`)

`recurse=False` 면 위 재귀를 모두 스킵 (각주 본문 내 표가 yield 안 됨). 기존 v0.2.0 의 `TableCell` 재귀 정책과 일관.

### `Document.bytes_for_image(picture: PictureBlock) -> bytes` — 신규

```python
class Document:
    def bytes_for_image(self, picture: PictureBlock) -> bytes:
        """PictureBlock 의 'bin://' URI 를 bytes 로 해석.

        embedded 모드 ('data:image/...') 또는 external 모드 ('file://...') 인
        PictureBlock 에는 적용 안 됨 — ValueError.
        broken reference (image=None) 도 ValueError.
        """
```

이미지 binary 가 IR JSON 에 inline 되지 않으므로, 사용자가 raw bytes 가 필요할 때 본 헬퍼로 접근. `Document` 가 bin_data_content 를 보유하므로 IR 직렬화 후 다른 프로세스로 전달된 IR 에서는 호출 불가 (intentional — IR 자체는 self-contained 하지 않음을 명시).

### `HwpLoader(mode="ir-blocks")` 변경

v0.2.0 은 `ParagraphBlock` → text content, `TableBlock` → HTML content. v0.3.0 신규 매핑:

| Block kind | LangChain content | metadata 추가 |
|---|---|---|
| `picture` | `caption.blocks` 평문 + `description` (있으면) | `image_uri`, `image_mime`, `image_width`, `image_height` |
| `formula` | `text_alt` 또는 `script` | `script_kind`, `inline` |
| `footnote` / `endnote` | 각주 본문 평문 | `note_kind`, `number`, `marker_section_idx`, `marker_para_idx` |
| `list_item` | `marker + " " + text` | `level`, `enumerated` |
| `caption` | `blocks` 평문 (단독 caption 은 거의 없음 — Picture/Table 자식) | `direction` |
| `toc` | `entries` 의 `text` 들을 개행 결합 | `entry_count` |
| `field` | `cached_value` (또는 빈 문자열) | `field_kind`, `raw_instruction` |

`HwpLoader(mode="ir-blocks")` 의 default 는 v0.2.0 처럼 body 만. 새 옵션 `include_furniture: bool = False` 추가 — True 시 footnote/endnote/header/footer 도 LangChain Document 로 노출 (각각 metadata.scope="furniture").

## 호환성 보장

### v0.2.0 → v0.3.0 코드 호환

- `Document.to_ir()` 시그니처 동일 — 반환 타입은 `HwpDocument` 이지만 v0.3.0 의 HwpDocument 는 v0.2.0 의 슈퍼셋
- v0.2.0 시절의 `paragraph_block.text` / `table_block.cells` / `iter_blocks(scope="body")` 등은 그대로 동작 — 새 kind 가 추가됐을 뿐
- v0.2.0 의 `assert_never` 패턴 미사용 가이드 (v0.2.0 ir.md § 권장 소비 패턴) 가 v0.3.0 에서 본격 효력 — `match block: case _: ...` 가 v0.3.0 의 8 신규 kind 를 모두 흡수

### v0.2.0 ↔ v0.3.0 IR JSON 호환

| 시나리오 | 결과 |
|---|---|
| v0.2.0 소비자가 v0.3.0 IR JSON (`schema_version=1.1`) 을 읽음 | SchemaVersion validator 가 `UserWarning` 발생, 본문은 통과. 새 kind 는 `UnknownBlock` 으로 라우팅. **단** `furniture.endnotes` 는 v0.2.0 `Furniture` 의 `extra="forbid"` 에 걸려 `ValidationError` |
| v0.3.0 소비자가 v0.2.0 IR JSON (`schema_version=1.0`) 을 읽음 | 정상. 새 필드는 default 값 (빈 리스트 / None) — 추가 옵셔널은 모두 default 보유 |

**v0.2.0 측 endnotes ValidationError 회피 권장 패턴**: SchemaVersion 을 먼저 검사 후 majorless minor 차이 시 `Furniture.model_config = ConfigDict(extra="ignore", frozen=True)` 로 ad-hoc 완화. 또는 v0.3.0+ 로 업그레이드. CHANGELOG 에 명시.

### Public API surface diff

```diff
# python/rhwp/ir/__init__.pyi
+ from rhwp.ir.nodes import (
+     PictureBlock, ImageRef,
+     FormulaBlock,
+     FootnoteBlock, EndnoteBlock,
+     ListItemBlock,
+     CaptionBlock,
+     TocBlock, TocEntryBlock,
+     FieldBlock, FieldKind,
+ )

# python/rhwp/__init__.pyi
class Document:
+    def bytes_for_image(self, picture: PictureBlock) -> bytes: ...
```

기존 export 는 모두 그대로 — 추가만 있음.

## 테스트 전략

### 단위 테스트

- `tests/test_ir_picture.py` — PictureBlock + ImageRef 직렬화 왕복 / `bin://` URI 파싱 / caption 컨테인먼트
- `tests/test_ir_formula.py` — FormulaBlock script_kind 분기 / `text_alt` 폴백 정책
- `tests/test_ir_footnote.py` — FootnoteBlock / EndnoteBlock 의 marker_prov ↔ prov 분리 / 각주 안의 표 재귀
- `tests/test_ir_list.py` — ListItemBlock level/marker/enumerated 조합 (HWP numbering vs bullet)
- `tests/test_ir_caption.py` — Picture/Table 양쪽에 caption 부착 (TableBlock.caption_block ↔ caption 일관성)
- `tests/test_ir_toc.py` — TocBlock 컨테이너 + TocEntryBlock leaf type / is_stale 미구현 디폴트
- `tests/test_ir_field.py` — FieldKind 14 종 + unknown 라우팅 / cached_value vs raw_instruction
- `tests/test_ir_furniture.py` — page_headers/page_footers/footnotes/endnotes 순서 보장 / endnotes 가 v0.2.0 schema 와 충돌

### 통합 테스트 (실제 샘플)

- `external/rhwp/samples/aift.hwp` — 머리글/꼬리말 / 단순 footnote 검증
- 그림·각주가 풍부한 HWP 샘플 추가 (필요 시 sample 추가 PR 상류에)
- `table-vpos-01.hwpx` 의 표 캡션이 `TableBlock.caption_block` 으로 노출

### Schema conformance

- `export_schema()` 출력의 SchemaVersion default 가 `"1.1"` 인지 확인
- `_KNOWN_KINDS` 가 11 개로 확장됐는지
- `UnknownBlock.kind` 의 `not.enum` 후처리가 새 kind 들을 포함
- JSON Schema Draft 2020-12 meta-validation 통과
- LLM strict-mode: `additionalProperties: false` 전체 적용 / `minimum`/`maximum` 부재

### CI 보강

- `.github/workflows/ci.yml` 의 `test-without-extras` skip count: v0.2.0 의 4 → v0.3.0 의 N (typer/aiofiles/jsonschema/langchain-core 조합으로 재산정)
- `.github/workflows/publish-schema.yml` — v1.1 in-place 갱신 + content-addressed alias `hwp_ir_v1-sha256-<new>.json` 발행

## 구현 스테이지 분할

규모가 크므로 v0.2.0 패턴대로 `docs/implementation/v0.3.0/stages/` 하위로 분리.

| Stage | 내용 | 산출물 |
|---|---|---|
| **S1 — Picture + Furniture 채움** | `PictureBlock` / `ImageRef` Pydantic 모델 + Rust ir.rs 의 picture walker + bin_data_content 노출. master_pages + Control::Header/Footer 매핑하여 page_headers/page_footers 채움. `Document.bytes_for_image` 헬퍼 | `python/rhwp/ir/nodes.py`, `src/ir.rs`, `tests/test_ir_picture.py`, `tests/test_ir_furniture.py` |
| **S2 — Formula + Footnote/Endnote** | FormulaBlock + 두 노트 타입. 본문 마커 위치는 그대로 InlineRun, 각주/미주 본문은 furniture 로 라우팅 | `nodes.py` 확장, ir.rs 확장, `test_ir_formula.py`, `test_ir_footnote.py` |
| **S3 — ListItem + Caption + Toc + Field** | 작은 4 종 일괄. ParaShape numbering_id 추론 (ListItem) / Picture+Table caption_block (Caption) / FieldType 14 종 매핑 (Field) / TOC 필드 추출 (Toc) | nodes.py 확장, ir.rs 확장, 4 테스트 파일 |
| **S4 — Schema v1.1 + CLI/LangChain + 문서** | SchemaVersion 1.1 GA, JSON Schema in-place 갱신, content-addressed alias 발행. `rhwp-py blocks --kind` 확장. `HwpLoader(mode="ir-blocks")` 신규 매핑. README/examples 업데이트 | `schema/hwp_ir_v1.json` 갱신, `python/rhwp/cli/`, `python/rhwp/integrations/langchain.py`, CHANGELOG, examples |

각 스테이지 완료 시 `docs/implementation/v0.3.0/stages/stage-N.md` 작성 — v0.2.0 과 동일 패턴.

## 결정 사항 (리서치 기반)

| # | 이슈 | 결정 | 근거 |
|---|---|---|---|
| 1 | 이미지 binary 임베딩 | **`bin://` URI 기본, embedded/external 은 직렬화 시점 모드 (v0.4.0+ opt-in)** | Docling `ImageRefMode` 패턴 — 모델은 source 보존, 직렬화 시 결정. IR JSON 크기 폭발 회피. 상세: [ir-expansion-research § 1](../../design/v0.3.0/ir-expansion-research.md#1-pictureblock) |
| 2 | HWP 수식 → LaTeX 자동 변환 | **미제공 — `script_kind="hwp_eq"` 으로 raw 출고. LaTeX/MathML 은 사용자가 외부 변환** | 공개 변환기 부재 (조사 결과 검증). `script_kind` 닫힌 Literal 로 미래 확장 여지. 상세: [§ 2](../../design/v0.3.0/ir-expansion-research.md#2-formulablock) |
| 3 | 각주·미주 분리 vs 통합 | **분리 (`FootnoteBlock` ≠ `EndnoteBlock`)** | 상류 rhwp 가 분리, HWP 사용자 의도 다름 (페이지 하단 vs 문서 끝). Pandoc `Note` 통합 패턴은 정보 손실 |
| 4 | 각주 본문 위치 | **`furniture.footnotes` / `endnotes` — body 와 분리** | RAG body 검색 오염 회피. `marker_prov` 로 본문 인용 위치 별도 보존 → 역추적 가능 |
| 5 | 목록 컨테이너 | **평면 (`level + marker + enumerated`) — group container 미도입** | Docling 패턴, 상류 list group 미존재로 매퍼 부담 회피. 컨테이너 필요 시 v0.4.0+ MINOR 추가 |
| 6 | 캡션 부착 방식 | **컨테인먼트 (`Picture.caption: CaptionBlock`)** | HWP 가 항상 1:1, ref-id 도입 시 소비자 JSON-Pointer resolver 부담. v0.2.0 `TableBlock.caption: str` 필드 보존 + `caption_block` 추가 |
| 7 | TOC 신뢰성 | **`is_stale: bool` 필드로 frozen-at-save-time 명시** | HWP TOC 은 저장 시점 스냅샷, heading 변경 시 stale 가능. v0.3.0 은 cached 만 노출, stale 검출은 v0.4.0+ |
| 8 | Field kind 어휘 | **닫힌 Literal 14 종 + `"unknown"`** | 상류 FieldType 매핑. `field_type_code: int | None` 으로 미래 상류 추가 forward-compat |
| 9 | RevisionMark | **영구 비목표 — 상류 미지원** | 조사 결과 zero match. 상류 구현 시 그 시점 재검토 |
| 10 | SchemaVersion bump | **`1.0` → `1.1` (in-place v1 URL)** | v0.2.0 versioning 표 § "새 블록 타입 추가" 행 정확 적용 |

## 다른 산출물의 파급 (코드 / 데이터)

- `python/rhwp/ir/schema/hwp_ir_v1.json` — v1.1 갱신, content-addressed alias 신규 hash 추가 (구현 stage S4)
- `examples/` — Picture/Footnote 사용 예제 추가

문서 cross-link (README 인덱스 / phase-2 연동) 는 CONVENTIONS.md § Cross-link 방향성 규칙 에 따라 본 spec 본문에서 다루지 않음.

## 참조

### 1차 소스 (라이브러리 / 코드 / 스펙)

- Docling Core `document.py`: <https://github.com/docling-project/docling-core/blob/main/docling_core/types/doc/document.py>
- Docling Core `labels.py`: <https://github.com/docling-project/docling-core/blob/main/docling_core/types/doc/labels.py>
- Pandoc-types 1.23.1: <https://hackage.haskell.org/package/pandoc-types-1.23.1/docs/Text-Pandoc-Definition.html>
- Unstructured `elements.py`: <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/documents/elements.py>
- Azure Document Intelligence v4 layout response: <https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/analyze-document-response>
- Mistral OCR API: <https://docs.mistral.ai/api/endpoint/ocr>
- OpenAI Structured Outputs: <https://platform.openai.com/docs/guides/structured-outputs>

### 연구 / 가이드

- HtmlRAG (WWW 2025): <https://arxiv.org/abs/2411.02959>
- Anthropic Contextual Retrieval (2024): <https://www.anthropic.com/news/contextual-retrieval>
- DocLayNet labeling guide: <https://github.com/docling-project/docling-core/blob/main/test/data/doc/2206.01062.yaml.md>
- Firecrawl chunking guide (2026): <https://www.firecrawl.dev/blog/best-chunking-strategies-rag>

### 상류 컨텍스트 (v0.2.0 pin `bea635b`)

- `external/rhwp/src/model/image.rs` — `Picture`, `ImageAttr`
- `external/rhwp/src/model/bin_data.rs` — `BinData`, `BinDataContent`
- `external/rhwp/src/model/control.rs` — `Equation`, `Field`, `FieldType` 14 종
- `external/rhwp/src/model/footnote.rs` — `Footnote`, `Endnote`, `FootnoteShape`
- `external/rhwp/src/model/header_footer.rs` — `Header`, `Footer`, `MasterPage`
- `external/rhwp/src/model/style.rs` — `Numbering`, `Bullet`, `ParaShape.numbering_id`
- `external/rhwp/src/model/shape.rs` — `Caption`
- `external/rhwp/src/renderer/equation/` — SVG-only equation renderer (LaTeX 미제공)

### v0.2.0 선례

- 본문 v0.2.0 IR 설계: [v0.2.0/ir.md](../v0.2.0/ir.md)
- v0.2.0 결정 증거: [design/v0.2.0/ir-design-research.md](../../design/v0.2.0/ir-design-research.md)
