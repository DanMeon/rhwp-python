# 0.2.0 — CLI 도입

`pip install rhwp-python` 만으로 터미널에서 바로 쓸 수 있는 `rhwp` 커맨드 제공. Phase 1 의 examples 스크립트를 `rhwp.cli` 모듈로 승격.

## 목표

- `rhwp parse file.hwp` — 파싱 + 메타데이터 + 텍스트 프리뷰 (examples/01 승격)
- `rhwp render file.hwp -o out/` — SVG + PDF 렌더링 (examples/02 승격)
- `rhwp chunks file.hwp` — LangChain 청킹 (examples/03 승격, `[langchain]` extras 필요 시 안내)
- `rhwp version` — 패키지 + rhwp 코어 버전 출력

## 설계

### 엔트리포인트

```toml
# pyproject.toml
[project.scripts]
rhwp = "rhwp.cli:app"

[project.optional-dependencies]
# examples extras 폐지 — core 의존성으로 typer 승격 (CLI가 core 기능이 됨)
# 또는 cli extras 로 격리 (사용자 선택)
```

옵션 A (권장): `typer` 를 core 의존성으로. 설치 즉시 CLI 사용 가능.
옵션 B: `rhwp-python[cli]` extras 유지. Python 라이브러리로만 쓰는 사용자 부담 제거.

트레이드오프:
- A — 사용성 우선. typer 는 가벼운 의존성 (click 포함 약 300KB)
- B — 의존성 최소화 우선. 그러나 `[cli]` 를 거의 모든 사용자가 결국 설치

0.2.0 에서는 **A (core 포함)** 로 시작 권장. 0.3+ 에서 피드백 기반으로 옵션 B 전환 가능.

### 모듈 구조

```
python/rhwp/
├── __init__.py          # 기존 (Document, parse, version, ...)
├── cli.py               # 신규 — typer.Typer() app + 서브커맨드
└── integrations/
    └── langchain.py     # 기존
```

`cli.py` 는 기존 `examples/*.py` 의 `main` 함수를 사실상 그대로 각 서브커맨드로 옮김. typer.run 대신 `app.command("parse")` 데코레이터.

### 서브커맨드 명세

| 커맨드 | 핵심 옵션 | 의존성 |
|---|---|---|
| `rhwp parse <path>` | `--preview INT`, `--json` | core |
| `rhwp render <path>` | `--output-dir PATH`, `--no-svg`, `--no-pdf` | core |
| `rhwp chunks <path>` | `--chunk-size INT`, `--chunk-overlap INT`, `--mode [single\|paragraph]` | `[langchain]` extras — 미설치 시 안내 exit |
| `rhwp version` | (없음) | core |

`--json` 은 파싱 결과 메타데이터만 JSON 으로 출력 — shell 파이프 가능성 고려.

## 이관 계획

1. `python/rhwp/cli.py` 작성 — examples 3개 내용 병합
2. `pyproject.toml` 에 `[project.scripts]` + `typer` 의존성 추가, `examples` extras 제거 (또는 유지 후 deprecate)
3. `examples/*.py` 는 두 방향:
   - 보존 (사용자 학습용, `python examples/01_*.py` 로도 여전히 실행 가능)
   - 또는 제거 (CLI 가 대체하므로)
4. README 에 CLI 사용법 섹션 추가
5. 새 pytest 케이스 `tests/test_cli.py` — typer `CliRunner` 로 각 서브커맨드 스모크

## 비목표

- 대화형 프롬프트 (typer `prompt=True`) 없음 — 모든 입력은 인자/플래그
- shell completion 스크립트 자동 설치 — typer 기본 제공 `--install-completion` 로 충분
- config 파일 지원 — 단일 문서 작업이라 불필요
