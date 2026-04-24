# v0.3.0 `rhwp-py` CLI — 설계 의사결정 리서치 요약

[v0.3.0/cli.md](../../roadmap/v0.3.0/cli.md) §결정 사항 중 외부 독자가 "왜?" 를 던질 만한 3건 (이름 선정 · 업스트림 overlap=0 정책 · 기본 출력 포맷) 의 업계 선례·대안·실패 시나리오를 기록한다. cli.md 본문이 최종 결정을 기술하고, 본 문서는 그 결정의 근거를 담는다.

## 결정 매트릭스

| # | 이슈 | 결정 | 핵심 근거 |
|---|---|---|---|
| 1 | Python 바인딩 명령어 이름 | **`rhwp-py`** | Python 생태계 관행 (`python-docx` / `pyarrow` / `lxml`) + 명령 이름 충돌 회피 |
| 2 | 상류 바이너리와의 overlap 정책 | **완전 분리 (overlap = 0)** | `docker` vs `podman` 의 "동일 표면" 비용 교훈, `gh` + `git` 의 "부분 중복" 도 우리 맥락에서 비적합 |
| 3 | 기본 출력 포맷 (`ir`/`blocks`) | **JSON 계열 (`blocks`: NDJSON, `ir`: JSON)** | kubectl/aws/gh 의 `-o` 관행 + jq streaming 친화 |

---

## 1. 이름 — `rhwp-py`

### 조사: Python 생태계의 "언어 suffix" binding 작명 실례

| 프로젝트 | PyPI 이름 | `import` 이름 | 설치 시 깔리는 명령 (있다면) | 원본 라이브러리 |
|---|---|---|---|---|
| lxml | `lxml` | `lxml` | 없음 | libxml2 (C) |
| pyarrow | `pyarrow` | `pyarrow` | 없음 (`plasma-store-server` 만, renamed) | Apache Arrow (C++) |
| python-docx | `python-docx` | `docx` | 없음 | Office Open XML 포맷 |
| protobuf (Python) | `protobuf` | `google.protobuf` | 없음 (`protoc` 은 C++) | protoc-gen-* 플러그인 |
| grpcio | `grpcio` | `grpc` | 없음 | gRPC C core |
| grpcio-tools | `grpcio-tools` | `grpc_tools` | 없음 (`python -m grpc_tools.protoc` 로 간접 호출) | protoc |
| pyyaml | `PyYAML` | `yaml` | 없음 | libyaml (C, 선택) |
| uv | `uv` | — | `uv` | Rust 도구 (자체 바이너리 재배포) |
| ruff | `ruff` | `ruff` | `ruff` | Rust 도구 (자체 바이너리 재배포) |

### 관찰

1. **Python 바인딩은 대부분 command 를 깔지 않는다** — 상류 도구가 이미 명령을 제공하면 Python 쪽은 라이브러리만 노출. `grpcio-tools` 의 `python -m grpc_tools.protoc` 패턴이 "우회" 해법으로 정착.
2. **자체 Rust 도구가 본체인 경우만 동일 이름 command 제공** — `uv`, `ruff` 는 "Python 생태계 도구" 이지만 실체는 Rust. PyPI 는 단순 배포 채널 역할. 본 프로젝트는 이와 달리 상류 `rhwp` Rust 바이너리가 이미 존재 — 동일 이름 경쟁이 아니라 **보완** 위치.
3. **`python-` 접두 / `-py` 접미 패턴은 이름 충돌 방지 용도** — `python-docx` 는 `docx` 이름이 이미 선점 (Microsoft) 된 상황 회피. `grpc-web` (JS) vs `grpcio` (Python) 도 같은 패턴.

### 대안 평가

- **`rhwp`**: 상류 바이너리와 PATH 충돌 — `pip install rhwp-python` 후 `rhwp` 가 어느 쪽을 가리키는지 OS/shell/설치 순서에 따라 비결정적. 업스트림 메인테이너 동의 없이 이름 선점하면 [PEP 541](https://peps.python.org/pep-0541/) dispute 소지.
- **`hwp`**: 포맷명만 표시 — 다른 HWP 도구 (`pyhwpx`, `pyhwp`) 도 이름 욕심 낼 여지 있고 "어느 언어 구현인지" 불명. shell 자동완성에서 구분 불가.
- **`pyrhwp`**: 접두 패턴. `pyOpenSSL` / `pyyaml` 과 비슷하지만, 우리 PyPI 패키지명 `rhwp-python` 과 **접두·접미 방향이 역전** — 일관성 붕괴.
- **`hwprag`**: RAG 강조. 기능 범위가 "RAG 전용" 이 아니고 (Document IR / Schema export 등 범용), 이름이 스코프를 오도.
- **`rhwp-py`**: `rhwp-python` 패키지명과 접미가 일관. Python 레이어임을 명시. 상류와 문자 단위로 구분 (`rhwp` 와 `rhwp-py` 는 tab completion 에서도 섞이지 않음).

### 실패 시나리오 (선택 후에도 감시 필요)

- **업스트림이 추후 PyPI `rhwp-python` 을 가져감** — 이 패키지는 `pip install` 시 obsolete 되고, `rhwp-py` 명령 소유권도 이전. 현재 커뮤니티 배포 지위를 README 에 명시해 둔 상태.
- **Homebrew `rhwp-py` formula 충돌** — tap 에 같은 이름이 있으면 업스트림 `rhwp` formula 와 공존 가능하나 사용자 혼동 여지. 필요 시 formula 이름을 `rhwp-python` 로 분리.

### 출처

- PEP 541 (Package Index Name Retention): <https://peps.python.org/pep-0541/>
- python-docx naming rationale: <https://python-docx.readthedocs.io/en/latest/>
- grpcio-tools `python -m grpc_tools.protoc` 패턴: <https://grpc.io/docs/languages/python/quickstart/>

---

## 2. 상류 바이너리와 overlap=0

### 조사: "동일/유사 기능 도구의 이름·스코프 공존 패턴"

| 사례 | 이름 관계 | 기능 overlap | 결과 |
|---|---|---|---|
| `docker` vs `podman` | 완전 분리 | **거의 100%** (의도적으로 호환) | podman 이 `alias docker=podman` 권장 — 이름 경쟁, 사용자 혼동 지속 |
| `gh` vs `git` | 완전 분리 | **부분** (gh 가 일부 git 명령을 상위 개념으로 래핑) | 성공적 — 역할 분담 명확 (git=VCS, gh=GitHub 플랫폼) |
| `kubectl` vs `oc` (OpenShift) | 완전 분리 | **~90%** (oc 는 kubectl 의 superset) | OpenShift 고유 기능만 쓰는 사용자에게 혼란, 문서 중복 |
| `aws` vs `aws-shell` | 접미 분리 | 부분 | aws-shell 은 REPL 레이어만 — 명확한 층위 분리 |
| `npm` vs `yarn` vs `pnpm` | 완전 분리 | **거의 100%** | 생태계 분화, 세 도구 모두 문서·CI·IDE 통합 비용 부담 |
| `pip` vs `uv pip` | namespace 분리 | **거의 100%** | uv 가 pip 호환성을 명시적으로 광고 — overlap 을 feature 로 |

### 교훈

- **Overlap 100% 는 "대체재 경쟁"** — 유지보수 중복, 버그 프로필 divergence, 사용자가 "어느 쪽 이슈에 리포트해야 하는지" 헷갈림.
- **Partial overlap 은 추상화 레이어 차이가 명확할 때만 성립** — `gh` 는 "GitHub 플랫폼 명령" 이라는 상위 개념. 우리가 만약 `rhwp-py export-svg` 를 제공하면 내부적으로 상류 `rhwp` 를 호출하거나 rhwp 의 Rust 렌더러를 FFI 로 재노출해야 하는데, **어느 쪽이든 버그 표면이 두 배**.
- **Overlap 0 이 "역할 분담" 메시지를 가장 명확히 전달** — 사용자는 "렌더는 `rhwp`, 구조 추출은 `rhwp-py`" 로 즉시 학습.

### 본 프로젝트의 특수성

- **`rhwp` 와 `rhwp-py` 는 동일 Rust 코어를 공유** (`external/rhwp` submodule). 즉 동일 파싱 결과.
- `rhwp` 가 이미 제공하는 것: `export-svg` / `export-pdf` / `info` / `dump` / `dump-pages` / `diag` / `ir-diff` / `convert` / `thumbnail`.
- Python 레이어 고유: **Pydantic IR 모델 · JSON Schema export · LangChain Document 매핑 · shell-friendly NDJSON 스트리밍**. 이 중 어느 것도 상류 Rust 바이너리가 제공하지 **않는다**.

따라서 **완전 분리가 "두 도구가 서로 대체 관계가 아님" 을 가장 분명하게 알린다**. README 에 권장 조합 워크플로우 한 섹션만 추가하면 사용자 학습 부담 최소.

### 실패 시나리오

- **사용자가 `rhwp-py render` 를 기대하고 혼란** — README / `rhwp-py --help` 초반에 "렌더링은 업스트림 `rhwp export-svg` 사용" 을 명시해 redirect.
- **상류가 Python IR export 기능을 직접 추가** — 그 시점에 overlap 이 생기며, `rhwp-py` 는 deprecate 경로를 시작. 현재로서는 상류가 Python 레이어를 공식 채택할 계획 없음이 [edwardkim/rhwp#227](https://github.com/edwardkim/rhwp/issues/227) 합의에 명시.

### 출처

- gh CLI scope rationale: <https://cli.github.com/manual/>
- podman-docker 호환성 논의: <https://podman.io/docs/installation#podman-docker>
- pip vs uv pip 호환성 전략: <https://docs.astral.sh/uv/pip/compatibility/>

---

## 3. 기본 출력 포맷 — JSON 계열

### 조사: 구조화 출력 CLI 의 기본값 관행

| CLI | 기본 포맷 | 대체 옵션 | 비고 |
|---|---|---|---|
| `kubectl get` | table (사람용) | `-o json` / `yaml` / `jsonpath` | 기본은 terminal UX, 스크립팅은 명시 플래그 |
| `aws` | JSON | `--output table` / `text` / `yaml` | 기본이 JSON — AWS 는 "스크립팅이 primary use case" 로 설계 |
| `gh` | table-like | `--json <fields>` | 기본은 사람용, JSON 은 필드 선택 강제 |
| `docker ps` | table | `--format '{{json .}}'` | Go 템플릿으로 변형 |
| `jq` | JSON (가공) | `--raw-output` | JSON 이 자연 |
| `hugr-cli` / `pipx` etc. | mixed | — | 소규모 도구는 혼재 |

### 교훈

- **"대화형 탐색" primary use case → table/text 기본** (kubectl, gh, docker)
- **"스크립팅/pipeline" primary use case → JSON 기본** (aws, jq)
- 우리 `rhwp-py` 의 예상 use case:
  - `parse` / `version` — 빠른 확인용 → **text 기본**
  - `ir` — 파일 변환 후 jq/스크립트 소비 → **JSON 기본**
  - `blocks` — shell pipeline 에서 필터·변환 → **NDJSON 기본** (줄 단위 스트리밍)
  - `chunks` — vector indexer 로 직접 투입 → **NDJSON 기본**
  - `schema` — 파일 리다이렉션이 전형 → **JSON 기본**

### NDJSON vs JSON array 선택

- **NDJSON (한 줄 한 객체)**
  - jq streaming: `rhwp-py blocks file.hwp | jq -c 'select(.kind == "table")'`
  - `wc -l`, `head`, `tail` 에 자연 매핑
  - 파이프 상대방이 스트리밍 소비 (vector-indexer 가 한 블록씩 임베딩) 가능
- **JSON array (`[{...}, {...}]`)**
  - `json.load()` 한 방에 파싱 가능, 일부 도구가 array 만 수용
  - 단점: 전체를 버퍼링해야 — 대형 문서 (수천 블록) 에서 메모리 압박, 스트리밍 불가

`ir` 서브커맨드는 "문서 전체를 하나의 객체로" 출고하므로 JSON array 가 아닌 **단일 object (JSON)** 가 자연. `blocks` / `chunks` 는 열 단위 스트림이라 NDJSON.

### kubectl/aws/gh 기준 추가 검증

- `kubectl get pods -o json` — array 기본, `-o jsonpath` 로 단일 값 추출
- `aws s3api list-objects` — `Contents` 배열 안에 객체 — 하지만 `--output json` 은 하나의 객체로
- `gh issue list --json number,title` — JSON array
- 세 도구 모두 "복수 아이템" 을 array 로, "단일 문서" 를 object 로. 우리 설계와 일치.

### 실패 시나리오

- **사용자가 `rhwp-py blocks file.hwp | python -c "import json, sys; json.load(sys.stdin)"` 기대**
  - NDJSON 이라 `json.load` 는 첫 줄만 파싱
  - 해법: `--format json` 플래그로 array 출력 가능. 문서에 예시 명시.
- **Windows CMD 의 파이프 문자 인코딩 이슈** — NDJSON 은 모든 플랫폼에서 줄바꿈 안전 (`\n` 고정). PowerShell 은 `ConvertFrom-Json -AsHashtable` 로 NDJSON 스트리밍 지원.

### 출처

- NDJSON 표준: <http://ndjson.org/>
- kubectl output options: <https://kubernetes.io/docs/reference/kubectl/#output-options>
- aws CLI output format: <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-output-format.html>
- gh `--json` design rationale: <https://github.blog/2020-09-17-github-cli-1-0-is-now-available/#scripting-with-gh>

---

## 변경 파급 — cli.md 본문 교정 목록

본 리서치 결과를 cli.md 본문과 대조할 때 교정/보강할 지점:

1. **§이름 선정** — 현재 대안 비교 테이블에 "Python 생태계 binding 작명 패턴" 근거 한 문장 추가 (본 문서 §1 참조)
2. **§업스트림 경계** — overlap=0 이 "유지보수 중복 회피" 이외에도 "역할 분담 메시지 명확성" 이라는 근거가 있음을 명시
3. **§서브커맨드 스펙** — `blocks` 의 기본 포맷이 NDJSON 인 이유를 한 줄 추가 (streaming pipeline 친화)
4. **§결정 사항 테이블 #3** — "shell pipeline 과 CI 친화" 표현을 "kubectl/aws/gh 의 스크립팅-primary 관행 준수" 로 구체화

본 문서를 cli.md 에서 `상세 증거: [cli-design-research.md](../../design/v0.3.0/cli-design-research.md)` 로 cross-link — v0.2.0 ir.md ↔ ir-design-research.md 와 동일 패턴.

## 참조

- [roadmap/v0.3.0/cli.md](../../roadmap/v0.3.0/cli.md) — 본 리서치의 결정 요약
- [roadmap/v0.2.0/ir.md](../../roadmap/v0.2.0/ir.md) §방향 전환 배경 — CLI 폐기→재도입 맥락
- [design/v0.2.0/ir-design-research.md](../v0.2.0/ir-design-research.md) — 리서치 문서 포맷 선례
