# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — Document IR v1 (Phase 2 — targets v0.2.0)

**Document IR v1** — RAG / LLM 파이프라인이 직접 소비 가능한 구조화 문서 모델. Pydantic V2 기반 공개 타입 + JSON Schema (Draft 2020-12).

- `rhwp.ir.nodes` 모듈 — `HwpDocument` / `ParagraphBlock` / `TableBlock` / `TableCell` / `InlineRun` / `Provenance` / `UnknownBlock` / `Furniture` / `DocumentMetadata` / `Section` (10 노드, 전부 `frozen=True` + `extra="forbid"`).
- Callable `Discriminator` 기반 `Block` 태그드 유니온 — 미지 `kind` 는 `UnknownBlock` 으로 라우팅하여 forward-compat 보장 (v0.3.0 의 새 블록 타입이 v0.2.0 소비자를 깨뜨리지 않음).
- `Document.to_ir() -> HwpDocument` + `Document.to_ir_json(*, indent=None) -> str` — Rust `OnceCell<Py<PyAny>>` lazy 캐시 (unsendable 덕에 lock 불필요).
- `HwpDocument.iter_blocks(*, scope, recurse)` — body/furniture/all scope + TableCell 재귀 DFS 순회.
- Rust 측 HTML/text 직렬화 — attribute 순서 고정 (rowspan→colspan), HtmlRAG 호환.
- JSON Schema export — `rhwp.ir.schema.export_schema()` / `load_schema()` / `SCHEMA_ID` / `SCHEMA_DIALECT` + in-package `hwp_ir_v1.json` + `python -m rhwp.ir.schema` CLI.
- Discriminator 후처리 — `_harden_unknown_variant()` 가 UnknownBlock.kind 에 `not.enum: [known kinds]` 주입하여 oneOf 검증 정확도 보장.
- `HwpLoader` 에 `mode="ir-blocks"` 추가 — Block 을 LangChain `Document` 로 매핑 (표는 HTML content + 구조화 메타, 단락은 text + Provenance).
- `.github/workflows/publish-schema.yml` — GitHub Pages 배포 파이프라인, 불변 경로 정책 (v1 URL 영구) 자동화.
- Provenance 단위는 **Unicode codepoint** — Python `str[i]` 슬라이싱과 직접 호환 (이모지/SMP CJK 혼용에서도 off-by-one 없음).
- 신규 런타임 의존성: `pydantic>=2.5,<3`. 테스트 의존성: `jsonschema>=4`.
- 문서: `docs/roadmap/v0.2.0/ir.md` (사양), `docs/design/v0.2.0/ir-design-research.md` (7개 결정 증거), `docs/implementation/v0.2.0/stages/stage-{1..5}.md`.
- 테스트: **163 passed** — IR schema/roundtrip/tables/iter/export + LangChain ir-blocks + Rust unit tests (`cargo test` 5 passed).

### Changed — Phase 2 계획 전환

- 원안의 CLI 도구 (`rhwp` 바이너리) 는 **폐기**. 업스트림 `edwardkim/rhwp` 의 Rust 바이너리가 같은 이름을 점유하므로 충돌 방지 + Python 고유 가치 (RAG / LangChain 통합) 에 집중. 상세: `docs/roadmap/v0.2.0/ir.md` §방향 전환 배경.
- `python/rhwp/__init__.pyi` 에 `Document.to_ir` / `to_ir_json` 타입 힌트 추가.
- `pyproject.toml [tool.maturin] include` 에 `python/rhwp/ir/schema/*.json` 포함 (wheel + sdist).

### Deferred to v0.3.0+

- `PictureBlock` / `FormulaBlock` / `FootnoteBlock` / `ListItemBlock` / `CaptionBlock` / `TocEntryBlock` / `FieldBlock` — 현재는 미지 `kind` → `UnknownBlock` 폴백.
- Furniture 본문 파싱 (머리글/꼬리말/각주 내용).
- `DocumentMetadata.creation_time` / `modification_time` 을 `datetime` 으로 교체 (현재 `str | None`).
- text/table 정확 interleaving (컨트롤 문자 0x0B 위치 기반).
- LLM strict-mode 완전 호환 — `export_schema(strict=True)` 옵션.
- SchemaStore 카탈로그 등록 / content-addressed alias — GA 후 별도 PR.

## [0.1.1] — 2026-04-23

Patch release: fixes the sdist packaging so the source distribution stays within PyPI's 100 MB file size limit.

### Fixed

- `maturin sdist` now excludes `external/rhwp/samples/` (≈60 MB of test fixture HWP/HWPX files). The v0.1.0 sdist exceeded PyPI's 100 MB limit and was rejected by PyPI; wheels were unaffected and the `rhwp-python 0.1.0` wheels on PyPI remain functional.

### Changed

- `[tool.maturin] exclude` in `pyproject.toml` adds `**/samples/**` for the sdist format.

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

- Local `maturin build --release` wheel (3.0 MB) verified end-to-end in a clean venv: install → import → `rhwp.parse` → `HwpLoader` load. (Note: the v0.1.0 sdist exceeded PyPI's 100 MB limit and did not upload; fixed in [0.1.1](#011--2026-04-23).)
- GitHub Actions workflow (`publish.yml`) builds Linux (x86_64 + aarch64) / macOS (x86_64 + aarch64) / Windows wheels + sdist on release publish, then uploads via PyPI Trusted Publisher (OIDC).

[Unreleased]: https://github.com/DanMeon/rhwp-python/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/DanMeon/rhwp-python/releases/tag/v0.1.1
[0.1.0]: https://github.com/DanMeon/rhwp-python/releases/tag/v0.1.0
