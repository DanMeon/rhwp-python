# Stage S1 — PictureBlock + Furniture 채움 (완료)

**Status**: Frozen · **Target**: v0.3.0 · **Last updated**: 2026-04-26

**작업일**: 2026-04-26
**계획 문서**: [roadmap/v0.3.0/ir-expansion.md](../../../roadmap/v0.3.0/ir-expansion.md) §구현 스테이지 분할
**설계 근거**: [design/v0.3.0/ir-expansion-research.md](../../../design/v0.3.0/ir-expansion-research.md)

## 스코프

ir-expansion.md §S1 row 정확 매핑:

- `PictureBlock` / `ImageRef` Pydantic 모델 도입
- Rust `ir.rs` 의 picture walker (`Control::Picture` → `RawPicture`)
- `bin_data_content` 노출 — `Document.bytes_for_image(picture)` 헬퍼
- master_pages + `Control::Header` / `Control::Footer` 매핑하여
  `furniture.page_headers` / `page_footers` 채움
- SchemaVersion `1.0` → `1.1` (첫 신규 블록 타입 도입 시점)

S2 (Formula + Footnote/Endnote), S3 (ListItem + Caption + Toc + Field),
S4 (Schema 1.1 GA + CLI/LangChain) 스코프는 본 스테이지 범위 밖.

## 산출물

| 파일 | 변동 | 내용 |
|---|---|---|
| `python/rhwp/ir/nodes.py` | +29 / -8 | `ImageRef` / `PictureBlock` 추가, `_KNOWN_KINDS` `{paragraph, table}` → `{paragraph, table, picture}`, `Block` 유니온 picture 멤버, `CURRENT_SCHEMA_VERSION` 1.0 → 1.1 |
| `python/rhwp/ir/__init__.pyi` | +6 | `ImageRef` / `PictureBlock` re-export |
| `python/rhwp/ir/_raw_types.py` | +25 | `RawImageRef`, `RawPicture` TypedDict; `RawParagraph.pictures`, `RawDocument.headers`/`footers` 필드 추가 |
| `python/rhwp/ir/_mapper.py` | +60 | `_build_picture_block`, `_image_uri`, `_mime_for_extension` (12 종 mime 테이블), `_flatten_paragraph` 가 pictures 도 emit, `build_hwp_document` 가 furniture 채움 |
| `src/ir.rs` | +85 | `RawImageRef` / `RawPicture` 구조체, `build_raw_picture`, `collect_headers_footers_from_paragraph`, `lookup_bin_data_bytes`, `RawDocument.headers`/`footers`. `build_raw_paragraph` 가 `&Document` 를 받도록 시그니처 확장 (bin_data_list 접근용) |
| `src/document.rs` | +13 | `bytes_for_image_id(bin_data_id: u16) -> PyResult<Option<Bound<PyBytes>>>` |
| `python/rhwp/_rhwp.pyi` | +1 | `bytes_for_image_id` 스텁 |
| `python/rhwp/document.py` | +52 | `Document.bytes_for_image(picture)` — `bin://` URI 파싱 + 5 단계 fail-fast 검증 |
| `python/rhwp/integrations/langchain.py` | +13 | `_block_to_content_and_meta` 에 `PictureBlock` 분기 추가 (description → content, image_uri/image_mime → metadata) |
| `python/rhwp/ir/schema/hwp_ir_v1.json` | +71 / -2 | 재생성 (`ImageRef`, `PictureBlock` `$defs` 추가, schema_version default `1.1`) |
| `tests/test_ir_picture.py` | +257 (신규) | 36 테스트 (ImageRef/PictureBlock 모델 + mime 매핑 + mapper + bytes_for_image 5 에러 케이스 + 실제 샘플 lookup) |
| `tests/test_ir_furniture.py` | +166 (신규) | 15 테스트 (Furniture 모델 + mapper 헤더/푸터 라우팅 + 순서 + 실제 샘플 + iter_blocks recurse) |
| `tests/test_ir_schema.py` | -2 / +5 | "picture" → "footnote" 로 unknown-kind 픽스처 교체, parametrize fixture 갱신 |
| `tests/test_ir_roundtrip.py` | -7 / +21 | schema_version 1.0 → 1.1 (2 곳), `test_furniture_is_empty` → `test_furniture_lists_have_correct_types`, `test_body_contains_only_known_block_kinds` 에 PictureBlock 추가 |
| `tests/test_ir_iter_blocks.py` | -7 / +18 | `test_iter_blocks_furniture_is_empty_in_v0_2_0` → `test_iter_blocks_furniture_yields_consistent_with_lists`, known-kinds 테스트에 PictureBlock 추가 |
| `tests/test_ir_schema_export.py` | +2 | `expected_nodes` set 에 `ImageRef`, `PictureBlock` 추가 (10 → 12) |
| `tests/test_ir_tables.py` | +6 / -2 | TableCell.blocks 검사에 PictureBlock 허용 (셀 내부 그림 가능) |
| `tests/test_ir_mapper.py` | +1 | `_paragraph` helper 가 `pictures=[]` 채움 (TypedDict 필드 추가 반영) |
| `.github/workflows/ci.yml` | +1 | scoped pyright 목록에 `test_ir_picture.py` + `test_ir_furniture.py` 추가 |

## S1 확정 결정 사항

| 결정 | 선택 | 근거 |
|---|---|---|
| **Schema 버전 bump 시점** | S1 에서 즉시 1.0 → 1.1 | 첫 신규 블록 타입 (`picture`) 이 출고되는 시점부터 자기-기술 일관성 보장. S4 GA 는 schema JSON 발행 시점일 뿐, 버전은 콘텐츠 진화에 즉시 반영 |
| **PictureBlock.caption 필드 부재** | S3 까지 보류 | spec § 5 `CaptionBlock` 도입이 S3 — S1 에서 placeholder 추가 시 forward-incompat 변경 위험. 현 시점은 `description: str \| None` 로 alt-text 만 노출 |
| **Furniture endnotes 필드 부재** | S2 까지 보류 | EndnoteBlock 도입이 S2. v0.2.0 ↔ v0.3.0 호환 충돌 (spec § 호환성) 은 endnotes 가 추가될 때만 트리거 — S1 시점은 v0.2.0 Furniture 와 같은 형태 (page_headers / page_footers / footnotes) 유지 |
| **`bin://<bin_data_id>` URI** | 1-based, 상류 그대로 | spec § 1 명시. `Document.bytes_for_image` 가 `(bin_data_id - 1)` 인덱스로 `bin_data_content` lookup — 상류 `renderer/layout/utils.rs::find_bin_data` 와 동일 패턴 |
| **MasterPage paragraphs 처리** | Header/Footer 컨트롤만 추출 | spec § 8 매퍼 정책 reading. MasterPage paragraph 자체는 furniture 미포함 (페이지 배경 템플릿이지 머리글 아님) |
| **MasterPage flat 인덱스** | `flat_map().enumerate()` | 한 섹션의 여러 MasterPage paragraph 가 고유 idx 받도록 enumerate 를 flat_map 바깥에 배치 — 같은 섹션 내 (section_idx, para_idx) 충돌 회피 |
| **Block 출고 순서** | ParagraphBlock → tables → pictures | S1 단순 정책. HWP control 시각 순서 보존은 v0.4.0+ `order: int` 필드 검토 |
| **mime 매핑 위치** | Python mapper | Rust 는 raw extension (`Option<String>`) 만 출고, Python 이 12 종 mime 테이블 + `application/octet-stream` 폴백. IR 진화 시 maturin rebuild 회피 |
| **bytes_for_image 에러 정책** | 5 단계 fail-fast | image=None / non-bin scheme / parse fail / u16 range / lookup miss 각각 명시적 ValueError. 글로벌 CLAUDE.md "Error Philosophy — No Silent Fallback" 준수 |

## 비타협 제약 준수

- 모든 신규 IR 모델 (`ImageRef`, `PictureBlock`) `ConfigDict(extra="forbid", frozen=True)`
- `Field(ge=/le=/gt=/lt=)` 사용 **없음** — `width`/`height`/`dpi` 는 plain `int | None`
- Python 3.10+ 유니온 표기 (`T | None`) — v0.2.0 의 `Optional[T]` import 정리
- mapper 도메인 분기는 모두 Python (Rust 는 평탄 raw 만 출고) — IR 진화 시 maturin rebuild 회피 패턴 보존

## 검증

| 검사 | 결과 |
|---|---|
| `uv run pytest -m "not slow"` | **255 passed** (v0.2.0 의 204 + S1 신규 51) |
| `uv run pyright python/ tests/<scoped CI list>` | **0 errors** |
| `uv run pyright tests/type_check_errors.py` | **4 intentional errors** (CI 검증 통과) |
| `uv run ruff check <S1 changed files>` | clean (pre-existing 4 issues 무관) |
| `cargo clippy --all-targets -- -D warnings` | clean |
| Schema JSON conformance (`test_load_schema_matches_export_schema`) | pass — `hwp_ir_v1.json` 12 `$defs` 포함 |
| `code-reviewer` fresh-context 검증 | Critical 0 / Major 0 / Minor 3 (모두 반영 또는 알려진 한계로 명시) |

### 테스트 커버리지 (ir-expansion.md §S1 → 실제 케이스)

| ir-expansion.md 요구 | 테스트 |
|---|---|
| PictureBlock + ImageRef 직렬화 왕복 | `test_image_ref_roundtrip`, `test_picture_block_roundtrip_with_image`, `test_picture_block_broken_reference` |
| `bin://` URI 파싱 / mime 매핑 | `test_mime_mapping_known_extensions[12]`, `test_mime_mapping_unknown_falls_back`, `test_build_picture_block_with_known_extension` |
| caption 컨테인먼트 | (S3 — `caption: CaptionBlock` 도입 시) |
| `page_headers/page_footers/footnotes/endnotes` 순서 보장 | `test_build_hwp_document_preserves_header_footer_order`, `test_iter_blocks_furniture_yields_consistent_with_lists`, `test_real_sample_iter_blocks_furniture_matches_lists` |
| `endnotes` 가 v0.2.0 schema 와 충돌 | `test_furniture_rejects_v0_3_0_endnotes_field_in_s1` (S2 endnotes 도입 시점에 trigger 검증 활성화) |
| `bytes_for_image` 5 단계 에러 | `test_bytes_for_image_raises_on_broken_reference`, `..._unsupported_scheme`, `..._invalid_uri`, `..._out_of_range`, `..._lookup_miss` |

LLM strict-mode 스키마 conformance / `jsonschema` meta-validation 은 v0.2.0 S4 패턴 그대로 통과 (신규 12 `$defs` 모두 `additionalProperties: false`, 수치 range 키워드 부재).

## 알려진 한계 (S2/S3 또는 후속 MINOR 에서 처리)

- **`bin_data_content` 와 `bin_data_list` 인덱스 정합성** — 모든 BinData 가 Embedding 타입일 때만 정확. Link/Storage 혼합 문서에서는 잘못된 entry 반환 가능 — 상류 renderer 도 같은 가정 공유 (상류 패리티). `lookup_bin_data_bytes` 의 doc-comment 에 명시.
- **`PictureBlock.caption: CaptionBlock | None` 부재** — S3 추가 예정. 현재는 `description: str | None` 으로 alt-text 만.
- **`PictureBlock` `width`/`height`/`dpi` 항상 None** — 상류 Picture 가 픽셀 dimension 을 직접 노출하지 않으며 (border 좌표만), HWPUNIT 계산은 v0.4.0+ 검토.
- **`has_content=false` 케이스의 mapper 처리** — 현재는 `bin_data_id` 를 보존한 채 `bin://N` URI 출고 (forensics 위해), `Document.bytes_for_image` 호출 시점에 ValueError. 더 엄격한 정책 (image=None 으로 라우팅) 은 v0.4.0+ 검토.
- **HWP control 시각 순서 보존** — ParagraphBlock → tables → pictures 평탄화. 표/그림 혼재 문단의 원본 순서 보존은 v0.4.0+ `order: int` 필드 검토.
- **Furniture footnotes/endnotes** — S2 (`FootnoteBlock` / `EndnoteBlock` 도입) 에서 채움.

## S2 진입 조건 (인수인계)

S2 는 spec § 2 (FormulaBlock) + § 3 (FootnoteBlock / EndnoteBlock) 도입.
S1 에서 고정한 계약:

1. **`Block` 유니온 + `_KNOWN_KINDS` 확장 패턴** — S2 는 `formula`, `footnote`, `endnote` 추가 시 동일 패턴 (Annotated[T, Tag("...")] + frozenset 추가 + `_block_discriminator` 라우팅 자동) 적용.
2. **`Furniture.footnotes` 타입 강화** — 현재 `list[Block]` → S2 에서 `list[FootnoteBlock]` 로. v0.2.0 → v0.3.0 호환 메모 (spec § 호환성) 가 endnotes 신설과 함께 활성화.
3. **mapper Furniture 채움 패턴** — 현 `headers`/`footers` flatten 패턴을 footnote 컨트롤에도 동일 적용. 본문 마커 위치는 InlineRun 텍스트 그대로 보존, 본문 자체만 furniture.footnotes 로 라우팅 (spec § 3 "body vs furniture 배치").
4. **Provenance.marker_prov 추가** — Footnote/Endnote 의 본문 마커 위치 (몇번째 단락의 몇번째 글자) 별도 보존. S2 에서 `Provenance` 모델 확장 또는 `marker_prov: Provenance` 필드 추가 검토.

## 참조

- 상위 설계: [roadmap/v0.3.0/ir-expansion.md](../../../roadmap/v0.3.0/ir-expansion.md)
- 결정 사항 증거: [design/v0.3.0/ir-expansion-research.md](../../../design/v0.3.0/ir-expansion-research.md)
- 상류 타입 (S1 매핑): `external/rhwp/src/model/{image,bin_data,header_footer,document}.rs`
- v0.2.0 선례 (스테이지 분할 패턴): [implementation/v0.2.0/stages/stage-1.md](../../v0.2.0/stages/stage-1.md)
