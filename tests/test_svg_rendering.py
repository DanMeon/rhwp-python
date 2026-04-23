"""SVG 렌더링 API 검증."""

from pathlib import Path

import pytest
import rhwp


class TestRenderSvg:
    def test_render_single_page(self, parsed_hwpx: rhwp.Document) -> None:
        # ^ HWPX 소용량 사용 — aift.hwp 74페이지 전체는 느려서 별도 마커 필요시에만
        svg = parsed_hwpx.render_svg(page=0)
        assert isinstance(svg, str)
        assert svg.startswith("<svg")
        assert "</svg>" in svg
        assert len(svg) > 1000

    def test_out_of_range_raises_valueerror(self, parsed_hwpx: rhwp.Document) -> None:
        with pytest.raises(ValueError):
            parsed_hwpx.render_svg(page=parsed_hwpx.page_count + 100)


class TestRenderAllSvg:
    def test_count_matches_page_count(self, parsed_hwpx: rhwp.Document) -> None:
        svgs = parsed_hwpx.render_all_svg()
        assert len(svgs) == parsed_hwpx.page_count

    def test_all_start_with_svg_tag(self, parsed_hwpx: rhwp.Document) -> None:
        svgs = parsed_hwpx.render_all_svg()
        assert all(s.startswith("<svg") for s in svgs)

    def test_returns_list_of_str(self, parsed_hwpx: rhwp.Document) -> None:
        svgs = parsed_hwpx.render_all_svg()
        assert isinstance(svgs, list)
        assert all(isinstance(s, str) for s in svgs)


class TestExportSvg:
    def test_writes_files(self, parsed_hwpx: rhwp.Document, tmp_path: Path) -> None:
        paths = parsed_hwpx.export_svg(str(tmp_path), prefix="test")
        assert len(paths) == parsed_hwpx.page_count
        for path_str in paths:
            p = Path(path_str)
            assert p.exists()
            assert p.stat().st_size > 100
            assert p.suffix == ".svg"

    def test_default_prefix_is_page(self, parsed_hwpx: rhwp.Document, tmp_path: Path) -> None:
        paths = parsed_hwpx.export_svg(str(tmp_path))
        assert len(paths) == parsed_hwpx.page_count
        for p in paths:
            assert "page" in Path(p).stem

    def test_creates_output_dir(self, parsed_hwpx: rhwp.Document, tmp_path: Path) -> None:
        # ^ output_dir 이 없을 때 자동 생성
        target = tmp_path / "new" / "nested" / "dir"
        assert not target.exists()
        paths = parsed_hwpx.export_svg(str(target), prefix="x")
        assert target.is_dir()
        assert all(Path(p).parent == target for p in paths)

    def test_multipage_uses_numbering(self, parsed_hwpx: rhwp.Document, tmp_path: Path) -> None:
        # ^ page_count > 1 이면 `{prefix}_{NNN}.svg` 형태
        if parsed_hwpx.page_count <= 1:
            pytest.skip("sample is single-page")
        paths = parsed_hwpx.export_svg(str(tmp_path), prefix="multi")
        for i, path_str in enumerate(paths, start=1):
            assert Path(path_str).name == f"multi_{i:03d}.svg"
