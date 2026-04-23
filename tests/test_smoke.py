"""Stage 1 smoke tests — version/rhwp_core_version 동작 검증."""

import re

import rhwp

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+].+)?$")


def test_version_returns_string() -> None:
    assert isinstance(rhwp.version(), str)


def test_version_matches_semver() -> None:
    v = rhwp.version()
    assert SEMVER_PATTERN.match(v), f"rhwp.version() = {v!r} — expected semver"


def test_version_is_package_version() -> None:
    # ^ Cargo.toml 의 version="0.1.0" 과 일치
    assert rhwp.version() == "0.1.0"


def test_rhwp_core_version_returns_string() -> None:
    assert isinstance(rhwp.rhwp_core_version(), str)


def test_rhwp_core_version_matches_semver() -> None:
    v = rhwp.rhwp_core_version()
    assert SEMVER_PATTERN.match(v), f"rhwp.rhwp_core_version() = {v!r} — expected semver"


def test_all_exports_available() -> None:
    assert "version" in rhwp.__all__
    assert "rhwp_core_version" in rhwp.__all__


def test_native_module_path() -> None:
    # ^ module-name = "rhwp._rhwp" (가이드 §2.4) 규약 준수 확인
    #   importlib 로 우회: _rhwp 는 내부 네이티브 모듈 — Stage 1 범위에서 별도 스텁 미작성
    import importlib

    native = importlib.import_module("rhwp._rhwp")
    assert native.__name__ == "rhwp._rhwp"
    assert "version" in dir(native)
    assert "rhwp_core_version" in dir(native)


def test_pyi_and_py_all_match() -> None:
    # ^ .py 와 .pyi 의 __all__ 동기화 검증 — Stage 추가 시 누락 방지
    import ast
    from pathlib import Path

    assert rhwp.__file__ is not None
    pyi_path = Path(rhwp.__file__).with_suffix(".pyi")
    assert pyi_path.exists(), f"{pyi_path} not found"

    tree = ast.parse(pyi_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            pyi_all = set(ast.literal_eval(node.value))
            assert pyi_all == set(rhwp.__all__), (
                f".pyi __all__={pyi_all} vs .py __all__={set(rhwp.__all__)}"
            )
            return
    raise AssertionError("__all__ not found in .pyi")
