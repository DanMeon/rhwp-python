---
status: Draft
description: "v0.8.1 — 상류 HWPX serializer fidelity 개선 흡수 (legacy 도형 shapeComment #1451 등) + 'verify_hwpx_roundtrip' 보존 boundary 실질 확대 + 무효화된 'test_lossy' 재설계"
target: v0.8.1
last_updated: 2026-07-07
---

# v0.8.1 — HWPX fidelity 상류 sync

v0.8.0 이 상류 `diff_documents` 검증 범위로 확대한 `verify_hwpx_roundtrip` 의 보존 boundary 를, 그 사이 상류 HWPX serializer 가 도달한 fidelity 개선까지 흡수한다. 핵심 계기는 상류 [#1451](https://github.com/edwardkim/rhwp/issues/1451) — 본 프로젝트가 보고한 legacy 도형 (polygon / ellipse 등) `shapeComment` 미직렬화가 상류에서 해결되어, 회귀 fixture `table-vpos-01.hwpx` 가 무손실 round-trip 으로 전환됐다.

verify 로직은 상류 `diff_documents` 위임이라 이 개선이 코드 변경 없이 반영된다. 본 릴리스의 작업은 흡수한 상류 커밋의 submodule pin 갱신 문서화 + 상류 개선으로 무효화된 negative 회귀 테스트 (`test_lossy_document_reports_human_readable_differences`) 재설계에 한정된다. 공개 API·IR schema (`"1.1"`) 불변, 추가 표면 없음.

주요 결정의 근거·대안·실패 시나리오는 짝 페어: [hwpx-fidelity-sync-research.md](../../design/v0.8.1/hwpx-fidelity-sync-research.md).

## 결정 사항

| 항목 | 값 | 근거 |
|---|---|---|
| 1 — 버전 등급 | v0.8.1 PATCH | 공개 API 시그니처·IR schema (`"1.1"`) 불변, 표면 신규 0, breaking 0. 상류 GA 흡수 + 회귀 테스트 polish 성격이라 v0.6.1 (상류 v0.7.11~v0.7.12 흡수 PATCH) 전례 동형. 자세한 MINOR 대비 비교는 ADR §2. |
| 2 — submodule pin | `7d9aae7f` → `10f5c51e` (상류 v0.7.17 + 68, `main` HEAD) | v0.8.0 GA 기록 (`7d9aae7f`) 이후 흡수된 238 commit 을 pin 으로 확정. `main` 추적 유지 — `devel` (959 commit 리팩토링) 은 미릴리스라 미채택. 자세한 브랜치 비교는 ADR §3. |
| 3 — 보존 boundary 확대 반영 방식 | 상류 위임, binding 코드 변경 0 | `verify_hwpx_roundtrip` 이 `diff_documents` 위임이라 상류가 비교 대상에 추가한 필드만 자동 반영된다. 본 구간 실질 확대는 legacy 도형 `shapeComment` (`IrDifference::ObjectComment`, 상류 #1451) 1건. 동반된 serializer 개선 (바탕쪽 MasterPage / 쪽 테두리 element / 묶음 좌표) 은 `roundtrip.rs` 에 해당 diff variant 가 없어 (BorderFill 은 count 만 비교, v0.8.0 커버) boundary 밖 — emit ≠ verify (v0.8.0 § 배경 계승). 회귀 가드·문서만 갱신. |
| 4 — `test_lossy` 재설계 | 손실 e2e 제거 → 무손실 positive + invariant + `RoundtripReport` unit 계약 | `table-vpos-01.hwpx` 가 #1451 해결로 무손실화되어 자연 발생 negative fixture 가 소멸. detection 은 상류 `diff_documents` 위임, binding 의 `ok=False` 리포트 분기는 unit-construct 로 계약 가드. 옵션 A/B/C 비교는 ADR §1. |
| 5 — 상류 #1451 이슈 문서 전환 | RESOLVED (in-place Frozen) | 본 프로젝트가 보고한 이슈가 상류 머지됨. `docs/upstream/issue-hwpx-shapecomment-drawing-shapes.md` 를 CONVENTIONS § upstream 정책대로 전환 — 본문 첫 헤더 위 `> **RESOLVED** — 상류 commit '2d6d0cf9'+'c0f94fbb'` 인용 블록 + frontmatter `status: Frozen`, 기존 body 보존. |

## 인수조건

- **AC-1** — `table-vpos-01.hwpx` 를 parse → `verify_hwpx_roundtrip()` 결과가 `report.ok is True` 이고 `report.differences == []` (상류 #1451 해결로 polygon `shapeComment` 무손실 round-trip).
- **AC-2** — 무손실 문서 `aift.hwpx` 의 `verify_hwpx_roundtrip()` 는 `report.ok is True` + `report.differences == []` (v0.8.0 positive 보장 회귀 보존).
- **AC-3** — invariant `report.ok == (len(report.differences) == 0)` 가 모든 fixture 에서 성립 (양방향).
- **AC-4** — 손실 리포트 계약: `RoundtripReport(ok=False, differences=["..."])` 로 구성한 리포트에서 `differences` 는 비어있지 않은 `list[str]` (각 항목 `strip()` 후 비지 않음) 이고 invariant `ok == (len(differences) == 0)` 가 `False` 방향에서도 성립한다. e2e 손실 유도는 상류 무손실 도달로 현 코퍼스에서 불가 — detection 은 상류 `diff_documents` 계약 위임, 본 AC 는 binding 표면의 리포트 계약을 unit 으로 가드 (ADR §1).
- **AC-5** — 상류 pin `10f5c51e` 에서 `pytest -m "not slow"` 회귀 0. IR baseline byte-equal (`aift.hwp` + `table-vpos-01.hwpx`) 유지, 공개 API·IR schema (`"1.1"`) 불변.

## 영구 비목표

- **HWP5 binary writeback** (`Document.to_hwp_bytes` / `export_hwp`) — v0.9.0 예약 스코프. 본 PATCH 는 HWPX 검증 경로만 다룬다.
- **`devel` 브랜치 리팩토링 (959 commit) 선제 채택** — 미릴리스 개발 브랜치라 `main` 추적 정책상 다음 GA sync 대상. 우리 소비 심볼 시그니처는 조사 시점 `devel` 대조에서 보존됐으나, 미채택 브랜치라 실제 채택 시 재검증 대상.
- **상류 `diff_documents` 미비교 요소의 round-trip 보장** — 수식 script (description 만 비교) / 표 cell rowspan·colspan / BinData 실제 byte / 도형 raw byte 는 상류 비교 밖이라 boundary 밖 (v0.8.0 비목표 계승).
- **mutable IR 편집 API** — 사용자가 IR 을 편집해 새 문서를 생성하는 빌더 표면은 v1.0 API 안정 시점 검토 (v0.8.0 비목표 계승).

## 참조

- 짝 페어 (ADR): [hwpx-fidelity-sync-research.md](../../design/v0.8.1/hwpx-fidelity-sync-research.md)
- 상류 이슈: [edwardkim/rhwp#1451](https://github.com/edwardkim/rhwp/issues/1451) — legacy 도형 `shapeComment` 직렬화
- upstream 이슈 초안 (RESOLVED 전환 대상): [issue-hwpx-shapecomment-drawing-shapes.md](../../upstream/issue-hwpx-shapecomment-drawing-shapes.md)
- CONVENTIONS § upstream/ 해결 정책: [CONVENTIONS.md](../../CONVENTIONS.md)
