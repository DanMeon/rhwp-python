# v0.3.0 — `rhwp-py` 얇은 CLI

v0.2.0 에서 폐기했던 CLI 를 **이름을 분리한 Python 고유 command** 로 재도입한다. `pip install rhwp-python` 만 한 사용자가 shell pipeline 에서 바로 쓸 수 있게 하되, 상류 Rust `rhwp` 바이너리와 기능을 **중복 구현하지 않는다** — Python 레이어 고유 가치 (Document IR, LangChain 청크) 에 집중.

주요 결정 (이름 선정 / overlap=0 정책 / 기본 출력 포맷) 의 업계 선례·대안·실패 시나리오는 별도: [cli-design-research.md](../../design/v0.3.0/cli-design-research.md).

## 배경 — 재도입 근거

v0.2.0 ir.md §방향 전환 배경 에서 CLI 를 폐기한 이유는 "업스트림 Rust 크레이트가 이미 `rhwp` 바이너리를 제공해 PATH 충돌" 이었다. 같은 문서 끝부분:

> CLI 는 영구 비범위는 아니되 **업스트림이 커버하지 않는 Python 고유 기능이 충분히 축적된 이후에만** 재검토한다 (예: `rhwp-py chunks` — LangChain 청킹, `--json` 출력 등. 네임스페이스는 업스트림과 구분).

v0.2.0 으로 Document IR / `iter_blocks` / LangChain `ir-blocks` 모드가 안정화되어 "Python 고유 기능" 축적 조건이 충족됐다. 따라서 v0.3.0 에 CLI 를 **별도 이름** 으로 제공한다.

## 이름 선정 — `rhwp-py`

| 후보 | 업스트림 충돌 | 가독성 | 타이핑 |
|---|---|---|---|
| `rhwp` | **충돌** (상류 바이너리와 동일) | 최상 | 최소 |
| `rhwp-py` | 없음 | 명확 | 간결 |
| `pyrhwp` | 없음 | 접두어가 타이밍 애매 | 같음 |
| `hwp` | 상류 CLI 와 혼동 여지 | 단일 HWP 를 암시 | 최소 |
| `hwprag` | 없음 | RAG 강조 | 타이핑 부담 |

**`rhwp-py`** 채택 — "Python 레이어임" 을 명시하면서 상류와 식별 가능. PyPI 패키지명 `rhwp-python` 과 일관 (`-python` → `-py`).

**업스트림이 추후 `rhwp-python` PyPI 이름을 가져가면** `rhwp-py` 명령도 함께 이전된다 — 합의 시 메이저 버전 업과 함께 deprecate/이관 경로 제공.

## 목표와 비목표

### v0.3.0 목표

1. **Python 고유 기능을 shell 에서 바로**: `rhwp-py parse` / `rhwp-py ir` / `rhwp-py blocks` / `rhwp-py chunks` / `rhwp-py schema`
2. **IR 중심 UX**: 텍스트보다는 **구조화 JSON** 이 first-class output. `--format json|ndjson|text` 로 기본값은 shell-friendly 선택
3. **LangChain 청크 직접 출력**: 별도 Python 스크립트 없이 `rhwp-py chunks file.hwp --size 500 --format jsonl | vector-indexer`
4. **JSON Schema 로컬 export**: `rhwp-py schema > hwp_ir.json` 으로 in-package 스키마를 파일에 저장 (외부 도구·CI 파이프라인 편의)
5. **`typer.testing.CliRunner` 기반 smoke 테스트** 전 커맨드 커버

### 비목표 (v0.3.0)

- **렌더링** (`svg`/`pdf`) — 업스트림 `rhwp export-svg` / `rhwp export-pdf` 사용 권장. 재구현 없음
- **진단/덤프** (`info`/`dump`/`dump-pages`/`diag`/`ir-diff`) — 업스트림 전담 영역
- **포맷 변환** (`convert`/`thumbnail`) — 업스트림 제공
- **업스트림 바이너리 실행 래퍼** (e.g. `rhwp-py render` 가 내부적으로 `rhwp` 를 spawn) — scope creep. 사용자가 두 명령을 직접 조합
- **대화형 REPL / 웹 UI** — 별도 프로젝트 영역

### 영구 비범위

- `rhwp` 이름 선점 (PyPI 또는 PATH) — 업스트림 공식 배포 여지 유지

## 커맨드 트리

```
rhwp-py
├── parse <path>                   기본 정보 (섹션/단락/페이지 수, rhwp 버전)
├── ir <path> [--out FILE] [--indent N]
│                                  전체 IR 을 JSON 으로 출력 (stdout 또는 파일)
├── blocks <path> [OPTIONS]        블록 스트림
│   --scope body|furniture|all       (default: body)
│   --kind paragraph|table|all       (default: all)
│   --recurse / --no-recurse         (default: recurse)
│   --format json|ndjson|text        (default: ndjson)
│   --limit N
├── chunks <path> [OPTIONS]        LangChain 청크 스트림 (cli[chunks] extras)
│   --mode single|paragraph|ir-blocks (default: paragraph)
│   --size N                          (default: 500)
│   --overlap N                       (default: 50)
│   --format json|ndjson|text
├── schema [--out FILE] [--indent N]
│                                  in-package Document IR JSON Schema 출력
└── version                        rhwp-python + rhwp 코어 버전 출력
```

**글로벌 옵션** (모든 서브커맨드):

- `--quiet / -q` — stderr 메시지 최소화
- `--help` — typer 기본

**Exit code 규약**:

- `0` — 성공
- `1` — 사용자 오류 (파일 없음, 유효하지 않은 옵션 조합, 파싱 실패)
- `2` — extras 미설치 (예: `chunks` 호출했으나 `langchain-text-splitters` 부재)

## 서브커맨드 스펙

### `parse`

```
$ rhwp-py parse report.hwp
sections=3  paragraphs=921  pages=74
rhwp-python=0.3.0  rhwp-core=0.7.3
```

간단 요약만. 텍스트 추출은 `rhwp-py blocks --kind paragraph --format text` 로 유도.

### `ir`

```
$ rhwp-py ir report.hwp > report.ir.json
$ rhwp-py ir report.hwp --indent 2 | jq '.body[0]'
$ rhwp-py ir report.hwp --out report.ir.json
```

전체 `HwpDocument.model_dump_json(indent=...)` 를 stdout 또는 파일로. 파이프 유도형 UX — shell 에서 `jq` / `grep` 과 조합 자연스럽게.

### `blocks`

`iter_blocks(scope, recurse)` 의 CLI 노출. 기본 `ndjson` (한 줄 한 블록) — shell 에서 `xargs`/`awk` 로 stream 처리 쉬움.

```
$ rhwp-py blocks report.hwp --kind table --format json | jq '.rows'
$ rhwp-py blocks report.hwp --format text  # 단락/표 텍스트만
```

`--format text` 는 ParagraphBlock 은 `text`, TableBlock 은 `text` (평문 탭/개행 구분) 를 이어붙임. `--format json` 은 `ir.body` 의 list 를, `--format ndjson` 은 블록 당 한 줄.

### `chunks`

LangChain `RecursiveCharacterTextSplitter` 결과를 Document 단위로 출고.

```
$ rhwp-py chunks report.hwp --size 1000 --overlap 100 --format jsonl \
    | vector-store-indexer
```

`--mode ir-blocks` 는 표를 **청킹하지 않고 단일 Document 로 유지** (HtmlRAG 패턴). extras 부재 시 exit 2.

### `schema`

```
$ rhwp-py schema > hwp_ir.json
$ rhwp-py schema --out schemas/hwp_ir_v1.json --indent 2
```

`rhwp.ir.schema.export_schema()` 결과를 stdout/파일로. `python -m rhwp.ir.schema` 와 동일하지만 CLI 도구 인터페이스 일관성 위해 노출.

### `version`

```
$ rhwp-py version
rhwp-python 0.3.0
rhwp-core   0.7.3
```

## 업스트림 `rhwp` 바이너리와의 경계

| 작업 | 도구 | 근거 |
|---|---|---|
| HWP/HWPX → 텍스트/IR/블록/청크 | **`rhwp-py`** | Python IR · LangChain 은 Python 레이어 전용 |
| JSON Schema export | **`rhwp-py schema`** | 스키마 주인이 Python 패키지 |
| SVG / PDF 렌더링 | 상류 `rhwp export-svg/pdf` | 네이티브 렌더러가 성능·일관성 우위 |
| 메타데이터·조판 덤프 (`info`/`dump`/`dump-pages`) | 상류 `rhwp` | 파서 내부 구조 접근이 필요 — Rust 에서 직접이 명쾌 |
| 라운드트립 진단 (`diag`/`ir-diff`) | 상류 `rhwp` | HWP↔HWPX Parser IR 비교는 상류 전용 |
| 포맷 변환·썸네일 | 상류 `rhwp convert/thumbnail` | 네이티브 렌더러 필요 |

README 에 **두 도구를 조합하는 권장 워크플로우** 한 섹션 추가:

```bash
# 구조 추출은 rhwp-py, 시각 출력은 업스트림 rhwp
rhwp-py ir report.hwp > report.ir.json
rhwp export-svg report.hwp -o svg/
```

## 의존성 / 배포

### 새 extras 축

```toml
[project.optional-dependencies]
cli = ["typer>=0.12"]
# ^ 기존 langchain / examples 는 유지. chunks 서브커맨드는 langchain-text-splitters 도 요구:
cli-chunks = ["typer>=0.12", "langchain-core>=0.2", "langchain-text-splitters>=0.2"]
```

`pip install "rhwp-python[cli]"` 로 `rhwp-py` 명령 활성화. `chunks` 서브커맨드 사용자는 `[cli-chunks]` 또는 `[cli,langchain]` 조합.

### Entry point

```toml
[project.scripts]
rhwp-py = "rhwp.cli:app"
```

CLAUDE.md 전역 규칙 "Typer 사용. 단일 커맨드는 `typer.run(main)`, 다중 커맨드는 `app = typer.Typer()`" 준수 — 서브커맨드 있으므로 후자.

### `typer` 미설치 시 동작

`rhwp.cli` 모듈 import 시점에 typer 체크 → `ImportError` 발생하면 친절한 에러:

```
rhwp-py requires `typer`. Install with:
    pip install "rhwp-python[cli]"
```

Entry point stub 은 typer import 를 **지연 로드** — `rhwp.cli.app` 접근 시점에만 import 시도.

## 구현 스테이지 분할

| Stage | 내용 | 산출물 |
|---|---|---|
| **S1 — CLI 스켈레톤** | `python/rhwp/cli/` 패키지 (`__init__.py`, `__main__.py`, `app.py`), `parse` / `version` / `schema` 서브커맨드, extras 설정, entry point 등록 | `python/rhwp/cli/{__init__.py, __main__.py, app.py}`, `pyproject.toml`, `tests/test_cli.py` |
| **S2 — IR 커맨드** | `ir` / `blocks` 서브커맨드 + `--format json|ndjson|text` 구현 | `python/rhwp/cli/ir.py`, 테스트 확장 |
| **S3 — LangChain chunks** | `chunks` 서브커맨드 (langchain-text-splitters extras gate) | `python/rhwp/cli/chunks.py`, extras-gated 테스트 |
| **S4 — 문서화·검증** | README / examples / CHANGELOG 업데이트, 실제 HWP 파일 대상 수동 검증, 업스트림 조합 워크플로우 섹션 | 문서 전반 |

각 스테이지 완료 시 `docs/implementation/v0.3.0/stages/stage-N.md` 기록 (v0.2.0 패턴과 동일).

## 테스트 전략

### 단위 테스트 (`tests/test_cli.py` — 신규)

- `typer.testing.CliRunner().invoke(app, ["parse", str(sample)])` — 각 서브커맨드 smoke
- `--help` 출력에 모든 서브커맨드 포함 확인
- `--format json` 출력이 `json.loads` 로 파싱되는지
- `--format ndjson` 각 줄이 독립 JSON 으로 파싱되는지
- `version` 출력이 `rhwp.version()` 과 일치
- `schema` 출력이 `rhwp.ir.schema.export_schema()` 와 동등
- Exit code 검증 — 파일 없음 / 유효하지 않은 옵션 / extras 부재 (1 / 2)

### 통합 테스트

- 실제 샘플 `table-vpos-01.hwpx` 로 `blocks --kind table --format ndjson` → 표 개수·구조 확인
- `chunks --mode ir-blocks --format jsonl` → LangChain Document sequence 가 `HwpLoader(mode="ir-blocks")` 와 동일

### CI

- `test-core-only` job (langchain 없음) 에서 `chunks` 호출 시 exit 2 검증
- `typer` 없이 `rhwp-py --help` → 친절한 에러 메시지 검증 (선택)

## 결정 사항

| # | 이슈 | 결정 | 근거 |
|---|---|---|---|
| 1 | 이름 | `rhwp-py` | Python 생태계 binding 작명 관행 (`python-docx`/`pyarrow`/`grpcio-tools`) + 상류 `rhwp` 와 PATH 충돌 회피 — 상세: [cli-design-research § 1](../../design/v0.3.0/cli-design-research.md#1-이름--rhwp-py) |
| 2 | 렌더링 커맨드 | 제공 안 함 | 업스트림 Rust 바이너리가 강력 |
| 3 | 기본 출력 포맷 | `parse`/`version` 은 사람 가독, `ir`/`schema` 는 JSON, `blocks`/`chunks` 는 NDJSON | aws/kubectl/gh 의 "스크립팅 primary 는 JSON 기본" 관행 + jq streaming 친화 — 상세: [§ 3](../../design/v0.3.0/cli-design-research.md#3-기본-출력-포맷--json-계열) |
| 4 | typer 의존성 위치 | `[cli]` extras | core dep 팽창 회피 (CLAUDE.md 규칙) |
| 5 | `chunks` 의 extras | `[cli-chunks]` 또는 `[cli,langchain]` | 별도 gating — typer 만 설치한 사용자에게 langchain 강요 안 함 |
| 6 | 업스트림과의 overlap | 어느 것도 복제하지 않음 (overlap = 0) | `docker`/`podman` 의 동일-표면 비용 교훈 — 역할 분담 메시지 명확성 우선. 상세: [§ 2](../../design/v0.3.0/cli-design-research.md#2-상류-바이너리와-overlap0) |

## 다른 로드맵 문서에의 파급

- `docs/roadmap/README.md` — 버전 계획표에 "v0.3.0 = Phase 2 (IR 확장) + CLI" 로 병기
- `docs/roadmap/v0.2.0/ir.md` — §방향 전환 배경 마지막 문단의 "CLI 재검토" 언급에 본 문서 cross-link
- `docs/roadmap/phase-2.md` — v0.3.0 이 IR 확장 + CLI 두 축임을 언급
- `examples/README.md` — 04, 05 스크립트가 v0.3.0 CLI 의 프로토타입임을 각주 (향후 `rhwp-py` 로 이관)

## 참조

- v0.2.0 설계: [v0.2.0/ir.md](../v0.2.0/ir.md) §방향 전환 배경
- Phase 2 IR 확장: [phase-2.md](../phase-2.md)
- Typer 공식: <https://typer.tiangolo.com/>
- 업스트림 바이너리 서브커맨드: `external/rhwp/src/main.rs`, `external/rhwp/CLAUDE.md`
