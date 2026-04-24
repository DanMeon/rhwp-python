# Stage S4 — JSON Schema 공개 (완료)

**작업일**: 2026-04-24
**계획 문서**: [roadmap/v0.2.0/ir.md](../../../roadmap/v0.2.0/ir.md) §JSON Schema 공개
**설계 근거**: [design/v0.2.0/ir-design-research.md](../../../design/v0.2.0/ir-design-research.md) §8 ($id 호스팅)

## 스코프

- `export_schema()` / `load_schema()` + in-package JSON 파일 + GitHub Pages 배포 파이프라인
- Draft 2020-12 meta-validation + 실제 인스턴스 validation 테스트
- Pydantic `oneOf` + `UnknownBlock` 불일치 해결 — `_harden_unknown_variant()` 후처리로 discriminator 효과 에뮬레이션

**이월 (v0.3.0+ 검토)**:
- **LLM strict-mode 완전 호환** — Pydantic V2 기본 출력은 `default` 필드를 `required` 에서 제외. OpenAI strict 는 "모든 property required" 요구. 후처리 변환기 (`export_schema(strict=True)`) 는 **실효성 평가 후** 도입 검토
- **SchemaStore 카탈로그 등록** — v0.2.0 GA 직후 PR
- **Content-addressed alias** — GA 이후

## 산출물

| 파일 | 변경 | 요점 |
|---|---|---|
| `python/rhwp/ir/schema.py` (신규) | - | `export_schema()` / `load_schema()` / `SCHEMA_ID` / `SCHEMA_DIALECT` / `_harden_unknown_variant()` / `__main__` CLI |
| `python/rhwp/ir/schema/hwp_ir_v1.json` (신규, 510줄) | - | In-package 1차 배포 JSON |
| `python/rhwp/ir/__init__.pyi` (수정) | - | `export_schema` / `load_schema` / `SCHEMA_ID` / `SCHEMA_DIALECT` 재노출 |
| `pyproject.toml` (수정) | - | `[tool.maturin] include` 에 `ir/schema/*.json` 추가 (wheel + sdist) + `jsonschema>=4` 를 testing group |
| `tests/test_ir_schema_export.py` (신규, 14 테스트) | - | Draft 2020-12 meta-validation + sync 검증 + 실제 인스턴스 validation |
| `.github/workflows/publish-schema.yml` (신규) | - | verify-sync 가드 + GitHub Pages 배포 (불변 경로 자동) |
| `.github/workflows/ci.yml` (수정) | - | test-core-only skip 카운트 2로 업데이트 |

## 핵심 구현 결정

### 1. `$id` / `$schema` 주입

```python
SCHEMA_ID = "https://danmeon.github.io/rhwp-python/schema/hwp_ir/v1/schema.json"
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
```

`export_schema()` 는 dict 순서를 유지하기 위해 새 dict 로 재구성 — `$schema` / `$id` 가 맨 앞 배치.

### 2. `_harden_unknown_variant()` — discriminator 에뮬레이션

**문제**: Pydantic V2 callable Discriminator 는 JSON Schema `discriminator` 키워드로 표현 불가. 기본 출력은 단순 `oneOf` 이라 `UnknownBlock` (extra="allow") 이 `ParagraphBlock`/`TableBlock` 인스턴스에도 매치 → oneOf 가 "정확히 하나" 조건 실패.

**해결**: known variant (`kind.const` 값이 있는) 들의 kind 를 수집해, `UnknownBlock.properties.kind` 에 `not.enum: [known kinds...]` 주입. JSON Schema Draft 2020-12 valid 키워드이고 `Draft202012Validator.check_schema` 통과.

**자동성**: v0.3.0 에서 `PictureBlock` 추가 시 `_harden_unknown_variant()` 가 자동으로 `not.enum` 에 포함 — 수동 업데이트 불필요.

### 3. In-package JSON — 1차 배포 채널

- `python/rhwp/ir/schema/hwp_ir_v1.json` repo 체크인
- `[tool.maturin] include` wheel + sdist 양쪽 포함
- `load_schema()` 가 `importlib.resources.files("rhwp.ir")` 로 로드 — 네트워크 불필요
- `tests/test_ir_schema_export.py::test_load_schema_matches_export_schema` 가 sync 검증
- 재생성: `uv run python -m rhwp.ir.schema > python/rhwp/ir/schema/hwp_ir_v1.json`

### 4. LLM strict-mode 호환성 — 부분 지원, 완전 이월

**지원됨 (v0.2.0)**:
- `additionalProperties: false` 전 노드 적용 (UnknownBlock 제외)
- `minimum`/`maximum`/`exclusiveMinimum`/`exclusiveMaximum` 키워드 전부 부재 (CLAUDE.md "NEVER use ge/le/gt/lt" 의 결과)
- Enum-like 필드는 `Literal` 로 `const`/`enum` 생성

**미지원 (v0.3.0+)**:
- OpenAI strict 는 "**모든** property 가 required" 요구. Pydantic V2 기본 동작상 `default` 있는 필드는 required 에서 제외. 해결하려면 후처리 변환기 (`optional` 필드를 `required` 에 넣고 default 를 `anyOf: [T, null]` 로 표현) 필요. 실험으로 실효성 (생성 품질 vs 스키마 복잡도) 평가 후 `export_schema(strict=True)` 옵션 도입 검토.

**문서화**: `schema.py` 모듈 docstring 에 명시 — CLAUDE.md 전역 "Structured Output MUST use strict mode" 가 Writer 관점 규칙인 반면, 우리는 **Schema Producer** 이고 v0.2.0 생성 스키마는 strict mode 에 직접 꽂을 수 없음을 고지.

### 5. GitHub Pages 불변 경로 — 자동 루프

verify-sync 가드: CI 가 `diff -u` 로 repo JSON vs 코드 출력 비교, 불일치 시 deploy 차단.

**Critical C1 반영 (code-reviewer 지적)**: v2 도입 시 v1 이 `actions/deploy-pages@v4` 의 replace-all 로 덮여 사라지는 위험. Workflow 에 **자동 복사 루프** 추가:

```bash
for f in python/rhwp/ir/schema/hwp_ir_v*.json; do
    name=$(basename "$f" .json)
    ver="${name#hwp_ir_}"
    mkdir -p "pages/schema/hwp_ir/$ver"
    cp "$f" "pages/schema/hwp_ir/$ver/schema.json"
done
```

v2 도입 시 `hwp_ir_v2.json` 만 추가하면 워크플로우 수정 없이 v1/v2 공존 — v1 URL 은 영구 유지.

## 검증

| 검사 | 결과 |
|---|---|
| `uv run pytest tests/test_ir_schema_export.py -v` | **14 passed** |
| `uv run pytest -m "not slow"` | **142 passed** (S1 35 + S2/S3 16 + S3 tables 11 + S4 14 + 기존 66) |
| `cargo test --lib` | **5 passed** (Rust unit tests — escape_html, utf16_to_cp) |
| `cargo clippy --all-targets -- -D warnings` | clean |
| `uv run pyright python/ tests/` | 의도된 4 errors 만 |
| `uv run python -m rhwp.ir.schema \| diff` | no diff (sync OK) |
| `Draft202012Validator.check_schema(export_schema())` | meta-validation OK |
| `code-reviewer` fresh-context S4 검증 | **Critical C1** 1건 → 즉시 반영, Minor 2 / Nitpick 2 중 일부 반영 |

## 검증자 지적 반영

| # | 이슈 | 조치 |
|---|---|---|
| C1 | v2 도입 시 v1 덮어쓰기 위험 | workflow 에 `for f in hwp_ir_v*.json` 자동 복사 루프 추가 |
| M1 | 주석 "extra=allow 시 additionalProperties 생략" 이 사실과 불일치 | 주석 수정: `additionalProperties: true` 명시 출력 — False 만 아니면 통과 |
| N1 | `ImportError` 방어가 Python 3.9+ 에서 중복 | try/except 제거 |

이월:
- M2 (`test_load_schema_raises_clear_error_on_missing_package_resource` 가 smoke 만) — monkeypatch 로 파일 삭제 시뮬레이션은 복잡. 실사용 시 수동 검증
- N2 (`test_export_schema_defs_are_populated` 가 부분 집합만 체크) — 정확히 매치로 조이는 개선 가능

## 테스트 커버리지 (새 파일)

**`tests/test_ir_schema_export.py` (14)**:
| 테스트 | 검증 |
|---|---|
| `test_export_schema_has_id_and_dialect` | $id / $schema 주입 확인 |
| `test_export_schema_root_additional_properties_false` | 루트 additionalProperties: false |
| `test_export_schema_defs_are_populated` | 9개 definition 존재 |
| `test_export_schema_known_blocks_forbid_additional` | UnknownBlock 제외 전부 additionalProperties: false |
| `test_export_schema_no_numeric_range_keywords` | minimum/maximum/exclusive* 전부 부재 (재귀) |
| `test_export_schema_passes_meta_validation` | Draft 2020-12 meta-schema check_schema() |
| `test_load_schema_matches_export_schema` | In-package JSON 이 코드 출력과 동일 (sync) |
| `test_load_schema_is_valid_draft_2020_12` | Packaged JSON 도 meta 통과 |
| `test_real_hwp_document_validates_against_schema` | 실제 HWP 샘플의 to_ir() 가 schema 통과 |
| `test_minimal_hwp_document_validates` | 빈 HwpDocument validates |
| `test_paragraph_block_with_inlines_validates` | ParagraphBlock + InlineRun validates |
| `test_invalid_kind_fails_schema_validation` | ParagraphBlock.kind.const == "paragraph", TableBlock.kind.const == "table" 확인 |
| `test_schema_id_has_immutable_v1_path` | /v1/ 경로 포함, /schema.json 종료 |
| `test_load_schema_raises_clear_error_on_missing_package_resource` | load_schema smoke (실제 누락 시뮬레이션은 수동) |

## S5 진입 조건 (인수인계)

S5 는 "`iter_blocks` + LangChain 어댑터" — `ir.md §Python API §iter API`.

1. **`HwpDocument.iter_blocks(*, scope, recurse)`** — 순수 Python 메서드로 구현 가능 (Rust 변경 불필요)
   - `scope: Literal["body", "furniture", "all"] = "body"`
   - `recurse: bool = True` — TableCell.blocks 재귀
2. **LangChain 어댑터** — 기존 `python/rhwp/integrations/langchain.py` 의 `HwpDocumentLoader` 가 IR 을 사용하도록 옵션 추가
3. **테스트** — body-only scope, furniture scope (v0.2.0 은 빈 리스트), recurse=True/False 동작, LangChain `Document` 변환

S4 에서 고정한 계약:
- 모든 Pydantic 모델이 frozen — iter_blocks 가 block 참조를 반환해도 안전
- `Block` 유니온에 새 variant 추가 시 `_harden_unknown_variant()` 가 자동 반영

## 참조

- 상위 설계: [roadmap/v0.2.0/ir.md](../../../roadmap/v0.2.0/ir.md) §JSON Schema 공개
- 이전 스테이지: [stage-1.md](stage-1.md), [stage-2.md](stage-2.md), [stage-3.md](stage-3.md)
- Pydantic V2 JSON Schema: <https://docs.pydantic.dev/latest/concepts/json_schema/>
- JSON Schema Draft 2020-12: <https://json-schema.org/draft/2020-12/release-notes>
- OpenAI Structured Outputs strict mode 제약: <https://platform.openai.com/docs/guides/structured-outputs>
