# Stage S1 — Pydantic 모델 초안 (완료)

**Status**: Frozen · **GA**: v0.2.0 · **Last updated**: 2026-04-24

**작업일**: 2026-04-24
**계획 문서**: [roadmap/v0.2.0/ir.md](../../../roadmap/v0.2.0/ir.md) §구현 스테이지 분할
**설계 근거**: [design/v0.2.0/ir-design-research.md](../../../design/v0.2.0/ir-design-research.md)

## 스코프

Document IR v1 의 **공개 데이터 모델 (Pydantic V2)** 만. Rust 바인딩 (S2), JSON Schema export (S4), `Document.to_ir()` 메서드 (S2) 는 본 스테이지 범위 밖.

## 산출물

| 파일 | 라인 | 내용 |
|---|---|---|
| `python/rhwp/ir/__init__.py` | 7 | docstring only (프로젝트 규칙 — 순환 import 방지) |
| `python/rhwp/ir/__init__.pyi` | 57 | 타입 체커용 `__all__` 재-export |
| `python/rhwp/ir/nodes.py` | 288 | 10개 모델 + `Block` tagged union + `model_rebuild()` |
| `tests/test_ir_schema.py` | 297 | 35 테스트 케이스 (파라미터화 포함) |
| `pyproject.toml` | — | `[project] dependencies = ["pydantic>=2.5,<3"]` 추가 |
| `docs/roadmap/v0.2.0/ir.md` | — | §노드 타입 섹션 S1 최소 필드 스펙 보강 |

## 구현된 타입 (nodes.py)

- **Leaf**: `Provenance`, `InlineRun`, `DocumentMetadata`, `Section`
- **블록**: `ParagraphBlock` (kind="paragraph"), `TableBlock` (kind="table"), `UnknownBlock` (catch-all, v1.0 포함)
- **재귀**: `TableCell` (blocks: list["Block"]) ↔ `Block` ↔ `TableBlock.cells: list[TableCell]` — 문자열 전방 참조 + 파일 하단 `model_rebuild()` 3회
- **루트**: `HwpDocument`, `Furniture`
- **유니온**: `Block = Annotated[Union[...], Discriminator(_block_discriminator)]` — callable discriminator 로 미지 `kind` 를 `UnknownBlock` 으로 라우팅
- **버전**: `SchemaVersion = Annotated[str, StringConstraints(pattern=r"^\d+\.\d+(\.\d+)?$")]` + `@field_validator` — major 상향 시 `UserWarning`

## S1 확정 결정 사항 (ir.md 에 소급 반영)

| 타입 | v0.2.0 S1 필드 | 이월 |
|---|---|---|
| `Section` | `section_idx: int` 만 | 용지·단·헤더 레퍼런스는 S2 Rust 매핑 시 MINOR 확장 |
| `DocumentMetadata` | `title` / `author` / `creation_time` / `modification_time` — 전부 `str \| None` | `datetime` 교체는 v0.3.0 MINOR 호환 |
| `TableBlock.caption` | `str \| None` (단순 텍스트) | 복합 캡션 (캡션 안의 블록) 은 v0.3.0+ |

## 비타협 제약 준수

- 모든 IR 모델 `ConfigDict(extra="forbid", frozen=True)`. `UnknownBlock` 만 `extra="allow"` 예외
- `from __future__ import annotations` 사용 **없음**
- `Field(ge=/le=/gt=/lt=)` 사용 **없음** — 범위 서술은 `description`
- Python 3.9 런타임 호환: `Optional[T]` / `Union[T, U]` 사용 (PEP 604 `T | None` 은 3.10+)
- `list[T]` / `tuple[T, ...]` 는 PEP 585 (3.9+ OK) 로 내장 타입 사용

## 검증

| 검사 | 결과 |
|---|---|
| `uv run pytest tests/test_ir_schema.py -v` | **35 passed** |
| `uv run pytest -m "not slow"` | **102 passed** (회귀 없음 — 기존 67 + 신규 35) |
| `uv run ruff check python/rhwp/ir/ tests/test_ir_schema.py` | clean |
| `uv run pyright python/rhwp/ir/ tests/test_ir_schema.py` | **0 errors** |
| `uv run pyright python/ tests/` | 의도된 `type_check_errors.py` 4 errors 만 (CLAUDE.md 규약) |
| `code-reviewer` fresh-context 검증 (16개 항목) | 전원 통과, Critical/Minor/Nitpick 0건 |

## 테스트 커버리지 매핑 (ir.md §단위 테스트 → 실제 케이스)

| ir.md 요구 | 테스트 |
|---|---|
| 직렬화 왕복 (HwpDocument/ParagraphBlock/TableBlock) | `test_hwp_document_roundtrip`, `test_paragraph_block_roundtrip`, `test_table_block_simple_roundtrip` |
| discriminator 분기 — 잘못된 kind | `test_discriminator_routes_unknown_kind`, `test_discriminator_routes_known_kinds` |
| 재귀 3단 (중첩 표) | `test_table_nested_three_levels` |
| `extra="forbid"` 실효성 | `test_extra_forbid_raises_on_unknown_field[8 parametrized]` |
| `schema_version` pattern 검증 | `test_schema_version_accepts_valid[4]`, `test_schema_version_rejects_invalid[7]`, `test_schema_version_warns_on_future_major`, `test_schema_version_minor_bump_does_not_warn` |
| `frozen=True` | `test_frozen_raises_on_mutation`, `test_frozen_unknown_block_cannot_be_mutated` |
| codepoint offset (이모지 SMP 호환) | `test_provenance_char_offsets_are_codepoint_based` |

LLM strict-mode 스키마 conformance / `jsonschema` meta-validation 은 S4 (JSON Schema export) 이후.

## S2 진입 조건 (인수인계)

S2 는 "Rust → Python dict → Pydantic `model_validate`" 매핑을 `src/document.rs` + 신규 `src/ir.rs` 에 작성. S1 에서 고정한 계약:

1. **모든 IR 모델 frozen** — S2 에서 `Document.to_ir()` 의 Rust `OnceCell<PyObject>` 캐시와 함께 aliasing 방어 완성
2. **`char_start`/`char_end` codepoint** — S2 Rust 바인딩이 상류 UTF-16 `char_offsets` → codepoint 변환 `to_ir()` 시점 1회 수행
3. **`body` / `furniture` 분리** — Rust 매퍼는 머리글/꼬리말 본문을 식별해 `furniture` 쪽으로 라우팅 (v0.2.0 은 빈 리스트 출고)
4. **`Section` / `DocumentMetadata` 최소 필드** — S2 에서 상류 Rust 타입 매핑 시 필드 확장은 MINOR 호환

## 참조

- 상위 설계: [roadmap/v0.2.0/ir.md](../../../roadmap/v0.2.0/ir.md)
- 결정 사항 증거: [design/v0.2.0/ir-design-research.md](../../../design/v0.2.0/ir-design-research.md)
- 상류 타입 (S2 에서 매핑): `external/rhwp/src/model/{document,paragraph,table}.rs`
