"""Document.from_bytes 검증 — bytes 기반 생성 (네트워크 fetch, in-memory archive 등).

sync API 이며 thread-safety 문제와 무관. ``rhwp.Document.from_bytes(data, source_uri=...)``
는 ``_Document::from_bytes`` classmethod (PyO3) 위의 Python wrapper.
"""

from pathlib import Path

import pytest
import rhwp


def test_from_bytes_returns_document(hwp_sample: Path) -> None:
    data = hwp_sample.read_bytes()
    doc = rhwp.Document.from_bytes(data)
    assert isinstance(doc, rhwp.Document)
    assert doc.source_uri is None  # 인자 미지정 시 None


def test_from_bytes_with_source_uri(hwp_sample: Path) -> None:
    data = hwp_sample.read_bytes()
    doc = rhwp.Document.from_bytes(data, source_uri="mem://test")
    assert doc.source_uri == "mem://test"


def test_from_bytes_equivalent_to_parse(hwp_sample: Path) -> None:
    data = hwp_sample.read_bytes()
    bytes_doc = rhwp.Document.from_bytes(data, source_uri=str(hwp_sample))
    path_doc = rhwp.parse(str(hwp_sample))
    assert bytes_doc.section_count == path_doc.section_count
    assert bytes_doc.extract_text() == path_doc.extract_text()


def test_from_bytes_hwpx(hwpx_sample: Path) -> None:
    data = hwpx_sample.read_bytes()
    doc = rhwp.Document.from_bytes(data)
    assert isinstance(doc, rhwp.Document)
    assert doc.section_count > 0


def test_from_bytes_invalid_data_raises() -> None:
    with pytest.raises(ValueError):
        rhwp.Document.from_bytes(b"not a valid hwp file")


def test_from_bytes_ir_equivalent_to_parse(hwp_sample: Path) -> None:
    """from_bytes 경로도 parse 와 동일한 IR 을 생성하는지."""
    data = hwp_sample.read_bytes()
    bytes_doc = rhwp.Document.from_bytes(data, source_uri=str(hwp_sample))
    path_doc = rhwp.parse(str(hwp_sample))
    # ^ JSON 문자열 비교 — Pydantic 객체 자체는 서로 다른 인스턴스이지만 값 동일
    assert bytes_doc.to_ir_json() == path_doc.to_ir_json()
