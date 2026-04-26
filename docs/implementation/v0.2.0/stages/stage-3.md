# Stage S3 — Table 통합 (완료)

**Status**: Frozen · **GA**: v0.2.0 · **Last updated**: 2026-04-24

**작업일**: 2026-04-24
**계획 문서**: [roadmap/v0.2.0/ir.md](../../../roadmap/v0.2.0/ir.md) §테이블 표현 + §구현 스테이지 분할
**설계 근거**: [design/v0.2.0/ir-design-research.md](../../../design/v0.2.0/ir-design-research.md) §2 (HTML 직렬화 위치)

## 스코프

Rust `Control::Table` → `TableBlock` 추출. 3중 표현 (cells + HTML + text) 병기. 중첩 표 재귀 지원.

**이월 확정**:
- text/table 정확 interleaving (컨트롤 문자 0x0B 위치 기반) — v0.3.0+
- row_header vs column_header 구분 — HWP 에 정보 없음 (DocLayNet 어휘는 유지)
- `PictureBlock` / `FormulaBlock` / `FootnoteBlock` — v0.3.0+
- `py.import("rhwp.ir.nodes")` 모듈 레벨 캐싱 — v0.3.0+ 리팩토링

## 산출물

| 파일 | 변경 | 요점 |
|---|---|---|
| `src/ir.rs` | 재작성 (~370줄) | `flatten_paragraph_to_blocks` / `build_table_block` / `build_table_cells` / `table_to_html` / `table_to_text` / `escape_html` / `cell_role` / Rust unit tests |
| `python/rhwp/ir/nodes.py` | 보강 | `TableCell.grid_index` 와 `role` 필드에 description 추가 (S3 의미 명시) |
| `tests/test_ir_roundtrip.py` | 수정 | 기존 16 테스트를 S3 contract 에 맞게 — ParagraphBlock 필터 추가 (body 에 TableBlock 이 섞임) |
| `tests/test_ir_tables.py` | 신규 (11 테스트) | TableBlock 전용 — 출현, 필드, HTML 구조, text 구조, 셀 좌표/span, 중첩, Provenance 공유, JSON 왕복 |

## 핵심 구현 결정

### 1. Paragraph 평탄화 — `flatten_paragraph_to_blocks`

한 Paragraph 는 `[ParagraphBlock, TableBlock₁, TableBlock₂, ...]` 로 body 에 append. Controls 안의 `Control::Table` 만 추출 (다른 variant 는 v0.3.0+).

Provenance 는 같은 `(section_idx, para_idx)` 공유 — 같은 Paragraph 에서 파생된 것을 추적 가능. TableBlock 의 `char_start` / `char_end` 는 `None` (문단 텍스트 범위 밖).

### 2. HTML 직렬화 (Rust 측)

설계 근거: ir-design-research.md §2 — Unstructured / Docling 모두 Python layer. 그러나 우리는 Rust 가 이미 dict 를 만드는 경로라 **Rust 에서 직접 생성**. "잠정, 상류 PR 동시 추진" 원칙은 동일.

```rust
// attribute 순서 고정 (rowspan → colspan, 1 생략) — dedup hash 안정성
if cell.row_span > 1 { html.push_str(" rowspan=\"N\""); }
if cell.col_span > 1 { html.push_str(" colspan=\"N\""); }
```

HTML entity escape: `<`, `>`, `&`, `"`.

### 3. `<tr>` 경계 알고리즘 — "관찰된 row" 모델

`current_row: Option<u16>` 이 cell.row 가 바뀔 때 `<tr>` 열고 닫음. **row-span 으로 덮인 중간 행은 anchor cell 없음 → `<tr>` 미방출**. HTML 표준에서 rowspan 이 다음 row 를 자동 span 하므로 렌더링 무결. 테스트는 `<tr>` 개수 ≤ rows 로 완화.

### 4. TableCell 재귀 — 중첩 표

`TableCell.blocks` 는 `flatten_paragraph_to_blocks` 를 재귀 호출 — 셀 내부 Paragraph 에서 또 TableBlock 이 추출될 수 있음. 실제 HWPX 샘플에는 중첩 표가 없어 테스트는 `pytest.skip()` 분기.

### 5. role 매핑 단순화

HWP `Cell.is_header: bool` 만 제공 — row vs column 구분 없음. DocLayNet 어휘 중 `column_header` / `data` 만 사용 (v0.2.0). `row_header` / `layout` 은 스키마 enum 에 유지 (S3+ 외부 heuristic 이나 사용자 annotation 레이어에서 채울 수 있음).

### 6. Caption — 단순 텍스트만

상류 `Caption.paragraphs` 의 text 를 이어붙인 문자열. 복합 캡션 (캡션 안의 블록) 은 v0.3.0+ 이월.

## 검증

| 검사 | 결과 |
|---|---|
| `uv run pytest tests/test_ir_tables.py -v` | **11 passed** |
| `uv run pytest tests/test_ir_roundtrip.py -v` | **16 passed** |
| `uv run pytest -m "not slow"` | **128 passed** (S1 35 + S2/S3 roundtrip 16 + S3 tables 11 + 기존 66) |
| `cargo test --lib` | **5 passed** (escape_html × 3 + utf16_to_cp × 2) |
| `cargo clippy --all-targets -- -D warnings` | clean |
| `uv run pyright python/ tests/` | 의도된 4 errors 만 (`type_check_errors.py`) |
| `code-reviewer` fresh-context S3 검증 | **Critical 0**, Minor 5 → 3건 즉시 반영 |

## 검증자 지적 반영

| # | 이슈 | 조치 |
|---|---|---|
| M1 | `<tr>` 개수 == rows 계약이 row-span-only row 에서 실패 가능 | 테스트 완화 (`<=`), 주석 보강 |
| M3 | `test_table_html_escapes_special_chars` 빈 본문 — escape 함수 커버리지 0 | Python 테스트 삭제, Rust unit tests 3개 추가 (`escape_html_*`) |
| M4 | `cell_role` 이 `column_header`/`data` 두 값만 반환 | Pydantic 필드 description 에 v0.2.0 매핑 정책 명시 |
| M5 | `TableCell.grid_index` 의미 (anchor cell flat index) 가 상류 cell_grid 와 다름 | Pydantic 필드 description 추가 |

이월:
- **Nitpick 2**: 중첩 ParagraphBlock 의 para_idx 는 외부 para_idx 공유 — 정밀 식별자 v0.3.0+ 검토
- **Nitpick 3**: `py.import` 모듈 캐싱 — v0.3.0+ 리팩토링
- **M2**: 내 브리프의 "12 테스트" 는 오기 (실제 11) — stage-3.md 에 정정됨

## 테스트 커버리지 (새 파일)

**`tests/test_ir_tables.py` (11)**:
| 테스트 | 검증 |
|---|---|
| `test_hwpx_sample_has_tables` | 샘플에 TableBlock 출현 (9개) |
| `test_table_block_fields_populated` | rows/cols/cells 크기, kind, HTML 접두/말미 |
| `test_table_html_tr_td_structure` | `<tr>` 쌍 + 셀 마커 개수 == cells |
| `test_table_text_row_and_cell_separators` | `\n` 개수 ≤ rows-1 |
| `test_table_cells_have_valid_coordinates` | row/col 범위, span 경계, grid_index 공식, role enum |
| `test_table_cells_blocks_are_paragraph_or_table` | TableCell.blocks 가 ParagraphBlock 또는 중첩 TableBlock 만 |
| `test_table_block_shares_provenance_with_paragraph` | 직전 ParagraphBlock 과 (section_idx, para_idx) 공유 |
| `test_table_block_survives_json_roundtrip` | to_ir_json → model_validate_json 왕복 동등성 |
| `test_nested_tables_are_block_compatible` | 중첩 있으면 스키마 계약 동일 (샘플에 없으면 skip) |
| `test_hwp5_sample_tables_follow_contract` | HWP5 샘플에 표 있으면 동일 계약 (없으면 skip) |

**Rust unit tests (`src/ir.rs`)** (5):
- `escape_html_all_special_chars` — `<b>A & B</b>` → `&lt;b&gt;A &amp; B&lt;/b&gt;`
- `escape_html_quote` — 따옴표 escape
- `escape_html_plain_passes_through` — ASCII + 한글 무변환
- `utf16_to_cp_sentinel_returns_fallback` — `u32::MAX` → fallback_end
- `utf16_to_cp_matches_first_ge` — SMP 이모지 혼재 오프셋 매핑

## S4 진입 조건 (인수인계)

S4 는 "JSON Schema 공개" — `python/rhwp/ir/schema.py` + CI 배포.

1. **`export_schema()`** — `HwpDocument.model_json_schema(mode="serialization")` + `$id` 주입 + `$schema` Draft 2020-12
2. **In-package JSON** — `python/rhwp/ir/schema/hwp_ir_v1.json` + `pyproject.toml [tool.maturin] include`
3. **`load_schema()`** — `importlib.resources` 로 in-package 스키마 로드 (네트워크 불필요)
4. **GitHub Pages 배포 파이프라인** — `.github/workflows/publish-schema.yml`
5. **LLM strict-mode conformance 테스트** — `tests/test_ir_strict_schema.py`: `additionalProperties: false`, 모든 property required (nullable → `T | null`), `minimum`/`maximum` 키워드 부재, `$ref` 순환 참조 해소

S3 에서 고정한 계약:
- 모든 Pydantic 모델 `extra="forbid"` → JSON Schema 가 `additionalProperties: false` 자동 생성
- `UnknownBlock` 만 `extra="allow"` — strict mode 에서 이 variant 의 `additionalProperties` 는 `true` 로 나옴 (의도된 동작, 문서화 필요)
- `TableCell.grid_index` / `TableCell.role` 에 추가된 description 이 JSON Schema 에 반영됨

## 참조

- 상위 설계: [roadmap/v0.2.0/ir.md](../../../roadmap/v0.2.0/ir.md)
- 이전 스테이지: [stage-1.md](stage-1.md), [stage-2.md](stage-2.md)
- 상류 타입:
  - `external/rhwp/src/model/table.rs` (Table, Cell, TableZone, VerticalAlign)
  - `external/rhwp/src/model/control.rs` (Control enum, Control::Table variant)
  - `external/rhwp/src/model/shape.rs` (Caption)
