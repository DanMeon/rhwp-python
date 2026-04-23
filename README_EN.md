# rhwp-python

[**한국어**](README.md) | **English**

[![PyPI](https://img.shields.io/pypi/v/rhwp-python.svg)](https://pypi.org/project/rhwp-python/)
[![Python](https://img.shields.io/pypi/pyversions/rhwp-python.svg)](https://pypi.org/project/rhwp-python/)
[![CI](https://github.com/DanMeon/rhwp-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/DanMeon/rhwp-python/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> ⚠️ **Unofficial community package.** This project is **not an official distribution** of [edwardkim/rhwp](https://github.com/edwardkim/rhwp). The name `rhwp-python` is used so that the upstream maintainer can take the `rhwp` name on PyPI if they choose to publish officially. Please file bugs in the rhwp core upstream at [edwardkim/rhwp/issues](https://github.com/edwardkim/rhwp/issues).

PyO3 Python bindings for [rhwp](https://github.com/edwardkim/rhwp), a Rust-based parser and renderer for HWP/HWPX documents (Korean word processor format, 한컴오피스).

- **PyPI package**: `rhwp-python`
- **Python import**: `import rhwp`
- **Rust core**: pinned via git submodule at [`external/rhwp`](external/)

## Why rhwp-python

- **HWP + HWPX** — The major Python alternative `pyhwp` supports only HWP5 and has been
  unmaintained since 2016. rhwp handles both formats with the same API.
- **62× faster** than `pyhwp` on HWP5 text extraction (96 ms vs 5,980 ms, sandbox benchmark).
- **LangChain-ready** — `rhwp.integrations.langchain.HwpLoader` ships as optional extras,
  plugging directly into RAG pipelines.
- **Typed** — `py.typed` + `.pyi` stubs, pyright clean.

## Requirements

- Python 3.9+ (abi3-py39 wheel covers 3.9 through 3.13+)
- No runtime Python dependencies for the core API
- `rhwp-python[langchain]` extras pull in `langchain-core>=0.2` only

## Installation

```bash
pip install rhwp-python
# or
uv add rhwp-python
```

## Usage

```python
import rhwp

# Parse HWP / HWPX — file loading + parsing released from GIL
doc = rhwp.parse("report.hwp")
print(doc.section_count, doc.paragraph_count, doc.page_count)

# Text
full_text: str = doc.extract_text()          # non-empty paragraphs joined by "\n"
paragraphs: list[str] = doc.paragraphs()      # raw list, includes empty paragraphs

# SVG rendering — one page, or all pages
svg_page0: str = doc.render_svg(page=0)
all_svgs: list[str] = doc.render_all_svg()
written: list[str] = doc.export_svg("output/", prefix="page")
# → writes page_001.svg, page_002.svg, ... (single-page: page.svg)

# PDF rendering — returns Python `bytes`, not list[int]
pdf: bytes = doc.render_pdf()
byte_size: int = doc.export_pdf("output.pdf")
```

`rhwp.Document(path)` works identically to `rhwp.parse(path)`.

## LangChain integration

```bash
pip install "rhwp-python[langchain]"
```

```python
from rhwp.integrations.langchain import HwpLoader

# Whole document as a single Document (default — single mode)
docs = HwpLoader("report.hwp").load()

# One Document per non-empty paragraph (for RAG chunking — paragraph mode)
docs = HwpLoader("report.hwp", mode="paragraph").load()

# lazy_load: Document objects yielded on-the-fly (O(1) peak memory in paragraph mode)
for d in HwpLoader("report.hwp", mode="paragraph").lazy_load():
    index_into_vector_store(d)   # your pipeline

# Plugs into the standard LangChain text splitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
chunks = RecursiveCharacterTextSplitter(chunk_size=500).split_documents(docs)
```

Metadata preserved on every Document: `source`, `section_count`, `paragraph_count`,
`page_count`, `rhwp_version`, plus `paragraph_index` in `paragraph` mode.

## Performance

Release build on Apple M2 (8 cores). Parse = file read + full parse + Document creation.
Workload: 9 files (`aift.hwp` 5.5 MB + `table-vpos-01.hwpx` 359 KB + `tac-img-02.hwpx` 3.96 MB, ×3).

| Workers | Parse time | Speedup vs serial |
| ------- | ---------: | ----------------: |
| 1       | 268 ms     | 1.00× (baseline)  |
| 2       | 141 ms     | 1.91×             |
| 4       | 97 ms      | 2.76×             |
| 8       | 67 ms      | **4.01×**         |

`parse()` and the PDF conversion step release the GIL via `py.detach`, so
`ThreadPoolExecutor` scales with cores for batch workloads. PDF rendering itself is
CPU/allocator-bound inside `usvg` + `pdf-writer`, so parallelization yields only
약 1.1× on 2–3 workers — see `benches/bench_gil.py` for reproducible measurement.

## Known limitations (Phase 1)

- `Document` objects are `#[pyclass(unsendable)]` — single-threaded access only.
  Cross-thread access raises `RuntimeError`. Use the pattern in `benches/bench_gil.py`:
  run `parse + consume` inside the worker, return primitives (`int`, `str`, `bytes`).
- No font embedding / debug overlay / page metadata APIs (Phase 2+).
- No HWP/HWPX **serialization** (save) — read/render only.
- No structured access to tables, images, formulas — text extraction only.
- PDF render path outputs Rust-side `[DEBUG_TAB_POS]` / `LAYOUT_OVERFLOW` log lines
  from the rhwp core. Filter with `grep -v -E "(DEBUG_TAB_POS|LAYOUT_OVERFLOW)"` for now.

## Development

This project consumes the rhwp Rust core as a git submodule at `external/rhwp`.

```bash
git clone --recurse-submodules https://github.com/DanMeon/rhwp-python
cd rhwp-python

# install dev+testing+linting tools
uv sync --no-install-project --group all
uv run maturin develop --release

# test (core + LangChain, excluding slow PDF tests)
uv run pytest tests/ -m "not slow"

# PDF rendering tests
uv run pytest tests/ -m slow

# type check
uv run pyright python/ tests/

# benchmark GIL release
uv run python benches/bench_gil.py 2>&1 | grep -v -E "(DEBUG_TAB_POS|LAYOUT_OVERFLOW)"
```

If you forgot `--recurse-submodules` at clone time:

```bash
git submodule update --init --recursive
```

Test fixtures live in the submodule at `external/rhwp/samples/`; `tests/conftest.py`
reads from that path.

## Versioning

This Python package and the `rhwp` Rust core are versioned **independently**.
`rhwp.version()` returns this package's version; `rhwp.rhwp_core_version()`
returns the Rust core version bundled in the pinned submodule.

## License

MIT. Copyright holders: Edward Kim (rhwp Rust core) and DanMeon (rhwp-python bindings).
See [LICENSE](LICENSE).

## Project home

- Bindings source + issues: https://github.com/DanMeon/rhwp-python
- rhwp Rust core: https://github.com/edwardkim/rhwp
