# 0.1.0 — Phase 1 바인딩 분사 + PyPI 배포

**Status**: Frozen · **GA**: v0.1.0 (patch v0.1.1) · **Last updated**: 2026-04-23

rhwp Rust 코어 ([edwardkim/rhwp](https://github.com/edwardkim/rhwp)) 에 대한 PyO3 Python 바인딩을 별도 리포 `DanMeon/rhwp-python` 으로 분사하고 PyPI 에 `rhwp-python` 으로 배포한다. Phase 1 기능은 원본 `rhwp-python-heuristic/rhwp-python/` 에서 이관하며 기능 추가 없음.

관련 상류 이슈: [edwardkim/rhwp#227](https://github.com/edwardkim/rhwp/issues/227) — 2차 회신에서 메인테이너 승인.

## 결정 사항

| 항목 | 값 |
|---|---|
| GitHub 리포 | `DanMeon/rhwp-python` (public) |
| PyPI 패키지명 | `rhwp-python` (`rhwp` 는 업스트림 공식 배포 여지로 남김) |
| Python import | `import rhwp` |
| 확장 모듈명 | `rhwp._rhwp` (maturin `module-name`) |
| rhwp 참조 | `external/rhwp/` 에 `edwardkim/rhwp` 를 git submodule 로 고정 |
| 고정 commit | `163621382ba13be233b155df050375e900a038e2` (upstream/main, 2026-04-22) |
| 초판 버전 | `0.1.0` (Phase 1 스코프 그대로, 기능 추가 없음) |
| 라이선스 | MIT, Edward Kim (코어) + DanMeon (바인딩) 이중 표기 |

## 분사 작업 진행 현황

### 1. 신규 리포 인프라 — 완료

- [x] `DanMeon/rhwp-python` public 리포 (MIT)
- [x] `~/Desktop/kevin/python-template` (copier 9.14.0) 로 초기 인프라 골격 생성
- [x] `main` 브랜치 세팅

### 2. 소스 이관 — 완료

- [x] `external/rhwp` submodule 추가, upstream/main `1636213` 에 고정
- [x] 원본 `rhwp-python-heuristic/rhwp-python/` 의 `src/`, `python/rhwp/`, `tests/`, `benches/` 를 byte-identical 로 이관 (diff 교차 확인)
- [x] `Cargo.toml` path dep 을 `".."` → `"external/rhwp"` 로 교정
- [x] `[workspace]` 자기 선언 유지 (submodule workspace 편입 방지)
- [x] `tests/conftest.py` + `benches/bench_gil.py` 의 샘플 경로를 `external/rhwp/samples/` 로 보정
- [x] mydocs 문서를 현재 구조 (`docs/implementation/`, `docs/design/`, `docs/verification/`) 로 재배치

### 3. 메타데이터·라이선스 — 완료

- [x] `pyproject.toml` — `name = "rhwp-python"`, PyPI URL 전환, 이중 authors, `license-files = ["LICENSE", "external/rhwp/LICENSE"]`
- [x] 루트 `LICENSE` — Edward Kim + DanMeon 이중 copyright MIT
- [x] `.github/CODEOWNERS` — `@DanMeon` 단독 (리뷰 할당용, 저작권과 별개)

### 4. CI — 완료

- [x] `.github/workflows/ci.yml` — 3 OS (Linux/macOS/Windows) × Python 3.9~3.13 매트릭스 + pyright intentional error 4건 + importorskip 29 skip 검증
- [x] `.github/workflows/publish.yml` — `on: release: published` 트리거, 빌드 매트릭스 (Linux x86_64/aarch64, macOS x86_64/aarch64, Windows) + sdist + Trusted Publisher OIDC publish
- [x] `.pre-commit-config.yaml` — python/tests/benches 경로
- [x] `CONTRIBUTING.md` — 개발 절차 + submodule 안내

### 5. 검증 — 완료 (자동)

- [x] `code-reviewer` + `architect-reviewer` 에이전트 팀 독립 검증
- [x] 지적사항 반영: `bench_gil.py` 경로, pre-commit 경로, `license-files` 확장, ci.yml grep 단어경계
- [x] 계획 §2–§6 체크리스트 스코어카드 — [verification/v0.1.0/spinoff-review.md](../../verification/v0.1.0/spinoff-review.md)

### 6. 릴리스 실행 — 예정

- [ ] PyPI Trusted Publisher 등록 (owner=`DanMeon`, repo=`rhwp-python`, workflow=`publish.yml`)
- [ ] `examples/01~03_*.py` 세 스크립트로 실제 HWP 파일 3종 (일반/장문/HWPX) 육안 검증
- [ ] 첫 GitHub Release `v0.1.0` publish → `publish.yml` 가 PyPI 업로드
- [ ] 상류 이슈 #227 에 배포 완료 회신 (PyPI 링크)

## 범위 외

Phase 2 이후는 별도 로드맵 문서로 진행 — [phase-2.md](../phase-2.md), [phase-3.md](../phase-3.md), [phase-4.md](../phase-4.md) 참고.
