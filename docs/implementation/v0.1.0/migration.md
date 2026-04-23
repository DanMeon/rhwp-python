# 분사·이관 작업 로그

**작업일**: 2026-04-23
**작업자**: Claude (Opus 4.7) + DanMeon
**범위**: `rhwp-python-heuristic/rhwp-python/` → `DanMeon/rhwp-python` 별도 리포 분사

계획 문서: [roadmap/v0.1.0/rhwp-python.md](../../roadmap/v0.1.0/rhwp-python.md)

## 단계별 진행

### 1. 병렬 탐색 — 정보 수집

네 개의 탐색 에이전트를 병렬 스폰해 초기 상태를 파악:

| 에이전트 | 대상 | 결과 |
|---|---|---|
| A | `~/Desktop/kevin/python-template` | copier 9.14.0 템플릿 구조, 변수, 조건부 파일 |
| B | `rhwp-python-heuristic/rhwp-python/` | 소스 인벤토리, Cargo/pyproject 요점, conftest 경로 |
| C | rhwp 라이선스·저작권 | MIT, Edward Kim 원저작자, pyproject authors 병기 권장 |
| D | 현재 `rhwp-python/` | 1 커밋 초기 상태, origin=DanMeon/rhwp-python |

### 2. copier 초기화

```bash
copier copy /Users/kevin/Desktop/kevin/python-template . \
  -d project_name=rhwp-python \
  -d project_description="PyO3 Python bindings for rhwp — zero-dependency HWP parser" \
  -d package_name=rhwp \
  -d author_name=DanMeon -d github_owner=DanMeon \
  -d visibility=public -d license=MIT \
  -d min_python=3.10 -d "python_versions=3.10, 3.11, 3.12, 3.13" \
  -d use_cli=false -d use_pypi_publish=true -d cov_fail_under=60 \
  --defaults --trust
```

생성된 것 중 rhwp-python 환경에 **맞지 않는 것** — hatchling 기반 pyproject, `src/rhwp/` 레이아웃, 순수 Python CI. 이후 교체.

유지된 것 — `.gitignore`, `.pre-commit-config.yaml` 기본 골격, `.github/CODEOWNERS`, `.github/dependabot.yml`, `CONTRIBUTING.md`, `LICENSE`, codeql.yml.

### 3. 원본 소스 이관

`rsync -a` 로 `__pycache__` / `*.so` 제외 후 복사:

```bash
rsync -a --exclude='__pycache__' $SRC/src/ src/
rsync -a --exclude='__pycache__' --exclude='*.so' $SRC/python/ python/
rsync -a --exclude='__pycache__' $SRC/tests/ tests/
cp -r $SRC/benches ./
```

`diff -rq` 교차 검증 — `src/` `python/` `benches/` 100% byte-identical, `tests/` 는 `conftest.py` 만 의도적으로 다름 (경로 보정).

### 4. submodule 추가 + commit 고정

원래 계획은 fork 커밋 `d3e91b5` 였으나 upstream 미반영 (fork 전용). `git merge-base test/pyo3-sandbox upstream/main` 결과 **`163621382ba13be233b155df050375e900a038e2`** (upstream/main HEAD) 가 코어 상태 동등. 이 커밋에 submodule 고정:

```bash
git submodule add https://github.com/edwardkim/rhwp.git external/rhwp
cd external/rhwp && git checkout 163621382ba13be233b155df050375e900a038e2
```

`.gitmodules` 에 Phase 1 commit 주석 명시.

### 5. 설정 파일 교체·보정

| 파일 | 변경 |
|---|---|
| `pyproject.toml` | maturin 백엔드, `name="rhwp-python"`, 이중 authors, `license-files=["LICENSE","external/rhwp/LICENSE"]` |
| `Cargo.toml` | `rhwp = { path = "external/rhwp" }`, `[workspace]` 자기 선언, include 에 LICENSE 추가 |
| `LICENSE` | MIT, Edward Kim + DanMeon 이중 copyright |
| `README.md` | 한글 기본 + 언어 스위처 |
| `README_EN.md` | 영문 대응본 |
| `CHANGELOG.md` | 0.1.0, commit `1636213` 언급 |
| `.gitignore` | `target/` `*.so` `*.pyd` `*.dylib` `Cargo.lock` |
| `tests/conftest.py` | `parent.parent.parent/samples` → `parent.parent/external/rhwp/samples` |
| `benches/bench_gil.py` | 동일 경로 보정 (검증 지적 후 수정) |

### 6. CI 워크플로우

copier 생성 `ci.yml`/`publish.yml` 삭제 후 재작성:

- `ci.yml` — 3 OS × py3.9/3.10/3.11/3.12/3.13 test + pyright (정상 + intentional 4건) + `test-core-only` importorskip 29 skip 검증
- `publish.yml` — `on: release: published` 트리거, `verify-version` (Cargo.toml vs tag) + build 매트릭스 (Linux x86_64/aarch64, macOS x86_64/aarch64, Windows) + sdist + Trusted Publisher OIDC. xlstruct 스타일 참조. TestPyPI 단계 의도적 제외

### 7. 독립 검증 에이전트 팀

`code-reviewer` + `architect-reviewer` 를 병렬 스폰하고 독립 검증:

- code-reviewer: 릴리스 블로커 없음. 중요 지적 3건 (license-files 확장, ci.yml grep 단어경계, cross-arch wheel verify 공백)
- architect-reviewer: 계획 §2–§6 충족도 평가. 구조적 지적 8건 (bench_gil 경로, pre-commit 경로, CONTRIBUTING 경로, CHANGELOG 테스트 수, min_python 불일치, TestPyPI 부재, sdist verify 한계)

상세는 [verification/v0.1.0/spinoff-review.md](../../verification/v0.1.0/spinoff-review.md).

### 8. 지적사항 반영

- `benches/bench_gil.py` 경로 보정
- `.pre-commit-config.yaml` `python/tests/benches` 로 변경
- `CONTRIBUTING.md` `--group all`, 경로 수정, Python 3.9+
- `pyproject.toml` `license-files` 확장
- `ci.yml` grep 단어경계 (`'(^|[^0-9])29 skipped([^0-9]|$)'`)
- `ci.yml` Python 매트릭스 3.9~3.13 전체로 확장 (사용자 요청)
- `release.yml` → `publish.yml` rename, TestPyPI 제거, environment 제거 (사용자 요청 / xlstruct 스타일)

### 9. 예제 스크립트

- `examples/01_parse_basic.py`, `02_render_svg_pdf.py`, `03_langchain_rag.py` — typer 기반, `--help` 지원
- `pyproject.toml` 에 `examples` extras (`typer>=0.12`) 추가
- `examples/README.md` — 설치/사용법 + v0.2 CLI 승격 계획 언급

### 10. 문서 구조 확립

rhwp-python 자체 컨벤션 정립: `roadmap / design / implementation / verification` 4축, 버전이 있는 영역은 `v<X.Y.Z>/` 서브디렉토리 (git tag 와 동일 prefix). 불필요·중복 문서(원본 단계별 로그, 완료 감사 보고, CI 제안서, release-checklist 중복) 제거해 최소 세트로 정리.

## 최종 docs 구조

```
docs/
├── roadmap/
│   ├── README.md                        버전 매핑 인덱스 + 연표
│   ├── phase-2.md / phase-3.md / phase-4.md
│   ├── v0.1.0/rhwp-python.md            현재 릴리스 런칭 계획
│   └── v0.2.0/cli.md
├── design/
│   └── pyo3-bindings.md                 PyO3 바인딩 기술 가이드
├── implementation/
│   └── v0.1.0/migration.md              본 문서 (분사 작업 로그)
└── verification/
    └── v0.1.0/spinoff-review.md         code-reviewer + architect-reviewer 종합
```

## 원본 대비 주요 변경점 (코드)

| 파일 | 변경 |
|---|---|
| `Cargo.toml` | `path = ".."` → `"external/rhwp"`, include 에 `/LICENSE` 추가, repository URL 변경 |
| `pyproject.toml` | `name` 변경, authors 이중, URL 변경, `license-files` 명시, `langchain` extras 명칭 조정 |
| `tests/conftest.py` | REPO_ROOT 계산 한 단계 축소 + SAMPLES 경로 submodule 하위로 |
| `benches/bench_gil.py` | 위와 동일 보정 |

이 외의 Rust/Python 소스는 byte-identical.
