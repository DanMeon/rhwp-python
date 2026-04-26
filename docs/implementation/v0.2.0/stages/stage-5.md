# Stage S5 — `iter_blocks` + LangChain IR 통합 (완료)

**Status**: Frozen · **GA**: v0.2.0 · **Last updated**: 2026-04-24

**작업일**: 2026-04-24
**계획 문서**: [roadmap/v0.2.0/ir.md](../../../roadmap/v0.2.0/ir.md) §Python API §iter API + §모듈 구조
**설계 근거**: [design/v0.2.0/ir-design-research.md](../../../design/v0.2.0/ir-design-research.md) §5 (iter API 설계)

## 스코프

- `HwpDocument.iter_blocks(*, scope, recurse)` Python 메서드 — DFS 순회, body/furniture/all 세 scope, TableCell 재귀 on/off
- 기존 `HwpLoader` 에 `mode="ir-blocks"` 추가 — ParagraphBlock/TableBlock/UnknownBlock 을 LangChain `Document` 로 매핑 (table 은 HtmlRAG 호환 HTML content)
- CLAUDE.md "exactly 29" 규약 유지 위해 S5 LangChain 테스트를 별도 파일 분리

**v0.2.0 완료 — 이것이 마지막 스테이지**. GA 준비는 별도 작업 (CHANGELOG, 버전 번프, git tag).

## 산출물

| 파일 | 변경 | 요점 |
|---|---|---|
| `python/rhwp/ir/nodes.py` | +40줄 | `HwpDocument.iter_blocks()` 메서드 + `_walk_blocks()` helper |
| `python/rhwp/integrations/langchain.py` | 재작성 | `LoadMode` 에 `"ir-blocks"` 추가, `_block_to_content_and_meta()` 매핑, 공백 블록 필터 |
| `python/rhwp/integrations/langchain.pyi` | - | `LoadMode` 스텁 업데이트 |
| `tests/test_ir_iter_blocks.py` (신규) | 10 테스트 | iter_blocks DFS, scope, recurse, 3단 중첩 |
| `tests/test_langchain_loader_ir.py` (신규) | 11 테스트 | ir-blocks 모드 — 생성자, metadata, HTML content, Provenance 일치 |
| `.github/workflows/ci.yml` | - | test-core-only 가 3 파일 importorskip 기대 + pyright 리스트에 IR 테스트 7개 추가 |

## 핵심 구현 결정

### 1. `iter_blocks` DFS 순회 — 단순 generator

```python
def iter_blocks(self, *, scope="body", recurse=True) -> Iterator[Block]:
    if scope in ("body", "all"):
        yield from _walk_blocks(self.body, recurse)
    if scope in ("furniture", "all"):
        yield from _walk_blocks(self.furniture.page_headers, recurse)
        yield from _walk_blocks(self.furniture.page_footers, recurse)
        yield from _walk_blocks(self.furniture.footnotes, recurse)

def _walk_blocks(blocks, recurse):
    for block in blocks:
        yield block
        if recurse and isinstance(block, TableBlock):
            for cell in block.cells:
                yield from _walk_blocks(cell.blocks, recurse)
```

**설계 원칙** (ir.md §5):
- 속성 (`doc.body` / `doc.furniture`) 은 구조 기반 작업용 — 직접 순회·슬라이싱
- `iter_blocks` 는 scope + recurse 조합이 필요한 경우용 (예: `sum(1 for b in doc.iter_blocks(scope="all") if isinstance(b, TableBlock))`)
- 기본 `scope="body"`: RAG-safe — 머리글/꼬리말 임베딩 포함이 검색 오염의 주된 원인
- `recurse=True` 기본: 중첩 표 내부 블록도 스트리밍 (DFS pre-order)

### 2. LangChain ir-blocks 매핑 전략

| Block 타입 | page_content | metadata |
|---|---|---|
| ParagraphBlock | `block.text` (평문) | `kind="paragraph"`, section_idx, para_idx, char_start, char_end |
| TableBlock | **`block.html`** (HtmlRAG 호환) | `kind="table"`, section_idx, para_idx, rows, cols, **text** (검색 색인용), caption |
| UnknownBlock | `""` (필터링됨) | `kind=<raw kind string>`, section_idx, para_idx |

**설계 근거**:
- 표는 HTML 로 전달 — HtmlRAG (arXiv:2411.02959) 는 LLM 이 HTML 의 rowspan/colspan 의미를 유지할 수 있음을 실증
- 평문 `text` 는 별도 메타데이터로 병기 — 벡터 색인은 평문으로, LLM 프롬프트는 HTML 로 하는 dual-track RAG 지원
- 공백만 있는 블록 (`content.strip() == ""`) 은 RAG 노이즈이므로 스킵

### 3. `_block_to_content_and_meta` 의 UnknownBlock fallback

```python
assert isinstance(block, UnknownBlock)  # ^ fail-fast
```

- Pydantic Discriminator 가 `Block` 유니온을 3개 variant 로만 라우팅하는 불변 — ParagraphBlock / TableBlock elif 뒤에 UnknownBlock 만 남음
- v0.3.0+ 에 PictureBlock 등 새 variant 추가 시 **assert 위에 새 elif 를 먼저 추가** 해야 — 주석으로 명시
- CLAUDE.md "fail-fast only at external boundaries" 와 일관 — 내부 경로에서 silent fallback 금지

### 4. CLAUDE.md "exactly 29" 규약 유지

기존 `test_langchain_loader.py` 는 CLAUDE.md 명시대로 **정확히 29 테스트**. S5 의 ir-blocks 테스트를 추가하면 규약 깨짐 → 별도 파일 `test_langchain_loader_ir.py` (11 테스트) 로 분리.

부작용: test-core-only CI job 이 importorskip 으로 auto-skip 하는 파일이 2 → 3 증가. `ci.yml` 업데이트.

## 검증

| 검사 | 결과 |
|---|---|
| `uv run pytest tests/test_ir_iter_blocks.py -v` | **11 passed** |
| `uv run pytest tests/test_langchain_loader_ir.py -v` | **11 passed** |
| `uv run pytest tests/test_langchain_loader.py --collect-only` | **29 tests collected** (규약 유지) |
| `uv run pytest -m "not slow"` | **164 passed** (S1 35 + S2/S3 16 + S3 tables 11 + S4 14 + S5 iter 11 + S5 loader 11 + 기존 66) |
| `cargo test --lib` | 5 passed |
| `cargo clippy --all-targets -- -D warnings` | clean |
| `uv run pyright python/ tests/` | **4 errors (의도된 `type_check_errors.py` 만)** |
| `code-reviewer` fresh-context S5 검증 | Critical 2건 → 즉시 반영 |

## 검증자 지적 반영

| # | 이슈 | 조치 |
|---|---|---|
| C1 | `tests/test_ir_iter_blocks.py:67` dict literal → Furniture 전달 → pyright 5 errors | `Furniture(page_headers=...)` 로 명시 생성 |
| C2 | `ci.yml` pyright normal 리스트에 S1-S5 테스트 7개 누락 → 신규 타입 오류 CI 미감지 | 7개 파일 추가 (test_ir_schema, test_ir_roundtrip, test_ir_tables, test_ir_iter_blocks, test_ir_schema_export, test_langchain_loader_ir) |
| N1 | UnknownBlock fallback assert 의 v0.3.0+ 확장 포인트 힌트 | 주석 추가 |
| M1 | 내 brief 의 "10 테스트" 는 11 로 정정 (invalid-mode 회귀 테스트 포함) | stage-5.md 에 11 로 기록 |

이월 (v0.3.0+):
- **M2**: `test_ir_blocks_provenance_matches_ir` 가 순서 아닌 집합 비교 — 순서 검증 강화 가능
- **N2**: `scope="furniture"` 내부 순서 (headers→footers→footnotes) 가 테스트로 고정되지 않음 — ir.md 에 한 줄 추가하거나 테스트 추가

## 테스트 커버리지 (새 파일)

**`tests/test_ir_iter_blocks.py` (10)** — scope/recurse 계약 검증
**`tests/test_langchain_loader_ir.py` (11)** — ir-blocks 모드 매핑 검증

## v0.2.0 전체 완료

S1~S5 모두 완료. `docs/roadmap/v0.2.0/ir.md` §구현 스테이지 분할 의 5 단계 계획이 전부 산출물로 전환됨.

**GA 전 잔여 작업** (S5 스코프 밖):
- `CHANGELOG.md` v0.2.0 섹션 작성
- `Cargo.toml` 버전 번프 (0.1.1 → 0.2.0)
- `git tag v0.2.0` 생성
- PyPI 배포 (`publish.yml` 워크플로우 자동)
- README.md 에 Document IR 섹션 추가

## 참조

- 상위 설계: [roadmap/v0.2.0/ir.md](../../../roadmap/v0.2.0/ir.md)
- 이전 스테이지: [stage-1.md](stage-1.md), [stage-2.md](stage-2.md), [stage-3.md](stage-3.md), [stage-4.md](stage-4.md)
- LangChain BaseLoader: <https://python.langchain.com/docs/how_to/document_loader_custom/>
- HtmlRAG (arXiv:2411.02959): <https://arxiv.org/abs/2411.02959>
