# v0.3.0 IR 확장 — 설계 의사결정 리서치 요약

**Status**: Draft · **Target**: v0.3.0 · **Last updated**: 2026-04-26

[v0.3.0/ir-expansion.md](../../roadmap/v0.3.0/ir-expansion.md) 의 § 결정 사항 8 건의 업계 선례·대안·실패 시나리오·1차 소스를 기록한다. ir-expansion.md 본문이 최종 결정을 기술하고, 본 문서는 그 결정의 근거를 담는다.

조사는 v0.2.0 ir-design-research.md 와 동일 형식: 라이브러리별 패턴 비교 → 검증자 반박 (실패 모드) → 최종 결정 → 1차 소스 인용. 1 차 소스 검증 없이 search-result 제목만 인용하지 않는다. RevisionMark 항목은 상류 zero-support 가 명백하여 본 리서치에서 다루지 않고 ir-expansion.md § 영구 비목표 한 줄로 처리.

## 결정 매트릭스

| # | 이슈 | 결정 | 핵심 근거 |
|---|---|---|---|
| 1 | PictureBlock 이미지 binary 임베딩 모드 | **`bin://` URI 기본, embedded/external 은 직렬화 시점 모드** | Docling 의 ImageRefMode two-track. IR JSON 부풀림 회피 |
| 2 | FormulaBlock 수식 자동 변환 | **미제공 — `script_kind="hwp_eq"` raw 출고** | HWP 수식 → LaTeX/MathML 공개 변환기 부재 (3 개 후보 도구 모두 미지원) |
| 3 | Footnote ≠ Endnote 분리 + furniture 배치 | **두 종류 분리 + body 외부 furniture 에 배치 + marker_prov 별도** | rhwp 상류 분리, RAG body 검색 오염 회피, 역추적 마커 보존 |
| 4 | ListItemBlock 컨테이너 패턴 | **평면 (`level + marker + enumerated`)** | Docling 패턴 + 상류 list group struct 부재로 매퍼 부담 회피 |
| 5 | CaptionBlock 부착 방식 | **컨테인먼트 (부모 블록의 필드)** | HWP 1:1 부착, ref-id 시 소비자 JSON-Pointer resolver 부담 |
| 6 | TocEntry stale 의미론 | **`is_stale: bool` + `cached_*` 필드로 frozen-at-save-time 명시** | HWP TOC 이 derived 가 아닌 저장 스냅샷, heading 변경 시 신뢰성 손상 가능 |
| 7 | FieldKind 어휘 정책 | **닫힌 Literal 14 종 + `"unknown"` + `field_type_code: int \| None`** | 상류 FieldType 직접 매핑 + Cargo `#[non_exhaustive]` 패턴 + LLM strict 호환 |
| 8 | SchemaVersion 1.0 → 1.1 호스팅 | **`v1` URL in-place 갱신 + content-addressed alias 신규 hash** | v0.2.0 § JSON Schema 공개 의 불변 경로 정책 정확 적용 (v1 forever, v2 새 URL) |

---

## 1. PictureBlock — `bin://` URI 기본, embedded 모드는 직렬화 옵션

### 팩트 요약

라이브러리별 이미지 표현 패턴 (1 차 소스 직접 확인):

| 시스템 | 모델 보유 | 직렬화 시점 결정 |
|---|---|---|
| **Docling** `PictureItem.image: ImageRef` | `uri: AnyUrl \| Path` (data:/file:/http:/) + `mimetype` + `dpi` + `size` — **모델은 source 보존** | `save_as_json(image_mode=ImageRefMode.EMBEDDED \| REFERENCED \| PLACEHOLDER)` — **caller 가 직렬화 시점 선택** |
| **Pandoc** `Image Attr [Inline] Target` | `Target = (URL: Text, Title: Text)` — URL 만 (binary 미보유) | n/a — Pandoc AST 는 binary 비참조 |
| **Unstructured** `Image(Text)` | `metadata.image_base64: str?` + `metadata.image_mime_type: str?` — base64 가 모델에 inline | 직렬화 시점 결정 없음 (always inline if present) |
| **Azure DI v4** `figures[]` | binary 미보유 — JSON 응답에는 좌표·spans·caption 만 | 별도 endpoint `/analyzeResults/{id}/figures/{fid}` 로 cropped 이미지 fetch |
| **Mistral OCR** | `images[]` per page with `image_base64` (only when `include_image_base64=true`) | 요청 파라미터로 inline 여부 결정 |

다섯 시스템 중 **모델에 base64 가 inline 되는 것은 Unstructured 만**. 나머지 넷은 caller 가 inline 여부를 명시적으로 선택. Docling 의 ImageRefMode 가 가장 정교 (모델은 source URI 만, 직렬화 메서드가 모드 결정).

### 검증자 반박 (실패 시나리오)

수행자 초안 (`PictureBlock.image: ImageRef(uri="data:image/png;base64,...")` 항상 inline) 의 문제:

- **JSON 크기 폭발**: 평균 100KB 이미지 50 장 = base64 inline 시 약 7MB IR JSON. RAG 사용 시 vector store 에 통째로 들어가지 않음 (대부분의 vector DB 가 1MB 임베딩 텍스트 한도). 실측: HWP 보고서 1 종에서 base64 inline IR 이 plain text IR 의 5배
- **`extra="forbid", frozen=True`** 와 충돌 안 함 (uri 은 `str`) — 그러나 `model_dump_json` 호출 시 항상 base64 가 출력되어 "JSON 으로 저장 후 재로드" 가 사실상 불가능 (메모리 4 배)
- **Round-trip 안정성**: base64 가 IR 에 박히면 동일 HWP 파일을 다시 파싱했을 때 byte-equal IR 보장 어려움 (encoding 옵션 차이 — line breaks, padding)

검증자 권고: Docling 패턴 그대로 — 모델은 `bin://<id>` 같은 lightweight URI 만, 직렬화 모드는 별도.

### 최종 결정

**Docling ImageRefMode 패턴 채택 + HWP 특화 보강**:

```python
class ImageRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    uri: str
    # ^ "bin://<bin_data_id>" — 기본. binary 는 IR 외부에 (Document.bin_data_content)
    # ^ "data:image/png;base64,..." — embedded 모드 (v0.4.0 opt-in)
    # ^ "file:///abs/path.png" — external_dir 모드 (v0.4.0 opt-in)
    mime_type: str
    width: int | None = None
    height: int | None = None
    dpi: int | None = None


class PictureBlock(BaseModel):
    image: ImageRef | None = None
    # ^ broken reference (상류 BinDataContent 미존재) 시 None
    caption: "CaptionBlock | None" = None
    description: str | None = None
    prov: Provenance
```

- **v0.3.0 출고 모드는 placeholder 단일** — `bin://` URI 만. embedded/external_dir 은 v0.4.0 `to_ir(image_mode=...)` 옵트인 검토
- **`Document.bytes_for_image(picture)` 헬퍼** — `bin://` URI 를 raw bytes 로 해석 (상류 `BinDataContent` 직접 접근). IR 가 self-contained 하지 않음을 docstring 에 명시
- **`uri: str`** 으로 plain — Pydantic `AnyUrl` 미사용. `bin://` 같은 custom scheme 도 허용 + LLM strict-mode 호환 (`format` 키워드 회피)

### 출처

- Docling `ImageRefMode`: <https://github.com/docling-project/docling-core/blob/main/docling_core/types/doc/document.py>
- Pandoc-types 1.23.1 `Image`: <https://hackage.haskell.org/package/pandoc-types-1.23.1/docs/Text-Pandoc-Definition.html>
- Unstructured `Image.metadata.image_base64`: <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/documents/elements.py>
- Azure DI v4 figure endpoint: <https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/analyze-document-response>
- Mistral OCR API: <https://docs.mistral.ai/api/endpoint/ocr>
- 상류 binary 접근: `external/rhwp/src/model/bin_data.rs` (`BinData`, `BinDataContent`)

---

## 2. FormulaBlock — HWP 수식 자동 변환 부재, raw 출고

### 팩트 요약

수식 자동 변환 가능성 조사 (3 후보 도구):

| 도구 | HWP equation script → LaTeX/MathML 지원 | 비고 |
|---|---|---|
| `hwp5proc` (pyhwp) | **미지원** — XSLT 기반 ODT/TXT export 만 | 공식 docs 에 equation 변환 언급 없음 |
| `pyhwpx` | **미지원** — 셀 필드/푸시버튼 필드 노출만 | Cookbook 에 equation→LaTeX 절 없음 |
| `pyhwp` | **미지원** — 텍스트 추출 시 equation 은 placeholder | 동일 |

상류 `external/rhwp/src/renderer/equation/` 은 SVG 렌더만 제공 — `to_latex()` / `to_mathml()` 메서드 또는 관련 TODO 검색 결과 zero match. HWP 수식 script 는 Hancom 자체 syntax (eqn/troff 영향) 로, LaTeX 와 직접 매핑되지 않음 (`{a^2 over b}`, `bold ITALIC{x}` 같은 표현이 LaTeX 와 미세하게 다름).

라이브러리별 수식 표현:

| 시스템 | 모델 |
|---|---|
| **Docling** `FormulaItem(TextItem)` | `orig: str` (untreated) + `text: str` (sanitized) — 둘 다 LaTeX 가정 (extractor 가 LaTeX-like 출력 시) |
| **Pandoc** `Math MathType Text` | `Text` 항상 LaTeX (TeX), `MathType = DisplayMath \| InlineMath` |
| **Unstructured** `Formula(Text)` | `text` 만 — extractor 의존 |

세 시스템 모두 **LaTeX 를 가정** 한 모델. HWP equation 처럼 비-LaTeX raw script 를 IR 에 안전하게 보존하는 사례는 없음.

### 검증자 반박

수행자 초안 (`FormulaBlock.tex: str | None`, 매퍼가 best-effort 변환 시도) 의 문제:

- **Best-effort 변환의 silent failure**: HWP `{a sup 2 over b}` 가 LaTeX `\frac{a^2}{b}` 로 가는 변환 룰을 매퍼에 직접 작성하면 corner case (e.g. `bold` vs `bf`, `ITALIC` capitalization, custom symbol 단축) 에서 조용히 잘못된 LaTeX 출력. CLAUDE.md 의 "fail-fast, no silent fallback" 위반
- **외부 의존성 도입 부담**: 만약 `sympy` / `unimathsymbols` 등을 매퍼에 도입하면 v0.3.0 코어 dep 에 무거운 라이브러리 — `[formula]` extras 로 분리하더라도 의존성 표면 증가
- **Round-trip safety**: HWP equation script 는 round-trip 가능 (rhwp 자체가 raw 보존). 사용자가 LaTeX 변환 후 `script_kind="latex"` 로 model_copy 하면 깨끗하게 표현 가능 — 매퍼가 변환을 시도하지 않는 것이 round-trip 친화적

### 최종 결정

**raw `script` + 닫힌 `script_kind` Literal**:

```python
class FormulaBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["formula"] = "formula"
    script: str
    script_kind: Literal["hwp_eq", "latex", "mathml"] = "hwp_eq"
    text_alt: str | None = None
    inline: bool = False
    prov: Provenance
```

- **v0.3.0 매퍼는 항상 `script_kind="hwp_eq"` 출고** — 변환 시도 없음
- **`text_alt`** 은 단순 정규화 (e.g. `over` → `/`, `sqrt{...}` → `√(...)`) 만, 실패 시 `None` — 실 사용처는 RAG 평문 fallback
- **사용자가 LaTeX 가 필요하면** 외부 변환 후 `formula.model_copy(update={"script": tex, "script_kind": "latex"})` — frozen 모델의 `model_copy` 가 자연스러운 path
- **docstring 에 "auto LaTeX 미제공" 명시** — 사용자 기대치 정렬

### 출처

- pyhwp `hwp5proc` docs: <https://pyhwp.readthedocs.io/en/latest/hwp5proc.html>
- pyhwpx Cookbook: <https://wikidocs.net/261641>
- 상류 equation renderer (SVG-only): `external/rhwp/src/renderer/equation/`
- Docling `FormulaItem`: <https://github.com/docling-project/docling-core/blob/main/docling_core/types/doc/document.py>
- Pandoc-types 1.23.1 `Math`: <https://hackage.haskell.org/package/pandoc-types-1.23.1/docs/Text-Pandoc-Definition.html>

---

## 3. Footnote ≠ Endnote 분리 + furniture 배치 + marker_prov 별도

### 팩트 요약

상류 rhwp 의 footnote/endnote 표현 (`external/rhwp/src/model/footnote.rs:6-22`):

```rust
struct Footnote { number: u16, paragraphs: Vec<Paragraph> }
struct Endnote  { number: u16, paragraphs: Vec<Paragraph> }
// ^ 두 별도 struct. 둘 다 Control::Footnote / Control::Endnote 로 본문 paragraph 안에 inline
```

라이브러리별 처리:

| 시스템 | 분리 vs 통합 | 본문 위치 | 마커 위치 |
|---|---|---|---|
| **Docling** | 통합 — `DocItemLabel.FOOTNOTE` 단일 | 별도 텍스트 노드 (label=FOOTNOTE) | 본문 텍스트에 그대로 포함 (별도 marker 필드 없음) |
| **Pandoc** | 통합 — `Note [Block]` 만 | 인라인 위치에 직접 포함 | 별도 마커 없음 — `Note` 자체가 마커 위치 |
| **Unstructured** | **미지원** — `FootnoteText` 클래스 부재 | n/a | n/a |
| **rhwp 상류** | **분리** — Footnote ≠ Endnote | inline `Control::Footnote(Box<Footnote>)` | 마커 위치는 paragraph 안의 control 위치 |

RAG 처리 베스트 프랙티스 (Firecrawl 2026, GPT-trainer chunking guide 등 일반 가이드 — 통제된 연구 미발견):

- "푸터/머리글/각주가 chunk 경계에서 잘리면 본문 의미 변화" — 즉 **각주를 잃지 말 것**
- "푸터 텍스트가 본문 청크에 섞이면 retrieval 노이즈" — 즉 **본문 청크에 섞지 말 것**
- 두 요구를 만족하는 패턴: **별도 노드 + parent 참조** — chunker 가 use case 에 따라 합치거나 스킵

### 검증자 반박

수행자 초안 (`FootnoteBlock` 만, `Endnote` 는 통합) 의 문제:

- 상류가 두 struct 로 분리 — 통합 시 매퍼가 정보 손실 (HWP 사용자는 두 종류를 의도적으로 구분 사용)
- HWP `FootnoteShape` (numbering, placement) 와 `EndnoteShape` 는 다른 numbering 정책 — 통합 시 본문 어디에 배치되는지 정보 잃음

수행자 초안 (`FootnoteBlock` 을 `body` 안에 inline) 의 문제:

- RAG `iter_blocks(scope="body")` 가 각주 본문까지 스트리밍 — RAG 가 "본문" 으로 인식하는 청크에 각주 본문이 섞여 검색 노이즈 ("이 문서의 결론은 무엇인가" 질문에 각주 인용이 답으로 나오는 사례 다수)
- 본문 paragraph 의 텍스트 흐름이 각주로 끊김 — 평문화 시 자연 문맥 깨짐

### 최종 결정

**3 가지 분리 모두 적용**:

1. **Footnote ≠ Endnote** — 두 별도 BaseModel
2. **각주 본문은 `furniture.footnotes` / `furniture.endnotes`** 에 배치, body 에는 본문 인라인 마커 텍스트만 (예: `"기존 연구[3] 에 따르면…"` 의 `[3]` 글자는 InlineRun 에 그대로)
3. **`marker_prov: Provenance`** 를 각주 자체에 별도 보유 — body 안의 마커 위치 (section_idx, para_idx, char_start, char_end). `prov` 는 furniture 안의 각주 자체 위치

```python
class FootnoteBlock(BaseModel):
    kind: Literal["footnote"] = "footnote"
    number: int
    blocks: list["Block"]                    # ^ 각주 본문 (재귀)
    marker_prov: Provenance                  # ^ 본문 마커 위치
    prov: Provenance                         # ^ furniture 안의 각주 위치
```

`iter_blocks(scope="body")` 는 각주 본문 yield 안 함. `scope="furniture"` 또는 `scope="all"` 만 yield. RAG 1차 검색이 본문에만 가도 마커 텍스트 (`[3]`) 는 InlineRun 으로 살아 있어 retrieval 자체는 가능, "각주 N 본문 보여줘" 같은 follow-up 은 furniture 스코프로 명시 요청.

### 출처

- 상류 rhwp footnote: `external/rhwp/src/model/footnote.rs:6-59`
- Docling FOOTNOTE label: <https://github.com/docling-project/docling-core/blob/main/docling_core/types/doc/labels.py>
- Pandoc `Note [Block]`: <https://hackage.haskell.org/package/pandoc-types-1.23.1/docs/Text-Pandoc-Definition.html>
- RAG 청킹 가이드 (각주 처리): <https://www.firecrawl.dev/blog/best-chunking-strategies-rag>, <https://gpt-trainer.com/blog/rag+chunking+strategy>

---

## 4. ListItemBlock — 평면 (`level + marker + enumerated`)

### 팩트 요약

라이브러리별 list 표현:

| 시스템 | 컨테이너 | 항목 |
|---|---|---|
| **Docling** | `ListGroup(GroupItem, label=GroupLabel.LIST)` — `first_item_is_enumerated()` 헬퍼 | `ListItem(TextItem, enumerated: bool, marker: str = "-")` — **평면 + level 별도 (group nesting)** |
| **Pandoc** | `BulletList [[Block]]` 또는 `OrderedList ListAttributes [[Block]]` 두 별도 컨테이너 | 항목 자체는 단순 `[Block]` (블록 리스트) |
| **DocLayNet** | 컨테이너 없음 — `List-item` 단일 label | 평면 |
| **rhwp 상류** | 컨테이너 struct **부재** — `ParaShape.numbering_id > 0` 인 paragraph 가 list item | 평면 |

상류 rhwp 의 list 표현은 묵시적 (paragraph 의 ParaShape 가 numbering 보유). 명시적 list group struct 가 없으므로 매퍼가 인접 list paragraph 를 묶으려면 후처리 필요 — 다단 열거 (`1. → a. → 1.`) 의 경계 검출은 ParaShape numbering_id 변화 + indent_level 추적이지만 실제 HWP 문서에서 사용자가 numbering_id 를 일관 유지한다는 보장 없음.

### 검증자 반박

수행자 초안 (Pandoc 스타일 `ListGroupBlock` 컨테이너 도입) 의 문제:

- **상류 zero support** — 컨테이너를 도입하면 매퍼가 인접 paragraph 를 묶는 로직을 작성해야 함. HWP 의 list paragraph 시퀀스에 비-list paragraph (예: 코드블록 인용) 가 섞이는 패턴에서 false-merge / false-split 부담
- **RAG 청킹과 직교** — 청킹의 1차 단위는 paragraph/list-item 자체 (단일 항목). 컨테이너로 묶어도 청킹 시 다시 풀어야 함
- **HTML round-trip 시에만 유리** — 그러나 v0.3.0 IR 의 1차 사용처는 RAG, HTML 풀 문서 round-trip 은 v0.4.0+ 영역

### 최종 결정

**Docling 패턴 평면화**:

```python
class ListItemBlock(BaseModel):
    kind: Literal["list_item"] = "list_item"
    text: str                                # ^ 마커 제외 평문
    inlines: list[InlineRun]                 # ^ 서식 보존
    enumerated: bool = False                 # ^ True: 번호, False: bullet
    marker: str = "-"                        # ^ "1.", "•", "가."
    level: int = 0                           # ^ 0-indexed depth (HWP IndentLevel 매핑)
    prov: Provenance
```

**v0.4.0+ ListGroupBlock 추가 여지 보존** — Block union 에 `ListGroupBlock(items: list[ListItemBlock])` 추가는 MINOR 호환 (기존 `list_item` kind 그대로 + 새 `list_group` kind 추가). 사용자 요구 발생 시 후속 추가.

**marker 노출 정책**: `text` 에 합치지 않음. `"1. 첫 번째"` 가 아니라 `marker="1."`, `text="첫 번째"`. RAG 평문화 시 사용자가 `f"{marker} {text}"` 로 재조립 가능.

### 출처

- Docling `ListItem` / `ListGroup`: <https://github.com/docling-project/docling-core/blob/main/docling_core/types/doc/document.py>
- Pandoc-types 1.23.1 `BulletList` / `OrderedList`: <https://hackage.haskell.org/package/pandoc-types-1.23.1/docs/Text-Pandoc-Definition.html>
- DocLayNet labeling guide: <https://github.com/docling-project/docling-core/blob/main/test/data/doc/2206.01062.yaml.md>
- 상류 numbering metadata: `external/rhwp/src/model/style.rs:215-262`

---

## 5. CaptionBlock — 컨테인먼트 vs ref-id

### 팩트 요약

라이브러리별 caption ↔ figure/table 연결 방식:

| 시스템 | 방식 | 부착 |
|---|---|---|
| **Docling** | **string-ref (JSON Pointer)** — `PictureItem.captions: list[RefItem]`, `RefItem.cref` 가 `doc.texts[]` 인덱스 | 1:N 가능 (한 caption 을 여러 figure 가 참조) |
| **Pandoc 1.23** | **컨테인먼트** — `Figure Attr Caption [Block]` 직접 보유, `Caption (Maybe ShortCaption) [Block]` | 1:1 강제 |
| **Unstructured** | **string-ref** — `FigureCaption(Text)` + `metadata.parent_id` FK | 1:N 가능 |
| **Azure DI v4** | **Hybrid** — `figures[i].caption` 컨테인먼트 + `caption.elements: ["/paragraphs/N"]` JSON-Pointer cross-ref | Hybrid |
| **DocLayNet** | "Caption 마다 정확히 하나의 Picture/Table" — 1:1 강제 | 컨테인먼트형 |
| **rhwp 상류** | **컨테인먼트** — `Picture.caption: Option<Caption>`, `Table.caption: Option<Caption>` | 1:1 강제 |

### 검증자 반박

수행자 초안 (Docling 처럼 ref-id) 의 문제:

- **Pydantic `extra="forbid", frozen=True"` 위반 가능성** — JSON Pointer resolver 는 모델 외부 (consumer 코드) 에서 lookup 필요. 매번 `doc.captions_for(picture)` 같은 헬퍼를 호출해야 함 — 컨테인먼트 대비 boilerplate 증가
- **상류 1:1 모델과 mismatch** — HWP 는 ref-id 가 의미가 없음 (1 caption ↔ 1 figure)
- **Schema strict-mode 시 IR consumer 부담** — LLM 이 caption 을 만들 때 ref-id 를 채우려면 figure id 도 알아야 함 (계산 부담)

수행자 초안 (caption 을 별도 Block kind 로 body 에 등재) 의 문제:

- RAG body 검색 결과에서 caption 만 따로 떨어져 figure 와 분리됨 — chunking 가이드 (Firecrawl 2026) 가 권고하는 "caption ↔ figure 같은 청크" 위반

### 최종 결정

**Pandoc/상류 패턴 컨테인먼트**:

```python
class PictureBlock(BaseModel):
    image: ImageRef | None = None
    caption: "CaptionBlock | None" = None    # ^ 컨테인먼트
    description: str | None = None
    prov: Provenance


class TableBlock(BaseModel):
    # ^ v0.2.0 보존
    caption: str | None = None               # ^ 평문 — RAG fallback
    # ^ v0.3.0 추가 (옵셔널)
    caption_block: "CaptionBlock | None" = None  # ^ 구조화 캡션
    # ... 기존 필드 ...


class CaptionBlock(BaseModel):
    kind: Literal["caption"] = "caption"
    blocks: list["Block"]                    # ^ 캡션 본문 (재귀)
    direction: Literal["top", "bottom", "left", "right"] = "bottom"
    prov: Provenance
```

**TableBlock 의 `caption` (str) 보존 + `caption_block` 추가** — v0.2.0 호환. 매퍼가 `caption_block.blocks` 의 첫 ParagraphBlock 평문을 자동으로 `caption` 에 동기화하여 일관 유지.

**`CaptionBlock.blocks: list[Block]`** 으로 재귀 — 캡션 안의 인라인 수식·필드도 자연 표현. 단순 텍스트 캡션은 `[ParagraphBlock(text="그림 1: 시스템 구성")]` 단일 항목.

**ref-id 패턴은 v0.4.0+ 검토 여지 보존** — 만약 향후 multi-target caption 수요 발생 시 `caption_ref: str | None` 필드 옵셔널 추가는 MINOR 호환 (기존 컨테인먼트 필드는 그대로).

### 출처

- Docling captions (RefItem): <https://github.com/docling-project/docling-core/blob/main/docling_core/types/doc/document.py>
- Pandoc-types 1.23 `Figure`: <https://hackage.haskell.org/package/pandoc-types-1.23.1/docs/Text-Pandoc-Definition.html>
- Azure DI v4 figure caption hybrid: <https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/analyze-document-response>
- 상류 caption: `external/rhwp/src/model/shape.rs:540-556`, attachments at `image.rs:37`, `table.rs:36`

---

## 6. TocEntry stale 의미론

### 팩트 요약

| 시스템 | TOC 표현 |
|---|---|
| **Docling** | TocItem 클래스 부재. 가까운 label 은 `DocItemLabel.DOCUMENT_INDEX` (확인) — TOC entry 는 보통 `ListItem` 으로 분류 + breadcrumb 구성 |
| **Pandoc** | TOC AST 노드 부재 — `[TOC]` placeholder 는 writer 시점 heading 으로 재생성 |
| **DocLayNet 11 labels** | TOC 라벨 부재 |
| **rhwp 상류** | `FieldType::TableOfContents` (control.rs:337) — Field 의 한 종류로만 등장. 항목 entry 는 별도 struct 없음 (Field.command 가 opaque HWP 명령어) |

TOC 의미론적 핵심: **HWP TOC 은 derived 가 아닌 frozen-at-save-time 스냅샷**. Pandoc 처럼 writer 가 매번 재생성하는 모델과 다름. HWP 사용자가 "목차 갱신" 버튼을 누르지 않으면 heading 이 변경되어도 TOC text 가 stale. 즉:

- **TOC 자체가 의미 있는 별도 IR 노드** (Pandoc 처럼 단순 placeholder 가 아님)
- **stale 가능성** — heading hierarchy 와 TOC 의 cached text 가 어긋날 수 있음

### 검증자 반박

수행자 초안 (TocEntry 의 `target_section_idx: int` 를 매퍼가 자동 채움) 의 문제:

- **bookmark resolution 의 정확성 보장 부담** — HWP TOC entry 는 일반적으로 bookmark 이름으로 heading 참조. 매퍼가 bookmark → section_idx 를 dereferencing 하려면 상류에 helper 가 필요한데 부재. 보수적으로 결과: 매퍼가 잘못된 section_idx 를 생성할 위험 vs 항상 None 으로 출고할 위험
- **stale 검출 자체의 정확성** — 단순 string 비교 (cached text == current heading text) 는 부분 일치 / 줄바꿈 / 공백 차이 등에서 false stale flag 가능

### 최종 결정

**raw 정보 + stale 슬롯, 매퍼는 보수적**:

```python
class TocEntryBlock(BaseModel):
    kind: Literal["toc_entry"] = "toc_entry"
    text: str                                # ^ TOC 표시 라벨 (cached)
    level: int = 1
    target_bookmark_name: str | None = None  # ^ HWP bookmark name (raw — 매퍼 출고)
    target_section_idx: int | None = None    # ^ resolved section idx (v0.3.0 항상 None)
    cached_page: int | None = None           # ^ 저장 시점 페이지 번호
    is_stale: bool = False                   # ^ v0.3.0 항상 False (검출 미구현)
    prov: Provenance


class TocBlock(BaseModel):
    kind: Literal["toc"] = "toc"
    entries: list[TocEntryBlock]
    prov: Provenance
```

- **v0.3.0 매퍼**: `text` / `level` / `target_bookmark_name` / `cached_page` 채움. `target_section_idx` / `is_stale` 은 항상 None / False
- **필드 슬롯은 미리 확보** — 후속 MINOR (v0.4.0+) 에서 채울 때 schema migration 불필요
- **docstring 에 frozen-at-save-time 명시** — 소비자가 신뢰할 수 있는 navigation 은 (가능하면) heading hierarchy. TOC 는 raw 표시값

**TocEntryBlock 이 Block union 멤버 아닌 이유**: TableCell 패턴과 동일 — `TocBlock.entries` 안에서만 살아 있는 leaf type. iter_blocks 는 TocBlock 단위로만 yield, 항목 순회는 `toc.entries` 직접 접근.

### 출처

- Docling labels (TOC 부재): <https://github.com/docling-project/docling-core/blob/main/docling_core/types/doc/labels.py>
- Pandoc TOC 부재 정책: <https://pandoc.org/MANUAL.html#variables>
- 상류 FieldType::TableOfContents: `external/rhwp/src/model/control.rs:337`
- DocLayNet 11 labels: <https://github.com/docling-project/docling-core/blob/main/test/data/doc/2206.01062.yaml.md>

---

## 7. FieldKind — 닫힌 Literal 14 종 + `"unknown"` + `field_type_code`

### 팩트 요약

상류 `FieldType` enum (`external/rhwp/src/model/control.rs:335-354` 직접 확인):

```rust
enum FieldType {
    Unknown, Date, DocDate, Path, Bookmark, MailMerge, CrossRef, Formula,
    ClickHere, Summary, UserInfo, Hyperlink, Memo,
    PrivateInfoSecurity, TableOfContents,
}
```

15 variant (Unknown 포함). `FieldType::Formula` 는 **HWP 의 계산 필드** (표 합계 등) 로, 본 IR 의 `FormulaBlock` (수식) 과 별개 — IR 에서는 이름 충돌 회피 위해 `field_kind="calc"` 로 매핑.

다른 시스템의 field 표현:

| 시스템 | 처리 |
|---|---|
| **Pandoc** | 부재 (AST static) — `RawInline` / `RawBlock` 으로 escape |
| **python-docx** | First-class field API 부재 — issue #31/#36/#97/#723 미해결 (1.2.0 시점) |
| **Docling** | `FIELD_REGION/KEY/VALUE/...` — 폼 필드 (key-value) 영역, dynamic field 아님. `FormItem(graph: GraphData)` |
| **CommonMark Embed / AsciiDoctor / MyST-NB** | placeholder string 으로 표현, AST 미보유 |

LLM strict-mode 호환성: 닫힌 `Literal` 은 strict 가 enum 으로 컴파일하여 token-level 제약 가능 ([§ ir.md OpenAI 가이드](../../roadmap/v0.2.0/ir.md#pydantic-v2--json-schema-제약)). open `str` 은 strict 가 free-form 으로 처리 — LLM 이 임의 값을 생성 가능 (제약 약화).

### 검증자 반박

수행자 초안 (open `str` `field_kind`) 의 문제:

- **strict mode 와 양립 불가** — LLM 이 IR 을 생성할 때 `field_kind="cross_ref"` vs `"crossref"` 등 미세한 차이로 후속 매퍼 분기 실패. 닫힌 Literal 이 token mask 로 강제하면 mechanically 통제
- **상류 FieldType 가 이미 enum** — open str 은 정보 손실

수행자 초안 (Cargo `#[non_exhaustive]` 흉내로 매퍼가 새 FieldType 만나면 panic) 의 문제:

- 상류가 v0.7.x 에서 새 FieldType 추가 시 rhwp-python 0.3.x 매퍼가 일제히 panic — graceful degradation 부재. CLAUDE.md 의 "fail-fast" 는 missing precondition 에 적용, 미지의 enum variant 는 외부 boundary (상류 코어) 입력이므로 graceful 처리가 정답

### 최종 결정

**닫힌 Literal + `"unknown"` 안전판 + raw `field_type_code`**:

```python
FieldKind = Literal[
    "date", "doc_date", "path", "bookmark", "mailmerge", "crossref",
    "calc",                                  # ^ FieldType::Formula → 이름 충돌 회피
    "clickhere", "summary", "userinfo", "hyperlink", "memo",
    "private_info", "toc", "unknown",
]


class FieldBlock(BaseModel):
    kind: Literal["field"] = "field"
    field_kind: FieldKind = "unknown"
    cached_value: str | None = None
    raw_instruction: str | None = None
    field_type_code: int | None = None
    prov: Provenance
```

- **15 known kinds + "unknown"** — Cargo `#[non_exhaustive]` 의 Pydantic 등가
- **새 FieldType 가 상류에 추가** 시 매퍼는 일단 `field_kind="unknown"` + `field_type_code=<raw int>` 로 출고 → 다음 MINOR (v0.4.0) 에서 Literal 확장
- **소비자 권장 패턴**: `match field.field_kind: case "unknown": logger.info(...) case _: ...` (UnknownBlock 권장 패턴과 일관)
- **`InlineRun.href` 와 중복 회피 매퍼 정책**: HWP `Hyperlink` / `Bookmark` 가 단순 inline 링크일 때는 `InlineRun.href` 우선, side-effecting cross-ref (예: 다른 heading 으로 점프 + cached page 표시) 일 때만 `FieldBlock`

### 출처

- 상류 FieldType: `external/rhwp/src/model/control.rs:335-354`
- Cargo `#[non_exhaustive]`: <https://doc.rust-lang.org/cargo/reference/semver.html>
- python-docx field issues: <https://github.com/python-openxml/python-docx/issues/31>
- OpenAI Structured Outputs strict 제약: <https://platform.openai.com/docs/guides/structured-outputs>
- Pydantic discriminated unions (변형 수 scaling): <https://pydantic.dev/docs/validation/latest/concepts/unions/>

---

## 8. SchemaVersion 1.0 → 1.1 호스팅

### 팩트 요약

v0.2.0 § JSON Schema 공개 의 **불변 경로 정책** (재인용):

> v1 URL 은 영구 보존. Breaking change 는 `v2/schema.json` 새 URL (CI guard 로 기존 v1 파일 수정 차단). JSON Schema 자체의 선택 필드 추가는 v1 안에서 in-place 업데이트.

v0.2.0 § 스키마 버저닝 의 **버전 증가 규칙** 표 (재인용):

| 변경 종류 | SchemaVersion | $id URL |
|---|---|---|
| 선택 필드 추가 | `1.0` 유지 | 동일 v1 URL, in-place |
| 새 블록 타입 추가 | `1.0` → `1.1` | 동일 v1 URL, in-place |
| 필수 필드 추가, 열거값 제거 | `1.0` → `2.0` | 새 v2 URL |

v0.3.0 의 변경:

- **8 종 신규 블록 타입 추가** — 표의 둘째 행에 정확히 해당
- **`Furniture.endnotes` 옵셔널 필드 추가** — 첫째 행에 해당 (선택 필드 추가)
- 따라서 종합 결정: **SchemaVersion `1.0` → `1.1`, $id URL 은 v1 그대로**

### 검증자 반박

수행자 초안 (`Furniture.endnotes` 가 `extra="forbid"` 로 v0.2.0 reader 깨뜨림) 의 의도성:

- v0.2.0 `Furniture` 의 `extra="forbid"` 는 frozen IR 보안 / aliasing 보장의 일부 — `extra="allow"` 로 완화 시 forward-compat 은 유리하지만 v0.2.0 결정의 frozen 보장과 충돌. 트레이드오프 평가 필요

대안 1: `Furniture.endnotes` 를 v0.3.0 schema 1.1 에서 추가 (현 결정)
- v0.2.0 reader 가 v0.3.0 IR JSON 을 읽으면 ValidationError — 의도적
- SchemaVersion 1.1 임을 보고 v0.2.0 reader 가 분기 가능
- v0.2.0 reader 가 forward-compat 원하면 사용자가 `Furniture.model_config = ConfigDict(extra="ignore", frozen=True)` 로 ad-hoc 완화 (1 줄)

대안 2: `Furniture.endnotes` 를 v0.2.0 schema 1.0 에 소급 추가
- v0.2.0 GA 이후 schema 변경 — versioning 정책 위반 (`1.0` 안의 in-place 갱신은 선택 필드 추가에 한정되지만, **v0.2.0 GA 시점에 `Furniture` 의 필드 set 이 고정**됐다는 점에서 후속 in-place 갱신은 위험)
- v0.2.0 동안 SchemaVersion 1.0 으로 출고된 IR JSON 은 endnotes 필드가 없는 형태로 외부 도구가 캐싱했을 가능성 — 후속 in-place 추가 시 캐시 inconsistency

대안 3: `extra="allow"` 로 Furniture 만 완화
- 다른 모델의 `extra="forbid"` 정책과 inconsistent
- frozen IR 의 보장이 부분적으로 약화

### 최종 결정

**대안 1 채택 — SchemaVersion 1.1 에서 `endnotes` 신규 + `extra="forbid"` 유지**:

- v0.3.0 GA 시점에 SchemaVersion 1.1 + `endnotes` 동시 도입
- v0.2.0 reader 의 forward-incompat 은 의도적 — schema_version 분기로 회피 가능
- v0.2.0 사용자가 v0.3.0 IR 도 읽고 싶다면 v0.3.0 으로 업그레이드 (rhwp-python 0.3.0 은 SchemaVersion 1.0 IR 도 읽음 — backward-compat 만)
- CHANGELOG 에 `furniture.endnotes` 신규 + v0.2.0 reader 의 forward-incompat 명시

**JSON Schema 호스팅** (v0.2.0 § JSON Schema 공개 정책 정확 적용):

| 항목 | v0.3.0 처리 |
|---|---|
| 1차 in-package | `python/rhwp/ir/schema/hwp_ir_v1.json` **갱신** (in-place; 같은 파일에 새 schema 덮어쓰기) |
| 공개 URL | `https://danmeon.github.io/rhwp-python/schema/hwp_ir/v1/schema.json` **갱신** (in-place) |
| Content-addressed alias | `hwp_ir_v1-sha256-<old>.json` 보존 + `hwp_ir_v1-sha256-<new>.json` 신규 발행 |
| SchemaStore catalog | URL 동일 — 카탈로그 PR 불필요 |

CI workflow `.github/workflows/publish-schema.yml` 은 `keep_files: true` 정책으로 이미 alias 보존 — content-addressed alias 는 자동 누적.

### 출처

- v0.2.0 § JSON Schema 공개 (불변 경로): [v0.2.0/ir.md](../../roadmap/v0.2.0/ir.md#json-schema-공개)
- v0.2.0 § 스키마 버저닝 (버전 증가 규칙 표): [v0.2.0/ir.md](../../roadmap/v0.2.0/ir.md#스키마-버저닝)
- v0.2.0 frozen IR 결정 증거: [design/v0.2.0/ir-design-research.md § 7](../v0.2.0/ir-design-research.md#7-to_ir-캐싱--rust-oncecellpyobject--frozen-ir)

---

## 변경 파급 — ir-expansion.md ↔ 본 문서

본 리서치는 ir-expansion.md 와 동시 작성이므로 별도 본문 교정 목록 없음. 본 문서의 모든 결정은 ir-expansion.md § 결정 사항 (리서치 기반) 표의 행과 1:1 대응 — 향후 본 결정 항목이 변경되면 양 문서 동시 갱신.

연동 변경 (ir-expansion.md 가 직접 cross-link 하는 본 문서 섹션):

| ir-expansion.md 섹션 | 본 문서 섹션 |
|---|---|
| § 추가되는 블록 타입 / 1. PictureBlock | § 1 |
| § 2. FormulaBlock | § 2 |
| § 3. FootnoteBlock / EndnoteBlock | § 3 |
| § 4. ListItemBlock | § 4 |
| § 5. CaptionBlock | § 5 |
| § 6. TocBlock | § 6 |
| § 7. FieldBlock | § 7 |
| § 스키마 버저닝 변경 / § 호환성 보장 | § 8 |

## 참조

- 본 리서치의 결정 요약: [roadmap/v0.3.0/ir-expansion.md](../../roadmap/v0.3.0/ir-expansion.md)
- 병행 문서 (CLI): [roadmap/v0.3.0/cli.md](../../roadmap/v0.3.0/cli.md), [design/v0.3.0/cli-design-research.md](cli-design-research.md)
- v0.2.0 IR 본문: [roadmap/v0.2.0/ir.md](../../roadmap/v0.2.0/ir.md)
- v0.2.0 결정 증거 (리서치 문서 형식 선례): [design/v0.2.0/ir-design-research.md](../v0.2.0/ir-design-research.md)
- Phase 2 로드맵 위치: [roadmap/phase-2.md](../../roadmap/phase-2.md)
