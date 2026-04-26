# Stage S2 — Rust → dict 매퍼 + `Document.to_ir()` 바인딩 (완료)

**Status**: Frozen · **GA**: v0.2.0 · **Last updated**: 2026-04-24

**작업일**: 2026-04-24
**계획 문서**: [roadmap/v0.2.0/ir.md](../../../roadmap/v0.2.0/ir.md) §구현 스테이지 분할
**설계 근거**: [design/v0.2.0/ir-design-research.md](../../../design/v0.2.0/ir-design-research.md) §7 (캐싱 전략)

## 스코프

Rust `Document` → Python `dict` → Pydantic `HwpDocument.model_validate` 매퍼.
Paragraph 순회 + InlineRun 런 분할 + Provenance 채움. Rust `OnceCell` lazy 캐시.

**S3 이월**: Table 분리 추출 (`TableBlock`), controls 처리, 중첩 표. **S5 이월**: `iter_blocks` / LangChain 어댑터.

## 산출물

| 파일 | 내용 |
|---|---|
| `src/ir.rs` (신규) | `build_hwp_document()`, `build_paragraph_block()`, `build_inline_runs()`, `utf16_to_cp()`, `make_inline_run()` |
| `src/document.rs` (수정) | `ir_cache: OnceCell<Py<PyAny>>` 필드 + `to_ir()` / `to_ir_json(*, indent=None)` 메서드 |
| `src/lib.rs` (수정) | `mod ir;` 연결 |
| `python/rhwp/__init__.pyi` (수정) | `to_ir` / `to_ir_json` 타입 힌트 + `_HwpDocument` re-export alias |
| `tests/test_ir_roundtrip.py` (신규) | 15 테스트 — 실제 `aift.hwp` / `table-vpos-01.hwpx` 로 통합 검증 |

## 핵심 구현 결정

### 1. `OnceCell` 수동 get/set 패턴

`std::cell::OnceCell::get_or_try_init` 은 **nightly-only** (rust-lang issue #109737). Stable 대안으로 수동 패턴:

```rust
if let Some(cached) = self.ir_cache.get() {
    return Ok(cached.clone_ref(py));
}
let ir = ir::build_hwp_document(py, self.inner.document())?;
self.ir_cache.set(ir).expect("ir_cache was empty just above");
Ok(self.ir_cache.get().expect("ir_cache was just set").clone_ref(py))
```

`#[pyclass(unsendable)]` 가 단일 스레드 접근을 보증 — `get()` → `set()` 사이 race condition 불가. `expect` 는 단일 스레드 불변식으로 안전.

### 2. UTF-16 → codepoint 변환

상류 `CharShapeRef.start_pos` 는 **UTF-16 code unit** 위치. `Provenance` / `InlineRun.text` 는 **codepoint** 기준 (ir.md §3). `utf16_to_cp()` 가 `Paragraph.char_offsets` 로 선형 변환 (O(n), 캐시됨):

```rust
fn utf16_to_cp(char_offsets: &[u32], utf16: u32, fallback_end: usize) -> usize {
    if utf16 == u32::MAX { return fallback_end; }
    for (i, &off) in char_offsets.iter().enumerate() {
        if off >= utf16 { return i; }
    }
    fallback_end
}
```

### 3. InlineRun 런 분할 (방어적)

- `char_shapes` 순회하여 각 엔트리의 `[start_utf16, next_start_utf16)` 구간을 codepoint 범위로 변환
- 해당 codepoint 범위의 텍스트를 `InlineRun.text` 로 출고, `raw_style_id = char_shape_id`
- **Prefix 방어**: 첫 shape 의 `start_pos > 0` 이면 앞부분 텍스트를 style-less 런으로 prepend — HWP 관례는 `start_pos=0` 이지만 손상 파일 대비
- **Fallback**: `char_shapes` 가 비었거나 전부 컨트롤 뒤 위치면 단일 런으로 폴백

### 4. InlineRun 서식 플래그 매핑

상류 `CharShape` 필드 → `InlineRun`:

| Python | Rust |
|---|---|
| `bold` | `CharShape.bold: bool` |
| `italic` | `CharShape.italic: bool` |
| `strikethrough` | `CharShape.strikethrough: bool` |
| `underline` | `CharShape.underline_type != UnderlineType::None` |
| `raw_style_id` | `CharShapeRef.char_shape_id: u32` |
| `href` / `ruby` | 항상 `None` — 상류 Control 트리 매핑은 S3+ |

### 5. v0.2.0 S2 에서 비어있는 것

- `DocumentMetadata.{title,author,creation_time,modification_time}` — 전부 `None`. HWP Summary Information / DocProperties 매핑은 S3+.
- `Furniture.{page_headers,page_footers,footnotes}` — 전부 빈 리스트. 본문 파싱은 v0.3.0+.
- `source: Optional[Provenance]` — `None`.
- `TableBlock` — S2 에서는 모든 문단이 `ParagraphBlock`. 표 있는 문단도 `controls` 무시하고 text 만 추출. S3 에서 `Control::Table` → `TableBlock` 분리.

## 검증

| 검사 | 결과 |
|---|---|
| `uv run pytest tests/test_ir_roundtrip.py -v` | **15 passed** |
| `uv run pytest -m "not slow"` | **117 passed** (S1 35 + S2 15 + 기존 67) |
| `cargo clippy --all-targets -- -D warnings` | clean |
| `uv run pyright python/ tests/` | 의도된 `type_check_errors.py` **4 errors** 만 |
| `code-reviewer` fresh-context 검증 | **Critical 0** — 전 영역 설계와 일치 |

## 검증자 지적 반영 (Minor/Nitpick → 즉시 수정)

| 항목 | 조치 |
|---|---|
| `PyAny` 를 `prelude` 와 `types::` 양쪽에서 import 중복 | `types::` 쪽 제거 |
| 첫 shape `start_pos > 0` 인 손상 파일의 prefix 누락 가능성 | style-less 런으로 prepend 하는 방어 코드 추가 |
| `.pyi` 의 `to_ir` / `to_ir_json` 에 `Raises` 섹션 없음 | `pydantic.ValidationError` / `ImportError` 명시 |
| 주석 섹션 번호 "§3" 모호 | "§단락 내 InlineRun + §3 char 오프셋" 로 명시화 |

**이월** (S3 검토):
- `py.import("rhwp.ir.nodes")` + `getattr("HwpDocument")` 를 매 호출마다 수행 — `OnceCell` 덕에 실질적으로 1회지만, S3 에서 `TableBlock` import 추가 시 함께 lazy static `Py<PyType>` 로 리팩토링.

## 테스트 커버리지 (`tests/test_ir_roundtrip.py`)

| 테스트 | 검증 |
|---|---|
| `test_to_ir_returns_hwp_document` | 반환 타입 + schema_name/schema_version |
| `test_to_ir_caches_same_object` | `OnceCell` 캐싱 — 재호출 시 `is` 동일 |
| `test_ir_section_count_matches_document` | `len(ir.sections)` == `parsed.section_count`, `section_idx` 순차 |
| `test_ir_body_paragraph_count_matches` | 모든 body 가 `ParagraphBlock`, `len(ir.body)` == `parsed.paragraph_count` |
| `test_ir_body_text_joined_matches_extract_text` | 빈 문단 제외 개행 join 결과가 `extract_text()` 와 일치 |
| `test_provenance_monotonic` | section_idx 단조, 같은 섹션 내 para_idx 순차 증가 (섹션 경계에서 0 재시작) |
| `test_provenance_char_end_matches_text_length` | codepoint 기준 (`len(block.text)`) 일치, `page_range is None` |
| `test_inline_run_text_concatenates_to_paragraph_text` | 런 `text` 이어붙인 결과 == paragraph text (prefix 방어 포함) |
| `test_inline_run_has_styled_runs` | 최소 하나의 run 이 `raw_style_id` 보유 |
| `test_to_ir_on_hwpx_sample` | HWPX 샘플도 동일 계약 |
| `test_to_ir_json_parses_back` | `to_ir_json()` → `model_validate_json` 왕복 |
| `test_to_ir_json_indent_option` | `indent=2` 시 개행 포함, 없으면 한 줄 |
| `test_ir_is_frozen` | 반환 IR 수정 시 `ValidationError` |
| `test_furniture_is_empty` | v0.2.0 S2 는 전부 빈 리스트 |
| `test_metadata_fields_are_none` | v0.2.0 S2 는 전부 `None` |

## S3 진입 조건 (인수인계)

S3 는 "Table 통합" — `Control::Table` 을 `TableBlock` 으로 분리 추출.

1. **Paragraph.controls 순회** — `Control::Table(Table)` variant 판별
2. **Table 구조 → TableCell 배열** — 상류 `Table` 의 cells 순회, `row/col/row_span/col_span/grid_index` 채움
3. **HTML 직렬화** — `html.escape()` + attribute 정렬 (dedup hash 안정성, ir.md §2 결정사항)
4. **중첩 표** — `TableCell.blocks: list[Block]` 재귀 — 셀 내부 문단을 다시 `ParagraphBlock` 으로
5. **본문 평탄화** — 표가 있는 문단에서 표와 텍스트를 순서대로 body 에 배치 (컨트롤 문자 `0x0B` 위치 기준)

S2 에서 고정한 계약:
- Paragraph 단위 블록 분리 — S3 에서 "한 Paragraph → 여러 Block" 확장 시 Provenance 는 같은 `(section_idx, para_idx)` 공유 (char_start/char_end 로 구분)
- Rust 측 `OnceCell` 캐시 — S3 의 새 경로도 `build_hwp_document` 하위에서 호출되므로 캐시 공유
- `lazy_static` 리팩토링: `Py<PyType>` 캐시 도입 시점

## 참조

- 상위 설계: [roadmap/v0.2.0/ir.md](../../../roadmap/v0.2.0/ir.md)
- S1 완료 기록: [stages/stage-1.md](stage-1.md)
- 상류 타입 (S2 매핑 기준):
  - `external/rhwp/src/model/paragraph.rs` (Paragraph, CharShapeRef, char_offsets)
  - `external/rhwp/src/model/style.rs` (CharShape, UnderlineType)
  - `external/rhwp/src/model/document.rs` (Document, DocInfo)
