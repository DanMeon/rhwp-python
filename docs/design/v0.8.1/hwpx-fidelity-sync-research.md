---
status: Draft
description: "v0.8.1 hwpx-fidelity-sync ADR — 'test_lossy' 재설계 방식 / PATCH 등급 판단 / pin 추적 브랜치 3건의 옵션 비교와 근거"
target: v0.8.1
last_updated: 2026-07-07
---

# v0.8.1 hwpx-fidelity-sync — 설계 의사결정 리서치 요약

[v0.8.1/hwpx-fidelity-sync.md](../../roadmap/v0.8.1/hwpx-fidelity-sync.md) §결정 사항 중 외부 독자가 "왜?" 를 던질 만한 **3**건의 업계 선례·대안·실패 시나리오를 기록한다. spec 본문이 최종 결정을 기술하고, 본 문서는 그 결정의 근거를 담는다.

## 결정 매트릭스

| # | 항목 | 옵션 비교 | 채택 | 1차 근거 |
|---|---|---|---|---|
| 1 | `test_lossy` 재설계 | A: 새 손실 fixture 탐색 / B: xfail 대기 / C: 손실 e2e 제거 → invariant 흡수 / D: C + `RoundtripReport` unit-construct 계약 검증 | D | detection 은 상류 `diff_documents` 위임, binding 의 `ok=False` 리포트 분기는 unit 으로 가드 |
| 2 | 버전 등급 | A: PATCH v0.8.1 / B: MINOR v0.9.0 | A | 공개 표면 신규 0 · breaking 0, v0.6.1 전례 동형 |
| 3 | pin 추적 브랜치 | A: `main` (`10f5c51e`) / B: `devel` (`bca79ee5`) | A | `devel` 미릴리스, upstream 자체가 `main` 으로만 GA |

## 1. `test_lossy` 재설계

### 팩트

- `table-vpos-01.hwpx` 는 v0.8.0 시점 (pin `7d9aae7f`) 에서 polygon 2개의 `<hp:shapeComment>다각형입니다.</hp:shapeComment>` 가 `serialize_hwpx` 출력에서 소실되어 `verify_hwpx_roundtrip().ok == False` 였다 (`docs/upstream/issue-hwpx-shapecomment-drawing-shapes.md` 재현 절).
- 상류 #1451 해결 (commit `2d6d0cf9` legacy 도형 `shapeComment` 직렬화 1단계, `c0f94fbb` Polygon 보존 가드 2단계) 로 현재 pin `10f5c51e` 에서 동일 문서가 `report.ok is True` / `report.differences == []` (실측: `pytest` 에서 `test_lossy_document_reports_human_readable_differences` FAILED — `RoundtripReport(ok=True, differences=[])`).
- 현 fixture 코퍼스는 `aift.hwpx` (HWP5→HWPX 변환) 와 `table-vpos-01.hwpx` 둘 뿐이고 양쪽 모두 무손실 round-trip.
- `verify_hwpx_roundtrip` 은 `self.inner.document()` 를 serialize → reparse → `diff_documents(원본, 재파싱)` 하는 self round-trip 이라 외부 손상 주입 지점이 없다 — 손실은 오직 상류 serializer 가 아직 못 쓰는 요소에서만 자연 발생.
- 상류 `diff_documents` 가 비교하지 않는 요소 (수식 script / cell rowspan·colspan / BinData byte / 도형 raw) 는 차이가 있어도 검출되지 않으므로 손실 유도 fixture 로 부적합.

### 검증자 반박

- "손실 검출 e2e 를 없애면 verify 가 실제 손실을 잡는지 누가 보증하나?" → 상류가 `IrDifference` 를 방출하는지는 상류 회귀 테스트 (`task1392_shape_comment_loss_in_gate` 등 `ObjectComment` 게이트) 가 가드한다. 본 binding 의 변환 (`IrDifference` → `d.to_string()`) 은 순수 매핑이라 상류 계약이 성립하면 표면도 성립.
- "상류가 회귀하면 무손실 positive 가 놓치지 않나?" → 회귀 시 `table-vpos-01.hwpx` 의 AC-1 이 `ok is True` 위반으로 red 전환되어 자동 검출된다 — negative 를 positive 로 뒤집었을 뿐 검출력은 보존.
- "새 손실 fixture (A) 가 더 견고하지 않나?" → 상류가 143 HWPX 샘플 xfail 0 에 도달해 자연 손실 문서 확보가 난망하고, 확보하더라도 상류의 다음 fidelity 개선에 또 무효화되어 테스트가 상류 구현 진척에 결합된다 (동일 실패의 반복).
- "xfail (B) 로 두면 의도가 보존되지 않나?" → xfail 은 "언젠가 xpass 기대" 의미인데 여기선 반대 (상류 회귀 시 손실 재발) 라 의미가 뒤집힌다. invariant 흡수가 semantics 정합.
- "손실 e2e 를 지우면 binding 의 `ok=False` 분기가 아무 테스트도 안 타지 않나?" → 맞다 — 이것이 옵션 C 의 잔여 공백이다. `RoundtripReport` 는 invariant 를 model-enforce 하지 않고 (`python/rhwp/document.py` plain Pydantic) Rust 가 `ok = differences.is_empty()` (`src/document.rs:341`) 로 설정하기에만 성립하므로, 이 분기를 미검증으로 두면 리포트 계약이 무가드가 된다. 옵션 D 는 `RoundtripReport(ok=False, differences=[...])` 를 unit 으로 구성·assert 하여 non-empty str list + False 방향 invariant 를 e2e 없이 가드한다 (detection 위임은 유지, binding 표면 계약만 추가 검증).

### 최종 결정

D 채택. 손실 검출 e2e (`test_lossy...`) 를 제거하고 무손실 positive (AC-1/2) + invariant (AC-3) 로 재편하되, binding 의 `ok=False` 리포트 분기는 `RoundtripReport(ok=False, differences=[...])` unit-construct 로 계약 (AC-4) 을 가드한다. detection 자체는 상류 `diff_documents` 계약에 위임하고, 상류 회귀는 positive 테스트의 red 전환으로 자동 노출된다.

### 1차 소스

- 상류 이슈: <https://github.com/edwardkim/rhwp/issues/1451>
- 상류 해결 commit: `2d6d0cf9` (legacy 도형 shapeComment 직렬화 1단계), `c0f94fbb` (Polygon 보존 가드 2단계)
- upstream 이슈 초안 (재현 절 포함): `docs/upstream/issue-hwpx-shapecomment-drawing-shapes.md`

## 2. 버전 등급

### 팩트

- 현재 pin `10f5c51e` 에서 `cargo check` clean, `pytest -m "not slow"` 604 passed. 실패 2건은 (i) `test_version_is_package_version` — `.venv` 의 낡은 `rhwp_python-0.7.0.dist-info` 로 인한 로컬 메타데이터 불일치 (upstream 무관, 재설치로 해소) (ii) 본 spec 대상 `test_lossy`.
- 우리 소비 심볼 (`DocumentCore` 6 메서드 / `serialize_hwpx` / `diff_documents` / `svgs_to_pdf` / `RasterRenderOptions` / `LayerRasterRenderer` / `Paragraph::control_text_positions` / `utf16_pos_to_char_idx`) 시그니처 불변.
- IR schema 는 `"1.1"` 유지, `verify_hwpx_roundtrip` / `RoundtripReport` 시그니처·의미 불변, 신규 public 메서드·모듈 0.
- v0.6.1 은 "상류 v0.7.11~v0.7.12 GA 흡수 + polish" 를 PATCH 로 발행 (CHANGELOG `[0.6.1]`).

### 검증자 반박

- "보존 boundary 확대는 사용자 계약 강화라 MINOR 아닌가?" → 확대는 상류 `diff_documents` 위임의 자동 반영이지 binding 표면 추가가 아니다. 사용자가 호출하는 계약 (`verify_hwpx_roundtrip` 시그니처·반환 타입·의미) 은 불변이고 보장 범위만 상류를 따라 넓어진다 — SemVer 상 하위호환 확대라 PATCH 가 정합.
- "로드맵 v0.9.0 예약과 충돌하지 않나?" → v0.9.0 (HWP5 binary writeback) 은 별개 스코프이고, v0.8.1 은 그 사이 삽입되는 PATCH 라 SemVer 단조 증가를 깨지 않는다.

### 최종 결정

A 채택 (v0.8.1 PATCH). 공개 표면 신규 0 · breaking 0 · IR schema 불변이라 상류 GA 흡수 성격의 PATCH 로 발행하고, MINOR 예약 (v0.9.0) 은 보존한다.

### 1차 소스

- SemVer 2.0.0: <https://semver.org/spec/v2.0.0.html>
- 전례: `CHANGELOG.md` `[0.6.1]` 섹션 (상류 GA 흡수 PATCH)

## 3. pin 추적 브랜치

### 팩트

- 상류 원격 상태 (`git ls-remote`): `main` = `10f5c51e` (2026-06-25), `devel` = `bca79ee5` (2026-07-07). `main..devel` = 959 commit, `devel..main` = 14 commit.
- `.gitmodules` 는 `branch = main` 으로 고정. 우리 pin `10f5c51e` 는 `main` HEAD 와 동일하고 v0.7.17 태그보다 68 commit 앞선다.
- `devel` 최근 활동은 내부 리팩토링 (라운드 1~4: `parse_paragraph_list` 해체, `object_ops.rs` 9839줄 하위 모듈 분해, `layout_composed` 226→146) — main→devel diff 1561 파일 / +130K / -17K.
- 본 spec 이 흡수하는 fidelity 개선 (#1451 등) 은 이미 `main` HEAD (`10f5c51e`) 에 머지되어 포함됨.
- 우리 소비 심볼은 `devel` 에서도 시그니처 보존 (대조 완료) — 파일 위치만 이동 (`document_core/commands/`, `queries/` 하위 분해).

### 검증자 반박

- "devel 리팩토링이 크니 미리 채택해 다음 sync 를 줄이는 게 낫지 않나?" → 미릴리스 개발 브랜치라 미완 리팩토링의 회귀를 조기 노출하고 upstream 이 아직 검증 중인 상태에 결합된다. upstream 자체도 `main` merge 로만 GA 를 낸다.
- "devel 을 채택하면 fidelity 를 더 얻나?" → 본 spec 이 목표하는 fidelity 는 이미 `main` 에 있다. devel 추가분은 주로 내부 리팩토링이라 사용자 관찰 이득이 미미하고 계약은 불변.

### 최종 결정

A 채택 (`main`, pin `10f5c51e`). `.gitmodules` 의 `main` 추적 정책을 유지하고 `devel` 리팩토링은 상류 GA 시점에 흡수한다.

### 1차 소스

- `.gitmodules` (`branch = main`)
- 상류 브랜치 구조: <https://github.com/edwardkim/rhwp>

## 참조

- [roadmap/v0.8.1/hwpx-fidelity-sync.md](../../roadmap/v0.8.1/hwpx-fidelity-sync.md) — 본 리서치의 결정 요약
- 상류 이슈: [edwardkim/rhwp#1451](https://github.com/edwardkim/rhwp/issues/1451)
