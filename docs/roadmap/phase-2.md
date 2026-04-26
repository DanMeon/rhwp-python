# Phase 2 — Document IR 확장

**Status**: Active · **Target**: v0.3.0 · **Last updated**: 2026-04-26

**대상 버전**: v0.3.0 (IR 확장 + `rhwp-py` CLI 동시 진행)
**선행 조건**: v0.2.0 Document IR v1 (기본 스키마) GA — [v0.2.0/ir.md](v0.2.0/ir.md)
**상세 설계**: [v0.3.0/ir-expansion.md](v0.3.0/ir-expansion.md) — 본 Phase 의 구체 사양. 본 문서는 Phase 포지셔닝만 다룸
**설계 증거**: [design/v0.3.0/ir-expansion-research.md](../design/v0.3.0/ir-expansion-research.md) — 8 결정 사항의 업계 선례·실패 시나리오
**병행 문서**: [v0.3.0/cli.md](v0.3.0/cli.md) — CLI 재도입 설계

## 포지셔닝 변경 안내

Phase 2 원안은 "계층 JSON IR 스키마 도입 + 확장" (v0.3.0 ~ v0.4.0 두 릴리스) 이었으나, v0.2.0 의 CLI 계획이 폐기되면서 **IR 도입 자체를 v0.2.0 으로 당김**. Phase 2 는 이제 v0.2.0 기본 스키마 위의 **확장 타입** 만 다룬다.

- **v0.2.0 (Phase 2 전) — 기본 IR**: Document / Section / Paragraph / Table / Cell / InlineRun / Provenance + JSON Schema v1.0
- **v0.3.0 (Phase 2) — IR 확장**: 이미지 / 수식 / 각주 / 미주 / 머리글 / 꼬리말 / 목차항목 / 필드 + JSON Schema v1.1

## 목표

v0.2.0 에서 확보한 RAG-친화적 기본 구조에 HWP 문서의 고유 의미 요소를 추가한다. 확장은 **후방 호환** 이 원칙 — 기존 소비자는 새 `Block.kind` 를 모르더라도 v0.2.0 시절 처리를 그대로 수행할 수 있어야 함 (unknown-kind graceful skip).

## 추가되는 블록 타입

### 일반 문서 요소 (DocLayNet 파생)

- **`PictureBlock`** — 이미지. `ref_mode: Literal["placeholder" | "embedded" | "external"]` (Docling `ImageRefMode` 패턴), `mime_type`, `caption`. 바이너리는 v0.3.0 에서 `placeholder` (텍스트 치환) 기본값, 임베딩은 v0.4.0+
- **`FormulaBlock`** — 수식. HWP 수식은 자체 기호 체계 — `raw: str` (원본) + `tex: str | None` (향후 변환) 이중 필드
- **`FootnoteBlock` / `EndnoteBlock`** — 각주/미주. `ref_id`, `number`, `content: list[Block]` (본문 재귀)
- **`ListItemBlock`** — 목록 항목. `level: int`, `marker: str`, `inlines`
- **`CaptionBlock`** — 표/그림 캡션. `refers_to: str | None` (대상 블록 id)

### HWP 고유 요소

- **`TocEntryBlock`** — 목차 항목. `level: int`, `page_no: int | None`, `target_id: str | None`
- **`FieldBlock`** — 상호참조/변수 필드. `kind: "cross_ref" | "date" | "page_no" | ...`, `cached_value: str`
- **`RevisionMark`** — 변경 이력 마커. v0.3.0 스코프 여부 재평가 (상류 지원 상태 확인 필요)

### Furniture 채움

v0.2.0 에서 `furniture.page_headers`/`page_footers` 는 빈 리스트로 출고됐으나 v0.3.0 에서 실제 내용 채움. 스키마 변화 없음 — 값 채움만.

## JSON Schema 변경

- `schema_version`: `Literal["1.0"]` → `Literal["1.0", "1.1"]` 확장
- `Block` discriminated union 에 새 멤버 추가
- `$id` URL 은 동일 유지 (`hwp_ir_v1.json`) — `v1` major 안의 minor 추가
- 별도 스냅샷: `hwp_ir_v1_1.json` 게시 (구 버전 소비자를 위해)

## 릴리스 일정

단일 릴리스 (v0.3.0) — 8개 신규 블록 타입을 한 번에 안정화. 개별 타입별로 릴리스를 쪼개면 소비자가 어떤 Block 멤버가 존재하는지 반복 확인해야 함.

## v0.3.0 두 축의 연동

v0.3.0 은 한 릴리스에 두 축을 함께 GA — IR 확장 ([v0.3.0/ir-expansion.md](v0.3.0/ir-expansion.md)) 과 CLI ([v0.3.0/cli.md](v0.3.0/cli.md)). 본 절은 두 축이 만나는 지점의 SSOT — 각 spec 본문은 자체 축에 집중하고 spec ↔ spec 직접 cross-link 는 [CONVENTIONS.md](../CONVENTIONS.md) § Cross-link 방향성 규칙 에 따라 자제한다.

연동 지점:

- **`rhwp-py blocks --kind <kinds>`** — IR 확장의 8 신규 kind (`picture` / `formula` / `footnote` / `endnote` / `list_item` / `caption` / `toc` / `field`) 를 CLI enum 에 추가. CLI §S2 가 IR 확장 GA 와 동기 확장
- **`rhwp-py chunks --mode ir-blocks`** — IR 확장의 새 블록을 LangChain `Document` 로 매핑. `PictureBlock`+`CaptionBlock` 단일 청크 (HtmlRAG 패턴), `FootnoteBlock` 은 `--include-furniture` 옵트인
- **`rhwp-py schema`** — IR 확장으로 SchemaVersion 1.1 + 11 known kinds 로 확장된 JSON Schema 출력

GA 동기화: IR 확장 매퍼 / Pydantic 모델이 먼저 GA 가능 상태에 도달해야 CLI enum 도 의미 있게 노출 — 따라서 구현 순서는 IR 확장 stage S1~S3 → IR 확장 S4 (스키마 1.1) + CLI S2 (`blocks` enum 확장) 동시 진행이 자연. 단 stage 분할 자체는 두 spec 이 독립.

