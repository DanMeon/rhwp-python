# Phase 2 — Document IR 확장

**대상 버전**: v0.3.0
**선행 조건**: v0.2.0 Document IR v1 (기본 스키마) GA — [v0.2.0/ir.md](v0.2.0/ir.md)

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

## 미확정 이슈

- **이미지 임베딩 전략** — `embedded` 모드 지원 여부. base64 라 IR JSON 크기가 수 MB 단위로 증가할 수 있음. Docling 은 `PictureRefMode.PLACEHOLDER` 기본값 채택 — 동일 기본값 권장
- **수식 TeX 변환** — HWP 수식 → LaTeX 매핑. 상류 지원 확인 필요. 미지원 시 v0.3.0 은 `raw` 만, v0.4.0+ 에서 TeX 추가
- **`FieldBlock.kind` 열거값** — HWP 필드 타입이 수십 개. 닫힌 `Literal` 로 시작하면 미지 필드에 대해 `ValidationError`. 대안: `kind: str` + `known_kind: FieldKind | None` 이중 필드
- **중첩 Footnote 블록의 재귀 깊이** — 각주 내부에 표·그림 허용할 것인가? v0.3.0 초판은 단락 + 인라인만 허용하여 검증 부담 최소화
