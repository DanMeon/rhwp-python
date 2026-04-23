# rhwp-python

**한국어** | [**English**](README_EN.md)

[![PyPI](https://img.shields.io/pypi/v/rhwp-python.svg)](https://pypi.org/project/rhwp-python/)
[![Python](https://img.shields.io/pypi/pyversions/rhwp-python.svg)](https://pypi.org/project/rhwp-python/)
[![CI](https://github.com/DanMeon/rhwp-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/DanMeon/rhwp-python/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> ⚠️ **비공식 커뮤니티 패키지입니다.** 본 프로젝트는 [edwardkim/rhwp](https://github.com/edwardkim/rhwp) 의 **공식 배포가 아니며**, rhwp 메인테이너가 직접 PyPI 에 올릴 경우를 대비해 이름을 `rhwp-python` 으로 양보해 둔 상태입니다. rhwp 코어 버그는 [업스트림](https://github.com/edwardkim/rhwp/issues) 에 보고해 주세요.

[rhwp](https://github.com/edwardkim/rhwp) — Rust 기반 HWP/HWPX(한컴오피스 문서) 파서·렌더러 — 의 PyO3 Python 바인딩.

- **PyPI 패키지명**: `rhwp-python`
- **Python import**: `import rhwp`
- **Rust 코어**: [`external/rhwp`](external/) 에 git submodule 로 고정

## 왜 rhwp-python 인가

- **HWP + HWPX 동시 지원** — 대표 대안인 `pyhwp` 는 HWP5 만 지원하고 2016년 이후 유지보수 중단 상태. rhwp 는 두 포맷을 같은 API 로 처리.
- **텍스트 추출 62배 빠름** — HWP5 기준 `pyhwp` 대비 96 ms vs 5,980 ms (sandbox 벤치).
- **LangChain 즉시 연동** — `rhwp.integrations.langchain.HwpLoader` 를 extras 로 제공, RAG 파이프라인에 바로 플러그인 가능.
- **타입 완비** — `py.typed` + `.pyi` 스텁, pyright clean.

## 요구 사항

- Python 3.9+ (abi3-py39 wheel 하나로 3.9 ~ 3.13+ 커버)
- 코어 API 는 **런타임 Python 의존성 없음**
- `rhwp-python[langchain]` extras 는 `langchain-core>=0.2` 하나만 추가 설치

## 설치

```bash
pip install rhwp-python
# 또는
uv add rhwp-python
```

## 사용법

```python
import rhwp

# HWP / HWPX 파싱 — 파일 I/O + 파싱 단계에서 GIL 해제
doc = rhwp.parse("report.hwp")
print(doc.section_count, doc.paragraph_count, doc.page_count)

# 텍스트
full_text: str = doc.extract_text()          # 빈 문단 제외, "\n" 으로 join
paragraphs: list[str] = doc.paragraphs()      # 빈 문단 포함 원본 리스트

# SVG 렌더링 — 단일 페이지 또는 전체
svg_page0: str = doc.render_svg(page=0)
all_svgs: list[str] = doc.render_all_svg()
written: list[str] = doc.export_svg("output/", prefix="page")
# → page_001.svg, page_002.svg, ... (단일 페이지면 page.svg)

# PDF 렌더링 — list[int] 가 아니라 Python `bytes` 반환
pdf: bytes = doc.render_pdf()
byte_size: int = doc.export_pdf("output.pdf")
```

`rhwp.Document(path)` 는 `rhwp.parse(path)` 와 동일하게 동작.

## LangChain 통합

```bash
pip install "rhwp-python[langchain]"
```

```python
from rhwp.integrations.langchain import HwpLoader

# 문서 전체를 단일 Document 로 (기본 — single 모드)
docs = HwpLoader("report.hwp").load()

# 빈 문단 제외, 문단 1개당 Document 1개 (RAG 청킹용 — paragraph 모드)
docs = HwpLoader("report.hwp", mode="paragraph").load()

# lazy_load: Document 를 on-the-fly 로 yield (paragraph 모드에서 O(1) peak memory)
for d in HwpLoader("report.hwp", mode="paragraph").lazy_load():
    index_into_vector_store(d)   # 사용자 파이프라인

# 표준 LangChain 텍스트 스플리터에 바로 연결
from langchain_text_splitters import RecursiveCharacterTextSplitter
chunks = RecursiveCharacterTextSplitter(chunk_size=500).split_documents(docs)
```

모든 Document 메타데이터: `source`, `section_count`, `paragraph_count`,
`page_count`, `rhwp_version`. `paragraph` 모드에서는 `paragraph_index` 추가.

## 성능

Apple M2 (8 코어) release 빌드. Parse = 파일 읽기 + 전체 파싱 + Document 생성.
워크로드: 9 개 파일 (`aift.hwp` 5.5 MB + `table-vpos-01.hwpx` 359 KB + `tac-img-02.hwpx` 3.96 MB, ×3).

| 워커 수 | Parse 시간 | 순차 대비 가속 |
| ------- | ---------: | ----------------: |
| 1       | 268 ms     | 1.00× (기준)      |
| 2       | 141 ms     | 1.91×             |
| 4       | 97 ms      | 2.76×             |
| 8       | 67 ms      | **4.01×**         |

`parse()` 와 PDF 변환 단계는 `py.detach` 로 GIL 을 해제하므로 `ThreadPoolExecutor` 가
코어 수에 비례해 스케일. PDF 렌더링 자체는 `usvg` + `pdf-writer` 내부에서 CPU/allocator
바운드라 2 ~ 3 워커에서 약 1.1× 정도만 향상됨 — 재현은 `benches/bench_gil.py` 참고.

## 알려진 제약 (Phase 1)

- `Document` 객체는 `#[pyclass(unsendable)]` — 단일 스레드 접근만 허용.
  교차 스레드 접근 시 `RuntimeError`. 멀티스레드에선 `benches/bench_gil.py` 패턴 사용 —
  워커 내에서 `parse + consume` 까지 완결한 뒤 원시 타입(`int`, `str`, `bytes`) 만 반환.
- 폰트 임베딩 / 디버그 오버레이 / 페이지 메타데이터 API 없음 (Phase 2+).
- HWP/HWPX **저장(serialization)** 미지원 — 읽기/렌더링 전용.
- 표 / 이미지 / 수식 구조화 접근 없음 — 텍스트 추출만 지원.
- PDF 렌더 경로가 rhwp 코어의 `[DEBUG_TAB_POS]` / `LAYOUT_OVERFLOW` 로그를
  stdout 으로 출력. 필요 시 `grep -v -E "(DEBUG_TAB_POS|LAYOUT_OVERFLOW)"` 로 필터링.

## 개발

이 리포는 rhwp Rust 코어를 `external/rhwp` git submodule 로 소비합니다.

```bash
git clone --recurse-submodules https://github.com/DanMeon/rhwp-python
cd rhwp-python

# dev + testing + linting 툴 일괄 설치
uv sync --no-install-project --group all
uv run maturin develop --release

# 테스트 (core + LangChain, slow PDF 제외)
uv run pytest tests/ -m "not slow"

# PDF 렌더링 테스트
uv run pytest tests/ -m slow

# 타입 체크
uv run pyright python/ tests/

# GIL 해제 벤치마크
uv run python benches/bench_gil.py 2>&1 | grep -v -E "(DEBUG_TAB_POS|LAYOUT_OVERFLOW)"
```

clone 시 `--recurse-submodules` 를 빠뜨렸다면:

```bash
git submodule update --init --recursive
```

테스트 fixture 는 submodule 내부 `external/rhwp/samples/` 에 있으며,
`tests/conftest.py` 가 이 경로를 참조합니다.

## 버전 관리

이 Python 패키지와 `rhwp` Rust 코어는 **독립적으로** 버저닝됩니다.
`rhwp.version()` 은 이 패키지 버전을, `rhwp.rhwp_core_version()` 은
고정된 submodule 에 포함된 Rust 코어의 버전을 반환합니다.

## 라이선스

MIT. 저작권자: Edward Kim (rhwp Rust 코어) + DanMeon (rhwp-python 바인딩).
자세한 내용은 [LICENSE](LICENSE).

## 프로젝트 홈

- 바인딩 소스 / 이슈: https://github.com/DanMeon/rhwp-python
- rhwp Rust 코어: https://github.com/edwardkim/rhwp
