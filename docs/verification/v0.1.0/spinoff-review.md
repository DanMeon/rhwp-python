# 분사 작업 독립 검증 리포트

**Status**: Frozen · **GA**: v0.1.0 · **Last updated**: 2026-04-23

**검증일**: 2026-04-23
**검증 방식**: `code-reviewer` + `architect-reviewer` 서브에이전트를 **독립 컨텍스트**로 병렬 스폰. 각 에이전트는 이 세션의 작업 히스토리를 보지 않고 파일 상태만으로 판정.

범위: 분사 시점에 생성·수정된 config·CI·라이선스 파일 + 전체 리포 구조가 계획 문서 §2–§6 과 부합하는지.

## 검증 팀 구성

| 에이전트 | 역할 | 초점 |
|---|---|---|
| `code-reviewer` | 파일 단위 리뷰 | 정확성, 일관성, 경로, 라이선스 문구, CI job 논리 |
| `architect-reviewer` | macro 관점 리뷰 | 계획 문서 부합성, 구조적 리스크, 잠재 실패 경로 |

## 종합 판정

**릴리스 블로커 없음.** 다만 구현 품질·운영 안전성에서 개선 여지 다수. 아래 지적사항 중 **우선순위 높은 8건은 분사 세션 중 즉시 반영**, 나머지는 운영 중 개선.

## code-reviewer 주요 지적 (3건)

### 중요 이슈

1. **`pyproject.toml` `license-files = ["LICENSE"]` 만 있어 rhwp 코어 원본 LICENSE 가 wheel metadata 에서 누락**
   - 현재 LICENSE 는 고지만 담고, `external/rhwp/LICENSE` 는 sdist 내에만 존재
   - **대응**: `license-files = ["LICENSE", "external/rhwp/LICENSE"]` 로 확장 (반영 완료)

2. **`release.yml` cross-arch wheel install verify 공백**
   - `wheels-linux-aarch64`, `wheels-macos-x86_64` 는 업로드 전 install 검증 없음
   - **현재 상태**: release.yml 을 xlstruct 스타일 publish.yml 로 대체하면서 verify-wheel 단계 제거. cross-arch verify 는 v0.x 에서 별도 job 추가 고려

3. **`ci.yml` importorskip 검증의 `grep -qE "29 skipped"` 단어경계 부재**
   - "129 skipped" 도 match → false-pass 가능
   - **대응**: `grep -qE '(^|[^0-9])29 skipped([^0-9]|$)'` (반영 완료)

### 사소 이슈

- `release.yml:106,151` `paragraph_count == 921` 하드코딩 (submodule 승급 시 수동 업데이트 필요) — 의도적 sanity check 로 유지
- `pyproject.toml` Edward Kim author 이메일 누락 — 의도적 (원본 fork 에도 없음)
- sdist verify 가 checkout samples 를 참조 — 엄밀히는 "sdist 단독 설치 가능성" 미검증

### 통과 확인 (요약)

- §2 submodule `1636213` 고정 — `.gitmodules` + `CHANGELOG` + `git submodule status` 3자 일치
- §2 `Cargo.toml` path 교정, workspace 격리
- §2 conftest fixture 경로 + samples 파일 실존 (`aift.hwp`, `table-vpos-01.hwpx`)
- §3 `dynamic = ["version"]` + `[tool.maturin]` 명세 완비
- §4 publish.yml Trusted Publisher OIDC + 빌드 매트릭스
- §6 `[project.urls]`, LICENSE 이중 저작권, CHANGELOG 버전 + commit 언급, CODEOWNERS 단독

## architect-reviewer 주요 지적 (8건)

### 구조적 리스크 (수정 권장)

1. **`benches/bench_gil.py` 경로 보정 누락**
   - `SAMPLES = REPO_ROOT / "samples"` 가 원본 그대로. README Performance 섹션이 이 스크립트 재현을 인용하므로 외부 사용자 즉시 실패
   - **대응**: conftest.py 와 동일하게 `parent.parent / external/rhwp/samples` 로 수정 (반영 완료)

2. **`.pre-commit-config.yaml` 경로가 copier 기본값 (`src/`, `src/rhwp/`) 그대로**
   - 이 리포는 Python 패키지가 `python/rhwp/`, `src/` 는 Rust 소스 디렉토리. ruff 가 Rust 파일 스캔하거나 pyright 가 없는 경로 조회
   - **대응**: `python/ tests/ benches/` 로 수정 (반영 완료)

3. **`CONTRIBUTING.md` 도 동일 경로 오류 + `--group dev` 만으로는 pytest/pyright 누락**
   - **대응**: `--group all`, 경로 수정, Python 3.9+ (반영 완료)

4. **`.copier-answers.yml` `min_python: '3.10'` vs `pyproject.toml` `>= 3.9` 불일치**
   - pyproject 가 SSoT 이므로 현실 충돌 없으나 copier update 시 혼란
   - **현재 상태**: `.copier-answers.yml` 은 초기화 메타데이터. pyproject 주석으로 SSoT 선언 — 릴리스 블로커 아님

5. **`release.yml` Python 매트릭스 단일값 (`"3.12"`)**
   - abi3 특성상 한 인터프리터 빌드로 전 버전 커버 → 기능적으로 OK. 단 계획 §4 "3.9~3.13" 문자 해석과 불일치
   - **대응**: 계획 §4 의 의도는 "전 버전 호환 wheel" → abi3 로 충족. ci.yml 에서만 매트릭스 확장 (사용자 결정으로 3.9~3.13 전체로, 반영 완료)

6. **TestPyPI 스테이지 부재**
   - 계획 §5 는 rc1 을 TestPyPI 먼저 검증하는 흐름
   - **대응**: 사용자 판단으로 "CI 니까 바로 올려도 된다" — TestPyPI 스테이지 제거. 필요 시 v0.x 에서 rc 태그 분기로 추가 가능

7. **CHANGELOG 테스트 수치 (`48 core + 29 LangChain = 77`) vs 계획 문서 (`23 + 29 = 52`) 불일치**
   - 계획 문서가 Stage 6 시점 수치로 낡음. CHANGELOG 가 Stage 8 최종 수치라 정확
   - **현재 상태**: CHANGELOG 값 유지 (`def test_` 정적 72 + parametrize 감안 77 일치 가능성). 로드맵 0.1.0 문서는 테스트 수치를 아예 언급 안 해 혼선 원천 제거

8. **sdist verify job 이 sdist 단독이 아닌 checkout 의 samples 를 읽음**
   - 의도된 설계지만 이름만으로는 혼란
   - **현재 상태**: publish.yml 에서 verify-wheel/sdist 간략화. v0.x 에서 "sdist-only install + parse" 전용 job 분리 고려

### 검증된 핵심 결정

- PyPI 이름 `rhwp-python` vs import `rhwp` 매핑 (`pyproject.toml`, `python/rhwp/__init__.py`, `[tool.maturin] module-name="rhwp._rhwp"` 3자 정합)
- 업스트림 `1636213` submodule 고정 (`.gitmodules` + CHANGELOG + `git submodule status` 3자 일치)
- 이중 copyright LICENSE (MIT 조항의 저작권 고지 유지 의무 충족)
- 독립 cargo workspace 선언 (현재 submodule 에 workspace 없어 실제 충돌 없지만 미래 upstream 변경 대비 방어막)
- docs/phase1 구조의 12개 문서 전부 이관
- Phase 2~4 혼입 없음 (read/render only, no serialization 유지)
- `uv.lock` 미이관 / Cargo.lock gitignore — 라이브러리 crate 관례 일치

## 미해결 항목 (릴리스 후 또는 v0.x 에서)

| 항목 | 우선순위 | 비고 |
|---|---|---|
| cross-arch wheel install verify | 중 | v0.x 에서 별도 job |
| sdist 단독 설치 가능성 검증 | 중 | v0.x tmp-dir extract 후 install 방식 |
| CHANGELOG 테스트 수치 검증 | 낮음 | 릴리스 당일 `pytest --collect-only -q` 결과로 재기록 |

## 결론

분사 시점 기준으로 **계획 문서 §2–§6 핵심 요구사항 전부 충족**, 에이전트 지적 중 우선순위 높은 항목 전부 반영. 남은 개선은 v0.x 운영 중 점진 반영. 0.1.0 릴리스를 막을 이슈 없음.
