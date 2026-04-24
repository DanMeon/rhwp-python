# rhwp-python 예제

실제 HWP/HWPX 파일로 rhwp-python 을 사용하는 typer 기반 예제 모음.
각 스크립트는 **사용자 본인의 HWP 파일 경로**를 인자로 받아 바로 돌릴 수 있다.

## 사전 준비

```bash
# 01 ~ 05 예제 전부 한 방에 설치 (typer + langchain-core + text-splitters)
pip install "rhwp-python[examples]"
```

> 통합 레이어만 필요하면 (예제 러너 없이 직접 `HwpLoader` 사용) `pip install "rhwp-python[langchain]"` 만으로 충분하다.

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

### 4. Document IR — `04_document_ir.py`

```bash
python examples/04_document_ir.py path/to/your/file.hwp
python examples/04_document_ir.py path/to/your/file.hwp --limit 20
python examples/04_document_ir.py path/to/your/file.hwp --out ir.json
```

`to_ir()` 로 구조화 IR 을 얻어 블록 타입 분포, layout 셀 개수, 첫 표의 HTML 직렬화를 출력. `--out` 으로 전체 IR 을 JSON 파일로 저장 가능.

옵션:
- `--limit / -n INT` : 미리보기할 블록 최대 개수 (기본 15)
- `--out / -o PATH` : 전체 IR 을 JSON 파일로 덤프

### 5. LangChain `ir-blocks` 모드 — `05_langchain_ir_blocks.py`

```bash
python examples/05_langchain_ir_blocks.py path/to/your/file.hwp
python examples/05_langchain_ir_blocks.py path/to/your/file.hwp --kind-filter table
```

`HwpLoader(mode="ir-blocks")` 가 단락은 text, 표는 **HTML** (HtmlRAG 호환) 로 매핑하는 것을 단락/표 유형별로 미리본다. 표에는 `rows`/`cols`/`caption`/`text` 가 메타로 함께 노출되어 dual-track RAG (임베딩=평문, LLM=HTML) 가 가능.

옵션:
- `--kind-filter / -k {all,paragraph,table}` : 표시 종류 필터 (기본 `all`)
- `--limit / -n INT` : 미리보기할 Document 최대 개수 (기본 10)

## 릴리스 전 실제 HWP 검증

릴리스 직전 **본인의 업무 HWP 파일 3종 (일반 문서 / 장문 / HWPX)** 으로 다섯 스크립트를 순서대로 돌려 출력을 육안 확인한다. 한컴오피스 뷰어로 연 원본과 대조해 섹션/문단/페이지 수치, SVG/PDF 렌더, IR 의 block/table 구조, LangChain Document 매핑이 깨지지 않는지 본다.
