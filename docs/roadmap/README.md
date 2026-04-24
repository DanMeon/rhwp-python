# Roadmap

rhwp-python 의 버전별 로드맵. 완료된 단계는 참고 자료, 미래 단계는 구현 전 계획 초안.

## 현재 상태

- **v0.1.1** — sdist 크기 수정 완료, PyPI 배포 완료
- **v0.2.0** — Document IR v1 (Pydantic + JSON Schema) 계획
- **v0.3.0+** — Phase 2 이후 기능 (설계 단계)

## 버전 계획

각 확정 버전은 버전별 디렉토리 안에 문서가 모임. Phase 는 여러 MINOR 릴리스에 걸친 기능 묶음.

| 버전·단계 | 주제 | 문서 |
|---|---|---|
| v0.1.0 / v0.1.1 | rhwp-python 분사 + PyPI 런칭 (sdist 보정 포함) | [v0.1.0/rhwp-python.md](v0.1.0/rhwp-python.md) |
| v0.2.0 | Document IR v1 — Pydantic 모델 + JSON Schema 공개 | [v0.2.0/ir.md](v0.2.0/ir.md) |
| Phase 2 (v0.3.0) | IR 확장 (이미지·수식·각주·머리글꼬리·TocEntry·Field) + `rhwp-py` CLI | [phase-2.md](phase-2.md) · [v0.3.0/cli.md](v0.3.0/cli.md) |
| Phase 3 (v0.4~0.6) | view 렌더러 + RAG 로더 확장 | [phase-3.md](phase-3.md) |
| Phase 4 (v0.7~1.0) | JSON IR → HWP 역생성 | [phase-4.md](phase-4.md) |

> CLI 는 v0.2.0 원안이었으나 상류 Rust 크레이트(`edwardkim/rhwp`)의 `rhwp` 바이너리와 이름 충돌로 폐기. v0.3.0 에서 `rhwp-py` 라는 별도 이름으로 Python 고유 영역만 노출하는 얇은 CLI 를 재도입한다 (상세: [v0.3.0/cli.md](v0.3.0/cli.md)). 폐기 경위는 [v0.2.0/ir.md § 방향 전환 배경](v0.2.0/ir.md).

## 원칙

- **MINOR 단위 증분** — 기능 한 덩어리씩. 깨지는 변경 없이 누적
- **Phase 경계는 breaking 없음** — Phase 1 → 2 이동해도 기존 API 유지
- **Rust 코어 커밋 고정** — 각 릴리스는 `external/rhwp` submodule 의 특정 upstream commit 에 pin. 코어 업그레이드 시 CHANGELOG 에 명시
- **버전은 git tag 와 동일한 `v` prefix** — 디렉토리명·문서명 일관성
- **Stage 분할 기준** — 단일 세션/수일 규모는 단일 문서의 섹션으로 기록 (현재 `implementation/v0.1.0/migration.md` 처럼). 여러 주 이상 · 의존성 추적이 필요한 대형 작업(Phase 2 IR 구현 등)에서만 `implementation/v<X.Y.Z>/stages/stage-N.md` 로 분할

## 연표 (대략)

| 버전 | 대략 목표 시점 |
|---|---|
| v0.1.0 / v0.1.1 | 2026 Q2 (배포 완료) |
| v0.2.0 | 2026 Q2 ~ Q3 |
| v0.3.0 | 2026 Q3 ~ Q4 |
| v0.4.0 ~ v0.6.0 | 2027 |
| v1.0.0 | 2027+ |

타임라인은 **유동적** — 상류 `edwardkim/rhwp` 진척과 커뮤니티 수요에 따라 변경.

## 비범위 (영구)

- rhwp 코어 자체의 수정 — 모두 업스트림 PR 로
- HWP/HWPX 가 아닌 다른 한국 문서 포맷 (ARX / GUL 등) — rhwp 범위 밖
- OCR / 이미지 내 텍스트 인식 — 별도 도메인
