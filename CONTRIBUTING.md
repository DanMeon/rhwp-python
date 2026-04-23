# Contributing to rhwp-python

Thanks for your interest in contributing! AI-assisted contributions (issue creation, coding, reviews) are welcome.

This repository consumes the rhwp Rust core via a git submodule at `external/rhwp`.
Clone with `--recurse-submodules`, or run `git submodule update --init --recursive` after cloning.

## Before You Submit

- `uv sync --no-install-project --group all` to install dev + testing + linting deps
- `uv run maturin develop --release` to build the extension
- `uv run pytest tests/ -m "not slow" -v` must pass (run `pytest -m slow` for PDF tests)
- `uv run ruff check python/ tests/ benches/` and `uv run pyright python/ tests/` must pass
- Pre-commit hooks run these automatically

## Code Style

- Python 3.9+, `T | None` (not `Optional[T]`), PEP 561 typed
- Rust 1.83+ (PyO3 0.28 MSRV). No new `unsafe` in the bindings layer

## Pull Requests

1. Fork → feature branch → make changes with tests → PR against `main`
2. Keep PRs focused — one feature or fix per PR
3. For changes touching rhwp core, open an issue on [edwardkim/rhwp](https://github.com/edwardkim/rhwp) first; this repo only adds bindings
