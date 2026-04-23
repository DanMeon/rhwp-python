# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-04-22

Initial PyO3 Python bindings for the rhwp Rust HWP/HWPX parser and renderer.
Phase 1 milestone (upstream issue [edwardkim/rhwp#227](https://github.com/edwardkim/rhwp/issues/227)).

Distributed as `rhwp-python` on PyPI; `import rhwp` for usage.
The `rhwp` Rust core is consumed via git submodule pinned to upstream commit `1636213` (edwardkim/rhwp `main` as of 2026-04-22).

### Added

- Core bindings:
  - `rhwp.version()` — this Python package version.
  - `rhwp.rhwp_core_version()` — underlying Rust core version.
  - `rhwp.parse(path)` → `Document`.
  - `rhwp.Document(path)` — direct constructor, equivalent to `parse()`.
  - Attributes: `section_count`, `paragraph_count`, `page_count`.
  - Methods: `extract_text()`, `paragraphs()`, `render_svg(page)`,
    `render_all_svg()`, `export_svg(dir, prefix=None)`,
    `render_pdf() → bytes`, `export_pdf(path) → int`, `__repr__()`.
- GIL release (`py.detach`) on `parse()`, `render_pdf()`, and `export_pdf()` PDF-conversion step — parallel parse throughput up to **4.01×** on 8 cores (Apple M2).
- Crossplatform `abi3-py39` wheels: Linux x86_64 + aarch64 (manylinux auto), macOS x86_64 + aarch64, Windows.
- Optional extras `rhwp-python[langchain]`:
  - `rhwp.integrations.langchain.HwpLoader(BaseLoader)` with `single` / `paragraph` modes.
  - `lazy_load()` yields `Document` objects on-the-fly for O(1) peak memory in `paragraph` mode.
  - Metadata: `source`, `section_count`, `paragraph_count`, `page_count`, `rhwp_version`, plus `paragraph_index` in paragraph mode.
- PEP 561 typed API (`py.typed` + `.pyi` stubs), pyright clean on valid usage, four intentional-error samples verified.
- pytest suite: 48 core + 29 LangChain = **77 tests**.
- Error mapping preserves Python exception hierarchy: `FileNotFoundError` (NotFound), `PermissionError` (PermissionDenied), `OSError` (other I/O), `ValueError` (invalid format).

### Security

- No known CVEs.
- Built with Rust 1.83+ (PyO3 0.28 MSRV). Bindings layer adds no `unsafe` code.

### Known limitations

- `Document` is `#[pyclass(unsendable)]` — cross-thread use raises `RuntimeError`. Run `parse + consume` inside worker threads.
- No font embedding / debug overlay / page metadata APIs (Phase 2+).
- No HWP/HWPX serialization (save) — read/render only.
- No structured access to tables / images / formulas — text extraction only.

### Distribution

- Local `maturin build --release` wheel (3.0 MB) and `maturin sdist` (1.3 MB, submodule-based vendoring) both verified end-to-end in a clean venv: install → import → `rhwp.parse` → `HwpLoader` load.
- GitHub Actions workflow (`publish.yml`) builds Linux (x86_64 + aarch64) / macOS (x86_64 + aarch64) / Windows wheels + sdist on release publish, then uploads via PyPI Trusted Publisher (OIDC).

[Unreleased]: https://github.com/DanMeon/rhwp-python/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/DanMeon/rhwp-python/releases/tag/v0.1.0
