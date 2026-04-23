# rhwp-python 별도 리포 분사 계획

이슈 [#227](https://github.com/edwardkim/rhwp/issues/227) 2차 회신에서 메인테이너 승인을 받아, 현재 작업 리포 `rhwp-python-heuristic`의 `rhwp-python/` 디렉터리를 신규 리포로 옮기고 PyPI 배포까지 진행한다. Phase 2 이후 작업은 신규 리포에서 독립 문서 체계로 이어간다.

> 경로 규약
> - **원본 리포**: `rhwp-python-heuristic` (현재 작업 중인 로컬 경로: `/Users/kevin/Desktop/Projects/rhwp-python-heuristic`, 브랜치 `test/pyo3-sandbox`, `edwardkim/rhwp`의 fork)
> - **원본 소스 루트**: `rhwp-python-heuristic/rhwp-python/`
> - **신규 리포**: `DanMeon/rhwp-python`
> - **업스트림**: `edwardkim/rhwp` (신규 리포에서 `external/rhwp` submodule로 참조)

## 결정 사항

| 항목 | 값 |
|---|---|
| GitHub 리포 | `DanMeon/rhwp-python` (public) |
| PyPI 패키지명 | `rhwp-python` (`rhwp`는 업스트림 공식 배포 여지로 남김) |
| Python import | `import rhwp` |
| rhwp 참조 | `external/rhwp/`에 `edwardkim/rhwp`를 git submodule로 고정 |
| 초판 버전 | `0.1.0` (Phase 1 스코프 그대로, 기능 추가 없음) |
| 원본 리포 브랜치 | `rhwp-python-heuristic`의 `test/pyo3-sandbox` — 이관 완료 후에도 보존 (삭제 금지) |

## 체크리스트

### 1. 신규 리포 준비
- [ ] `DanMeon/rhwp-python` 리포 생성 (public, MIT, Python gitignore)
- [ ] `main` / `devel` 브랜치 구성
- [ ] PyPI에 `rhwp-python` 이름 점유 가능 여부 확인 (`pypi.org/project/rhwp-python/`)
- [ ] 점유 불가 시 `pyrhwp` 대체안 전환 후 이슈 #227에서 네이밍 변경 안내

### 2. rhwp submodule + 작업물 이관
- [ ] `git submodule add https://github.com/edwardkim/rhwp external/rhwp`
- [ ] Phase 1 호환 커밋(`rhwp-python-heuristic`이 참조 중인 `edwardkim/rhwp` 커밋)에 submodule 고정
- [ ] `rhwp-python-heuristic/rhwp-python/` 아래 파일을 신규 리포 루트로 재배치
  - `Cargo.toml`, `pyproject.toml`, `src/`, `python/rhwp/`, `tests/`, `benches/`, `README.md`, `LICENSE`, `CHANGELOG.md`
- [ ] `Cargo.toml`: `rhwp = { path = ".." }` → `rhwp = { path = "external/rhwp" }`
- [ ] 테스트 fixture 경로 보정 (필요 시 `tests/samples/`에 복제 또는 submodule 참조)
- [ ] 이슈 #227 관련 문서 선별 이관
  - `mydocs/plans/task_m101_227*.md`
  - `mydocs/working/task_m101_227_stage*.md`
  - `mydocs/report/task_m101_227_*.md`
  - `mydocs/tech/pyo3_binding_implementation_guide.md`
  - `mydocs/tech/ci_proposal_pyo3_bindings.md`
- [ ] 이관 파일 대 `rhwp-python-heuristic/rhwp-python/` 원본 diff 교차 확인 (누락 방지)

### 3. 빌드·테스트 재검증
- [ ] `maturin develop --release` 성공
- [ ] `pytest` 전 테스트 그린 (Phase 1: core 23 + LangChain 29 = 52건)
- [ ] `pyright` 0 errors
- [ ] `maturin build --release` + `maturin sdist`
- [ ] clean venv에서 wheel + sdist 각각 설치 → import → parse end-to-end 검증

### 4. CI 활성화
- [ ] `.github/workflows/release.yml` 적용 (Linux / macOS / Windows × Python 3.9~3.13 abi3)
- [ ] CI 첫 실행 녹색 확인

### 5. TestPyPI 배포 검증
- [ ] PyPI Trusted Publisher 설정 또는 API 토큰 등록
- [ ] TestPyPI에 `rhwp-python` 0.1.0rc1 업로드
- [ ] `pip install -i https://test.pypi.org/simple/ rhwp-python` clean venv 검증

### 6. PyPI 정식 배포
- [ ] `rhwp-python` 0.1.0 업로드
- [ ] `pip install rhwp-python` clean venv 검증
- [ ] PyPI 프로젝트 페이지 메타데이터 확인 (README, 라이선스, 프로젝트 URL)

### 7. 마무리
- [ ] 신규 리포 README에 Phase 2~4 로드맵 요약
- [ ] 이슈 #227에 배포 완료 회신 (PyPI 링크 포함)

## 리스크와 대응

- **`rhwp-python` PyPI 이름 선점됨** → `pyrhwp`로 전환. 이슈 #227에 네이밍 변경 공지
- **submodule 커밋 불일치로 빌드 실패** → Phase 1 검증 시점의 rhwp 커밋 해시를 `.gitmodules` 주석·CHANGELOG에 명시
- **Trusted Publisher 설정 오류** → Stage 5(TestPyPI)에서 먼저 검증 후 정식 배포
- **이관 누락** → Stage 2 말미에 `rhwp-python-heuristic/rhwp-python/` 파일 목록과 신규 리포 diff 교차 확인

## 범위 외 (Phase 2 이후, 신규 리포에서 별도 문서로 진행)

- Phase 2 — 계층 JSON IR 스키마 (재귀 중첩 표, rowspan/colspan, 비의미 셀 시맨틱 태그)
- Phase 3 — `to_markdown()` / `to_html()` view 렌더러 + LangChain·LlamaIndex 로더
- Phase 4 — JSON → HWP 역생성 (IR을 축으로 한 양방향 완성, rhwp 쓰기 API 성숙도에 의존)
