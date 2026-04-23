"""pytest 공통 fixture — 샘플 경로 및 파싱된 Document 캐시."""

from pathlib import Path

import pytest
import rhwp

# ^ 경로 구조: <REPO_ROOT>/tests/conftest.py
#   parent=tests → parent=<REPO_ROOT>
#   샘플은 rhwp 코어 submodule (external/rhwp) 내부 samples/ 디렉터리에 있음
REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = REPO_ROOT / "external" / "rhwp" / "samples"


@pytest.fixture(scope="session")
def samples_dir() -> Path:
    return SAMPLES


@pytest.fixture(scope="session")
def hwp_sample() -> Path:
    return SAMPLES / "aift.hwp"


@pytest.fixture(scope="session")
def hwpx_sample() -> Path:
    return SAMPLES / "table-vpos-01.hwpx"


@pytest.fixture(scope="session")
def parsed_hwp(hwp_sample: Path) -> rhwp.Document:
    return rhwp.parse(str(hwp_sample))


@pytest.fixture(scope="session")
def parsed_hwpx(hwpx_sample: Path) -> rhwp.Document:
    return rhwp.parse(str(hwpx_sample))
