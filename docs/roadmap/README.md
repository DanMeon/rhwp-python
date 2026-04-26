# Roadmap

rhwp-python 의 버전별 로드맵 + **활성 spec 인덱스 SSOT**. 모든 spec 의 Status / GA / Target 을 본 페이지에서 추적한다. 문서 관리 정책은 [docs/CONVENTIONS.md](../CONVENTIONS.md) 참조.

본 문서는 Living — 자유 갱신.

## 현재 상태 (2026-04-26)

- **v0.1.0 / v0.1.1** — Frozen, PyPI 배포 완료
- **v0.2.0** — Frozen, Document IR v1 GA (2026-04-25)
- **v0.3.0** — Draft, Phase 2 (IR 확장 + `rhwp-py` CLI) 진행 중
- **v0.4.0+** — 미착수, Phase 3 이후

## 활성 spec 인덱스

각 row 는 spec 한 개 + 짝이 되는 design research (있으면). Status 는 [CONVENTIONS.md § 문서 수명 4 분류](../CONVENTIONS.md) 정의에 따름.

| 버전 | Status | Roadmap spec | Design research (ADR) |
|---|---|---|---|
| v0.1.0 / v0.1.1 | Frozen | [v0.1.0/rhwp-python.md](v0.1.0/rhwp-python.md) | — |
| v0.2.0 | Frozen | [v0.2.0/ir.md](v0.2.0/ir.md) | [design/v0.2.0/ir-design-research.md](../design/v0.2.0/ir-design-research.md) |
| v0.3.0 (IR 확장) | Draft | [v0.3.0/ir-expansion.md](v0.3.0/ir-expansion.md) | [design/v0.3.0/ir-expansion-research.md](../design/v0.3.0/ir-expansion-research.md) |
| v0.3.0 (CLI) | Draft | [v0.3.0/cli.md](v0.3.0/cli.md) | [design/v0.3.0/cli-design-research.md](../design/v0.3.0/cli-design-research.md) |

cross-version reference (버전 무관): [design/pyo3-bindings.md](../design/pyo3-bindings.md) (Active).

## Phase 인덱스

Phase 는 여러 MINOR 릴리스에 걸친 기능 묶음. **구체 결정은 vX.Y.Z spec 이 보유** — phase 문서는 의도/스코프와 동시 GA 두 축 연동만 다룸.

| Phase | Status | 대상 버전 | 문서 |
|---|---|---|---|
| Phase 2 | Active | v0.3.0 | [phase-2.md](phase-2.md) — IR 확장 + CLI 두 축의 연동 SSOT |
| Phase 3 | Active | v0.4.0 ~ v0.6.0 | [phase-3.md](phase-3.md) — view 렌더러 + RAG 프레임워크 통합 |
| Phase 4 | Active | v0.7.0 ~ v1.0.0 | [phase-4.md](phase-4.md) — JSON IR → HWP 역생성 |

Phase 1 (v0.1.x) 은 GA 완료로 별도 phase 문서 없음.

## 구현 / 검증 로그 (Frozen)

작업 완료 후 로그. Frozen — 변경 없음.

| 버전 | 구현 로그 | 검증 리포트 |
|---|---|---|
| v0.1.0 | [implementation/v0.1.0/migration.md](../implementation/v0.1.0/migration.md) | [verification/v0.1.0/spinoff-review.md](../verification/v0.1.0/spinoff-review.md) |
| v0.2.0 | [implementation/v0.2.0/stages/](../implementation/v0.2.0/stages/) (S1~S5) | — |
| v0.3.0 (in-progress) | [implementation/v0.3.0/stages/](../implementation/v0.3.0/stages/) (S1) | — |

## 원칙

- **MINOR 단위 증분** — 기능 한 덩어리씩. 깨지는 변경 없이 누적
- **Phase 경계는 breaking 없음** — Phase 1 → 2 이동해도 기존 API 유지
- **Rust 코어 커밋 고정** — 각 릴리스는 `external/rhwp` submodule 의 특정 upstream commit 에 pin. 코어 업그레이드 시 CHANGELOG 에 명시
- **버전은 git tag 와 동일한 `v` prefix** — 디렉토리명·문서명 일관성
- **Spec 라이프사이클**: Draft → (GA) → Frozen → (필요 시) → Superseded by …. 상세: [CONVENTIONS.md § 새 spec 추가 절차](../CONVENTIONS.md)
- **Stage 분할 기준** — 단일 세션/수일 규모는 단일 `migration.md` 로. 여러 주 이상·의존성 추적이 필요한 대형 작업 (v0.2.0 IR 구현 등) 만 `stages/stage-N.md` 로 분할

## 연표 (대략)

| 버전 | 대략 목표 시점 |
|---|---|
| v0.1.0 / v0.1.1 | 2026 Q2 (GA 완료) |
| v0.2.0 | 2026 Q2 (GA 완료) |
| v0.3.0 | 2026 Q3 |
| v0.4.0 ~ v0.6.0 | 2027 |
| v1.0.0 | 2027+ |

타임라인은 **유동적** — 상류 `edwardkim/rhwp` 진척과 커뮤니티 수요에 따라 변경.

## 비범위 (영구)

- rhwp 코어 자체의 수정 — 모두 업스트림 PR 로
- HWP/HWPX 가 아닌 다른 한국 문서 포맷 (ARX / GUL 등) — rhwp 범위 밖
- OCR / 이미지 내 텍스트 인식 — 별도 도메인
