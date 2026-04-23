# rhwp-python 예제

실제 HWP/HWPX 파일로 rhwp-python 을 사용하는 typer 기반 예제 모음.
각 스크립트는 **사용자 본인의 HWP 파일 경로**를 인자로 받아 바로 돌릴 수 있다.

## 사전 준비

```bash
# 예제 실행용 (typer 포함)
pip install "rhwp-python[examples]"

# LangChain 예제까지 돌리려면
pip install "rhwp-python[langchain,examples]" langchain-text-splitters
```

## 스크립트

모든 스크립트는 `--help` 로 옵션을 확인할 수 있다.

### 1. 파싱 + 텍스트 추출 — `01_parse_basic.py`

```bash
python examples/01_parse_basic.py path/to/your/file.hwp
python examples/01_parse_basic.py path/to/your/file.hwp --preview 200
```

옵션:
- `--preview / -p INT` : 본문 프리뷰 문자 수 (기본 500)

### 2. SVG + PDF 렌더링 — `02_render_svg_pdf.py`

```bash
python examples/02_render_svg_pdf.py path/to/your/file.hwp
python examples/02_render_svg_pdf.py path/to/your/file.hwp -o ./out --no-pdf
```

옵션:
- `--output-dir / -o PATH` : 출력 디렉토리 (기본 `./render_output`)
- `--no-svg` / `--no-pdf` : 특정 포맷 건너뛰기
- `--prefix TEXT` : SVG 파일명 접두사 (기본 `page`)

### 3. LangChain RAG 파이프라인 — `03_langchain_rag.py`

```bash
python examples/03_langchain_rag.py path/to/your/file.hwp
python examples/03_langchain_rag.py path/to/your/file.hwp --chunk-size 1000 --chunk-overlap 100
```

옵션:
- `--chunk-size INT` : 청크 최대 문자 수 (기본 500)
- `--chunk-overlap INT` : 청크 간 오버랩 (기본 50)

## 릴리스 전 실제 HWP 검증

릴리스 직전 **본인의 업무 HWP 파일 3종 (일반 문서 / 장문 / HWPX)** 으로 세 스크립트를 순서대로 돌려 출력을 육안 확인한다. 한컴오피스 뷰어로 연 원본과 대조해 섹션/문단/페이지 수치가 맞는지, SVG/PDF 가 깨지지 않는지 본다.

## 향후 CLI 도입 계획

예제의 `typer.run(main)` 패턴은 추후 v0.2 에서 `python/rhwp/cli.py` 모듈로 승격 예정.
그 시점엔 `pip install rhwp-python` 만으로 `rhwp parse file.hwp`, `rhwp render file.hwp` 같은
명령을 바로 쓸 수 있도록 `[project.scripts]` 에 엔트리포인트를 노출할 계획.
