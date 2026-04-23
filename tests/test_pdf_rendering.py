"""PDF 렌더링 API 검증 — @slow (usvg + pdf-writer 병목)."""

from pathlib import Path

import pytest
import rhwp

pytestmark = pytest.mark.slow


class TestRenderPdf:
    def test_returns_bytes(self, parsed_hwpx: rhwp.Document) -> None:
        # ^ 가이드 §12.4: Bound<'py, PyBytes> 바인딩으로 Python bytes 직접 반환
        #   (list[int] 노출 금지)
        pdf = parsed_hwpx.render_pdf()
        assert isinstance(pdf, bytes)

    def test_pdf_signature(self, parsed_hwpx: rhwp.Document) -> None:
        pdf = parsed_hwpx.render_pdf()
        assert pdf.startswith(b"%PDF-")
        assert len(pdf) > 1000


class TestExportPdf:
    def test_writes_file(self, parsed_hwpx: rhwp.Document, tmp_path: Path) -> None:
        output = tmp_path / "out.pdf"
        size = parsed_hwpx.export_pdf(str(output))
        assert output.exists()
        assert output.stat().st_size == size

    def test_pdf_signature_in_file(self, parsed_hwpx: rhwp.Document, tmp_path: Path) -> None:
        output = tmp_path / "sig.pdf"
        parsed_hwpx.export_pdf(str(output))
        with open(output, "rb") as f:
            assert f.read(5) == b"%PDF-"

    def test_returns_size_as_int(self, parsed_hwpx: rhwp.Document, tmp_path: Path) -> None:
        output = tmp_path / "size.pdf"
        size = parsed_hwpx.export_pdf(str(output))
        assert isinstance(size, int)
        assert size > 0
