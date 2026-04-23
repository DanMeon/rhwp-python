# v0.2.0 Document IR — 설계 의사결정 리서치 요약

[v0.2.0/ir.md](../../roadmap/v0.2.0/ir.md) 초안에 남아 있던 8개 미결 결정 사항 중 7개 (#6 "중첩 테이블 깊이 제한" 은 사용자 결정으로 스킵) 를 **수행자 + 검증자 2인 1조 × 7 팀 = 14 에이전트** 병렬 조사로 해결. 본 문서는 각 팀의 핵심 증거·수렴 지점·최종 결정을 기록한다. ir.md 본문의 결정 배경 참조용.

## 결정 매트릭스

| # | 이슈 | 최종 결정 | 수렴/분기 | 주요 근거 |
|---|---|---|---|---|
| 1 | Block 유니온 확장 정책 | **MINOR bump + `UnknownBlock` catch-all 변형** | 수렴 (위험 완화 장치 필요) | Pydantic V2 discriminated union hard-fail, OpenAPI/Docling 모두 MINOR, Cargo SemVer `#[non_exhaustive]` |
| 2 | HTML 직렬화 위치 | **Python layer (잠정) + 상류 PR 동시 추진** | 분기 — Python 실용 vs Rust 이상론 | Unstructured/Docling 은 Python, 검증자는 IR drift · dedup hash divergence 경고 |
| 3 | char 오프셋 단위 | **Unicode codepoint** (`char_start`/`char_end`) | 완전 수렴 | Docling 동일 패턴, Python `str[i]` 호환, LSP 3.17 UTF-16 교훈 |
| 4 | `schema_version` 필드 타입 | **`Annotated[str, StringConstraints(pattern=...)]`** + `field_validator` | 완전 수렴 | Docling 실증, OpenAPI 3.x regex, Kubernetes/pip 등 모두 permissive-with-range |
| 5 | iter API 설계 | **`doc.body`/`doc.furniture` 속성 + `iter_blocks(scope=, recurse=)` 병설** | 부분 수렴 (둘 다 채택) | lxml `iter()`/`iterchildren()`, Docling `iterate_items`, docx-python 속성 패턴 |
| 7 | `to_ir()` 캐싱 | **Rust `OnceCell<PyObject>` lazy cache + IR Pydantic 모델 `frozen=True`** | 분기 — 수행자 캐시 설계 vs 검증자 반대 | abi3 호환, aliasing 방지 (frozen), unsendable 단일 스레드 락 불필요 |
| 8 | JSON Schema `$id` 호스팅 | **GitHub Pages + 불변 경로 정책 + In-package 1차 + SchemaStore 카탈로그 등록** | 수렴 (완화책 필요) | OpenAPI/AWS 자체 도메인, 소규모는 GitHub Pages + SchemaStore 외부 URL 패턴 |

---

## 1. Block 유니온 확장 — MINOR bump + UnknownBlock 안전장치

### 팩트 요약

업계 표준은 **새 variant 추가 = MINOR**:
- Docling v2.x: `RichTableCell` (v2.46), `Field` (v2.70) 추가 모두 MINOR. MAJOR 는 `DoclingDocument` 전체 교체 (v2.0) 때만
- OpenAPI 3.0 → 3.1: MINOR 로 분류 (단, OAI 는 SemVer 이탈 공식 선언)
- Cargo SemVer: `#[non_exhaustive]` enum 에 variant 추가는 MINOR; 없으면 MAJOR
- Kubernetes CRD: optional 필드 추가는 비파괴적

### 검증자의 반박 (실증)

그러나 **"consumer 가 graceful handle 하면 된다" 가정이 Pydantic V2 + pyright + OpenAI strict mode 에서 기계적으로 거짓**:

1. **Pydantic discriminated union hard-fail**: `{"kind": "picture"}` 한 개라도 포함되면 `union_tag_invalid` 로 **문서 전체 파싱 거부**
2. **pyright strict**: `match block: case Paragraph() case Table()` + `assert_never` 패턴이 v1.1 도입 시 빌드 브레이크
3. **OpenAI Structured Outputs**: v1.0 에 컴파일된 DFA mask 는 `kind: "picture"` 를 토큰 레벨에서 생성 불가
4. **TypeScript codegen**: `quicktype`/`datamodel-code-generator` 로 만든 TS union 은 regenerate 없이 컴파일 브레이크

### 최종 결정

**MINOR bump 정책 유지 + 다음 안전장치 v1.0 에 미리 도입**:

1. **`UnknownBlock(BaseModel)` catch-all variant** 를 v1.0 부터 Block 유니온에 포함 — Pydantic callable `Discriminator` 로 미지의 `kind` 를 여기로 라우팅
2. **문서에서 권장 소비 패턴을 `case _: return None` 으로 고정** — `assert_never` 패턴은 "사용하지 말 것" 으로 명시
3. **스키마 `$id` 는 major 단위로 불변** — v1.0 도 v1.1 도 같은 `hwp_ir_v1.json` URL (§8 참조). JSON Schema 자체는 in-place 업데이트되지만, LLM Structured Outputs 사용자는 별도의 버전 pin 필요 (문서로 안내)

### 출처

- [docling-core v2.0.0 Release](https://github.com/docling-project/docling-core/releases/tag/v2.0.0)
- [Cargo SemVer Compatibility](https://doc.rust-lang.org/cargo/reference/semver.html)
- [OAI Discussion #3793](https://github.com/OAI/OpenAPI-Specification/discussions/3793)
- [Pydantic callable Discriminator](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions-with-callable-discriminator)

---

## 2. HTML 직렬화 위치 — Python layer 잠정 + 상류 PR 준비

### 수행자 근거 (Python layer)

조사한 7개 프로젝트 중 RAG 용 HTML 직렬화가 Rust 코어에 있는 사례 **0개**:
- **Unstructured `TableElementHtml`** (BeautifulSoup 사용, 순수 Python)
- **Docling `TableItem.export_to_html()`** (순수 Python)
- **Polars `DataFrame.write_html()`** (Rust core + Python export)
- **tree-sitter + py-tree-sitter**: tree-sitter 는 IR 만, 렌더링은 상위 레이어

성능: HWP 전형 (≤100표, 표당 ≤1000셀) 기준 Python `f-string` + `html.escape()` 로 총 100-200ms — I/O 대비 무시 가능. HtmlRAG 정규화(attribute order, 공백) 는 Python 제어가 편함. 상류 `edwardkim/rhwp` 하이퍼-워터폴 워크플로우상 PR 수락 lag 가 수 주~수 개월 현실적.

### 검증자 근거 (Rust upstream)

- **IR drift 리스크**: 상류가 `TableCell` 표현을 바꿨을 때 Python HTML 생성기가 조용히 잘못 동작
- **Dedup hash divergence**: 상류가 나중에 자체 HTML 을 추가하면 attribute 순서·공백·엔티티 선택 차이로 **RAG dedup 가 실패**
- **미래 바인딩 amortization**: Ruby/Node.js 바인딩이 각각 재구현
- **"비공식 바인딩" 포지셔닝**: 포맷 결정은 포맷 소유자 (상류) 영역

### 최종 결정

**Python layer 에 구현하되, 명시적 "잠정" 마커**:

```python
# python/rhwp/_html.py
def table_block_to_html(block: TableBlock) -> str:
    """Provisional — may delegate to upstream Rust core in a future release.

    Attribute order fixed (rowspan-before-colspan) for deterministic hashing.
    Whitespace normalized: strip + collapse.
    """
```

동시에:
1. 상류에 **HTML export 도입 제안 이슈** 개설 — waterfall 승인 대기 (타임라인 비동기)
2. `TableBlock.html` docstring 에 "v0.3.0+ 에서 상류 구현으로 위임될 수 있음" 명시
3. HtmlRAG 호환 dedup 해시가 필요한 사용자에게는 "동일 패키지 버전 내에서만 해시 안정성 보장" 을 README 에 고지
4. 상류 구현이 도착하면 Python 레이어는 fallback 으로 유지 (backward-compatible 전환)

### 출처

- [Unstructured `convert.py`](https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/html/convert.py)
- [Docling Core Table export](https://github.com/DS4SD/docling-core)
- [pulldown-cmark html renderer (반례)](https://github.com/raphlinus/pulldown-cmark/blob/master/pulldown-cmark/src/html.rs) — 크레이트 1차 목적이 Markdown-to-HTML 이라 core 에 있음
- [edwardkim/rhwp CLAUDE.md](../../../external/rhwp/CLAUDE.md) — waterfall 워크플로우

---

## 3. char 오프셋 단위 — Unicode codepoint

### 만장일치 결론

수행자와 검증자 모두 동일 결론: **codepoint 단위, 필드명에 인코딩 명 박지 않기**.

### 증거

- **Docling `ProvenanceItem.charspan: tuple[int, int]`**: 0-indexed character span, Python `len()` 기준 → codepoint
- **LSP 3.17 `PositionEncodingKind`**: UTF-16 이 기본이지만 협상 가능. 3.17 이전 UTF-16-only 가 **10년간 off-by-one 버그를 낳았다** 는 MS 공식 post-mortem
- **Azure Doc Intelligence `stringIndexType`**: `textElements | unicodeCodePoint | utf16CodeUnit` 선택 가능. **Python SDK 권장값은 codepoint**
- **tree-sitter**: UTF-8 byte (Rust native) — parse tree 가 원본 텍스트를 보유하지 않아 재계산 없이 유지 가능한 단위
- **Python `str`**: PEP 393 (3.3, 2012) 이후 내부 codepoint 인덱싱. `text[i]` 가 codepoint 단위

### 실패 시나리오 (검증자 제시, 재현 가능)

```python
>>> full_text = "회의록 🙂 요약"  # 🙂 = U+1F642 (surrogate pair in UTF-16)
>>> len(full_text)                             # codepoints
9
>>> len(full_text.encode("utf-16-le")) // 2    # UTF-16 units
10
>>> # 상류가 UTF-16 기준 char_start=8, char_end=10 으로 "요약" 을 가리키면:
>>> full_text[8:10]
'약'   # off-by-one — '요' 가 날아감
```

한글 자체는 BMP 범위 (U+AC00 ~ U+D7A3) 라 UTF-16 = codepoint 이지만, **이모지·SMP CJK (U+20000+)** 혼용 시 즉시 어긋남.

### 최종 결정

```python
class Provenance(BaseModel):
    char_start: int = Field(
        description="Start character index (Unicode codepoints, 0-indexed). "
                    "Compatible with Python str slicing: text[char_start:char_end]"
    )
    char_end: int = Field(
        description="End character index (Unicode codepoints, 0-indexed, exclusive)."
    )
```

Rust 바인딩 레이어는 상류의 UTF-16 `char_offsets` 벡터를 **once at `to_ir()`** 로 codepoint 인덱스로 변환 (O(n), 캐시됨). v0.3.0+ 에서 LSP/JS interop 수요 생기면 `char_start_utf16` 병렬 필드 추가 — breaking 아님.

### 출처

- [LSP 3.17 PositionEncodingKind](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#positionEncodingKind)
- [Azure DI StringIndexType](https://learn.microsoft.com/en-us/rest/api/aiservices/document-models/analyze-document?view=rest-aiservices-v4.0+(2024-11-30))
- [docling-core ProvenanceItem](https://github.com/docling-project/docling-core)
- [upstream rhwp `paragraph.rs`](../../../external/rhwp/src/model/paragraph.rs) — UTF-16 내부 표현

---

## 4. `schema_version` 필드 타입 — `Annotated[str, StringConstraints]` + validator

### 만장일치 결론

**`Literal["1.0"]` 금지**. Docling 패턴 (`Annotated[str, StringConstraints(pattern=SEMVER_REGEX)]`) 채택.

### Literal 의 치명적 결함

v0.3.0 에서 `schema_version="1.1"` 문서를 v0.2.0 소비자가 읽으면:

```
pydantic_core.ValidationError: schema_version
  Input should be '1.0' [type=literal_error, input_value='1.1']
```

→ 사용자는 "이 문서가 뭐가 잘못됐는지" 조차 기계적으로 판독 불가. **forward-read 가 원천 차단**.

업계 선례는 모두 permissive-with-range:
- **OpenAPI 3.x** `openapi` 필드: `str` + regex `^3\.1\.\d+(-.+)?$`
- **pip metadata**: `metadata-version` 은 free-form `str` — 상위 버전 만나면 `warn("may not be fully understood")` 후 진행 (pip PR #9139, 2020)
- **Kubernetes CRD**: 전용 webhook 없이는 strict 버전 매칭 사용 금지 (공식 문서 경고)
- **protobuf**: `syntax = "proto3"` 자유형
- **JSON Schema `$schema`**: URI, 절대 enum 아님 (Draft 4/6/7/2019-09/2020-12 detect-and-degrade 필수)

### 최종 결정

```python
# python/rhwp/ir/nodes.py
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
                f"{CURRENT_SCHEMA_VERSION!r}. Some fields may be ignored. "
                f"Upgrade rhwp-python.",
                UserWarning,
                stacklevel=2,
            )
        return v
```

- **Pattern** 은 `"1.0"` / `"1.1"` / `"2.0.3"` 허용, `"banana"` 거부
- **Validator** 는 major 상향 시 UserWarning 만 발생 (reject 아님 — CLAUDE.md "fail-fast only at external boundaries" 예외: 외부 파일 읽기 경계)
- **JSON Schema 출력** 은 `{"pattern": "^\\d+\\.\\d+(\\.\\d+)?$", "type": "string"}` — 소비자 validator 가 forward-compat 가능

### 출처

- [docling-core `document.py`](https://github.com/docling-project/docling-core/blob/main/docling_core/types/doc/document.py) — 실증 패턴
- [OpenAPI 3.0 JSON Schema](https://spec.openapis.org/oas/3.0/schema/2024-10-18.html)
- [Kubernetes CRD Versioning](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/)
- [pip PR #9139 metadata-version handling](https://github.com/pypa/pip/pull/9139)

---

## 5. iter API — `doc.body` / `doc.furniture` 속성 + `iter_blocks(scope=, recurse=)`

### 수행자 제안

`scope: Literal["body", "furniture", "all"] = "body"` + `recurse: bool = True` — Docling `iterate_items(included_content_layers=...)` 단순화 버전.

### 검증자 제안

`iter_blocks` 자체를 제거하고 **`doc.body: list[Block]` / `doc.furniture: Furniture` 속성만 노출** — lxml `.getroot()` 반복, docx-python `Document.paragraphs` 직접 속성 패턴. Fowler "FlagArgument" 안티패턴 회피.

### 최종 결정

**둘 다 채택**:

```python
class HwpDocument(BaseModel):
    body: list[Block]          # ^ 구조적 접근 — for blk in doc.body
    furniture: Furniture       # ^ .page_headers, .page_footers, .footnotes

    def iter_blocks(
        self,
        *,
        scope: Literal["body", "furniture", "all"] = "body",
        recurse: bool = True,
    ) -> Iterator[Block]:
        """Stream blocks with optional filtering/recursion.

        - scope="body" (default, RAG-safe): yield body content only.
        - scope="furniture": yield headers/footers/footnotes.
        - scope="all": yield both, body first.
        - recurse=True: descend into TableCell.blocks.
        """
```

- **속성 (`body`/`furniture`)** 은 구조 자체를 드러냄 — 직접 순회·슬라이싱·`isinstance` 필터 가능
- **`iter_blocks()`** 는 recursion + scope 조합이 필요한 케이스 (`sum(1 for b in doc.iter_blocks(scope="all") if isinstance(b, TableBlock))`)

**기본값 `scope="body"` 근거**:
- RAG 이 1차 사용처 — 머리글/꼬리말 임베딩 포함이 검색 오염의 주된 원인 (연구 결과 § RAG 반패턴 5)
- Docling 도 `iterate_items(included_content_layers=None)` = 전체 이지만 실제 RAG 문서 예제는 body-focused

**`iter_blocks` 이름 유지 근거**: lxml `iter()`, BeautifulSoup `.descendants` 와 일관. `walk()` 는 재귀 강조 — v0.3.0 에서 `(Block, depth)` 튜플 반환하는 `walk()` 추가 여지 남김.

### 출처

- [lxml `_Element.iter` / `iterchildren`](https://lxml.de/apidoc/lxml.etree.html)
- [Docling `iterate_items()`](https://docling-project.github.io/docling/reference/docling_document/)
- [Fowler "FlagArgument"](https://martinfowler.com/bliki/FlagArgument.html)
- [python-docx `Document.paragraphs`](https://python-docx.readthedocs.io/en/latest/api/document.html)

---

## 7. `to_ir()` 캐싱 — Rust `OnceCell<PyObject>` + frozen IR

### 수행자 설계

```rust
#[pyclass(name = "Document", module = "rhwp", unsendable)]
pub struct PyDocument {
    pub(crate) inner: rhwp::document_core::DocumentCore,
    ir_cache: std::cell::OnceCell<PyObject>,
}

#[pymethods]
impl PyDocument {
    fn to_ir(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.ir_cache
            .get_or_try_init(|| build_hwp_document(py, &self.inner))
            .map(|obj| obj.clone_ref(py))
    }
}
```

- **abi3-py39 호환**: `#[pyclass(dict)]` 불필요 — Rust 구조체 필드로 캐시
- **Thread-safe (trivially)**: `unsendable` → 항상 owning 스레드만 접근 → `OnceCell` 은 `!Sync` 여도 안전
- **공유 경로**: `to_ir_json()` 이 `to_ir()` 재사용 → 캐시 자동 공유

### 검증자 반박

1. **Aliasing**: 같은 IR 인스턴스를 여러 번 반환하면 사용자가 `ir.blocks[0].text = "..."` 로 변경 시 다른 호출자에 노출
2. **Memory retention**: 배치 (10k HWP) 처리 시 캐시가 GC 차단 → OOM
3. **Cache-key retrofit**: 미래 `to_ir(include_furniture=True)` 파라미터 추가 시 단일 슬롯 캐시는 stale 반환

### 최종 결정 — 수행자 설계 채택 + 검증자 완화책 통합

1. **`OnceCell<PyObject>` 캐시** (수행자)
2. **IR Pydantic 모델 전체 `model_config = ConfigDict(frozen=True)`** (검증자 Aliasing 반박 무력화) — 변경 시도 시 `ValidationError`
3. **Document 는 read-only** (상류 API 가 수정 제공 안 함) → 무효화 시점 없음
4. **메모리 재점유**: `del doc` 로 캐시 해제 — docstring 으로 명시
5. **파라미터 확장 대비**: 현재 `to_ir()` 는 인자 없음. 미래에 `to_ir(include_furniture=...)` 가 필요해지면 **그 시점에 캐시를 별도 메서드 `_materialize_ir()` 로 내부화하고 `to_ir()` 는 매번 새로 생성** — breaking 아님 (행동 보존, 성능 특성만 변화)
6. **docstring 경고**:
   ```
   to_ir() returns a cached frozen IR. Modifying it raises ValidationError.
   For independent copies, use `ir.model_copy(deep=True)`.
   ```

**frozen=True 가 핵심**: 검증자가 지적한 실패 모드 5개 중 F1 (aliasing), F5 (deepcopy surprise) 는 frozen 으로 즉시 해소. F2 (memory) 는 사용자가 `del` 로 통제. F3 (concurrent race) 는 unsendable 로 원천 차단. F4 (parametrized) 는 "그때 결정 연기" 로 처리.

### 출처

- [PyO3 pyclass attributes](https://pyo3.rs/main/class.html)
- [Rust `std::cell::OnceCell`](https://doc.rust-lang.org/std/cell/struct.OnceCell.html)
- [Pydantic V2 `ConfigDict.frozen`](https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.frozen)

---

## 8. JSON Schema `$id` 호스팅 — GitHub Pages + 불변 경로 + SchemaStore + In-package

### 수행자 권고

**복합 전략**:

1. `$id` URL: `https://danmeon.github.io/rhwp-python/schema/hwp_ir/v1/schema.json`
   - 버전 디렉토리 구조 (`v1/schema.json`) — 하위 경로 확장 용이
2. **In-package schema** 1차: `python/rhwp/ir/schema/hwp_ir_v1.json` via `importlib.resources` — 네트워크 없이 `jsonschema.validate()` 가능
3. **SchemaStore catalog 등록** (외부 URL 방식) — VSCode/JetBrains 자동 인식
4. **CI 자동 배포** (`.github/workflows/publish.yml`) with `keep_files: true` — 이전 버전 URL 보존

### 검증자 실증 우려

**GitHub Pages 장애 기록 있음**:
- 2026-04-13: Pages 에러율 평균 10.58%, 피크 12.77%, ~17.5M 실패 요청 (97분, DNS 기록 삭제로)

**개인 계정 URL (`danmeon.github.io`) 리스크**:
- GitHub 공식 문서 경고: 계정 rename 시 redirect 일부만 유지되며, 동일 이름 squatter 가 redirect 덮어쓰기 가능
- Lando/VA.gov 등 실제 library-spec repo 이전 시 URL 대량 교체 사례 (PR 링크 증거 있음)

### 최종 결정

**수행자 복합 전략 채택 + 검증자 완화책 강화**:

| 항목 | 결정 |
|---|---|
| 1차 배포 | **In-package JSON 파일** (`python/rhwp/ir/schema/hwp_ir_v1.json`) — 네트워크 fetch 불필요 |
| 공개 URL | **`https://danmeon.github.io/rhwp-python/schema/hwp_ir/v1/schema.json`** (개인 계정 리스크 수용) |
| 경로 정책 | **Immutable paths** — v1 URL 은 영구, breaking change 는 `v2/schema.json` 으로 새 URL (CI guard 로 v1 수정 차단) |
| Content-addressed alias | `hwp_ir_v1-sha256-<hash>.json` 도 발행 — pin 하고 싶은 소비자용 |
| SchemaStore 등록 | **v0.2.0 GA 직후 PR 제출** — external URL 방식 (스키마 파일은 우리 repo 에 유지) |
| Future | 프로젝트가 성장하면 GitHub org (`rhwp-python`) 로 이전 검토. v0.2.0 에는 블로커 아님 |

### 리스크 수용 근거

- **In-package 가 1차** 이므로 공개 URL 이 다운되어도 `rhwp-python` 사용자는 영향 없음. URL 은 "외부 도구 편의" 용
- SchemaStore 외부 URL 방식이라 URL 이전 시 catalog PR 한 번만 수정하면 됨
- 비공식 커뮤니티 바인딩 단계에서 GitHub org 생성은 scope creep — 실제 수요 생긴 후 이전

### SchemaStore 등록 절차 (참조)

1. `SchemaStore/schemastore` fork, `src/api/json/catalog.json` 알파벳 순 삽입:
   ```json
   {
     "description": "HWP/HWPX document intermediate representation",
     "fileMatch": ["*.hwp_ir.json"],
     "name": "rhwp Document IR",
     "url": "https://danmeon.github.io/rhwp-python/schema/hwp_ir/v1/schema.json"
   }
   ```
2. `src/test/hwp_ir/` 에 양성 테스트 파일 추가
3. PR 심사 ~2주

### 출처

- [SchemaStore CONTRIBUTING](https://github.com/SchemaStore/schemastore/blob/master/CONTRIBUTING.md)
- [W3C Cool URIs for the Semantic Web](https://www.w3.org/TR/cooluris/)
- [GitHub Pages status history](https://www.githubstatus.com/history) — 2026-04-13 incident
- [GitHub username rename limits](https://docs.github.com/en/account-and-profile/concepts/username-changes)

---

## 변경 파급 — ir.md 본문 교정 목록

본 결정 사항 적용 시 [v0.2.0/ir.md](../../roadmap/v0.2.0/ir.md) 본문에서 교정 필요한 지점:

1. **§ Provenance** — `char_start/char_end` 를 UTF-16 → codepoint 로 변경, 필드명에서 `_utf16` 접미사 제거
2. **§ 스키마 버저닝** — `Literal["1.0"]` → `Annotated[str, StringConstraints(...)]` + validator
3. **§ 블록 태그드 유니온** — `UnknownBlock` catch-all variant 추가, callable Discriminator 설명
4. **§ Python API** — `doc.body` / `doc.furniture` 속성 + `iter_blocks(scope=, recurse=)` 시그니처
5. **§ Rust 경계 패턴** — `OnceCell<PyObject>` 캐시 추가, IR 모델 `frozen=True` 선언
6. **§ JSON Schema 공개** — SchemaStore 등록 계획, 불변 경로 정책, content-addressed alias
7. **§ 미결 결정 사항** → **§ 결정 사항 (요약)** 으로 교체, 상세는 본 리서치 문서 링크
