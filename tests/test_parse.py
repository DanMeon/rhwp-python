"""parse() / Document 생성자 / getters / __repr__ 검증."""

from pathlib import Path

import rhwp


class TestParsing:
    def test_parse_hwp5(self, hwp_sample: Path) -> None:
        # ^ sandbox 벤치로 확인된 aift.hwp 기준값
        doc = rhwp.parse(str(hwp_sample))
        assert doc.section_count == 3
        assert doc.paragraph_count == 921
        assert doc.page_count > 0

    def test_parse_hwpx(self, hwpx_sample: Path) -> None:
        doc = rhwp.parse(str(hwpx_sample))
        assert doc.section_count == 1
        assert doc.paragraph_count == 35
        assert doc.page_count > 0

    def test_parse_is_alias_of_constructor(self, hwp_sample: Path) -> None:
        a = rhwp.parse(str(hwp_sample))
        b = rhwp.Document(str(hwp_sample))
        assert a.section_count == b.section_count
        assert a.paragraph_count == b.paragraph_count
        assert a.page_count == b.page_count

    def test_returns_document_instance(self, hwp_sample: Path) -> None:
        doc = rhwp.parse(str(hwp_sample))
        assert isinstance(doc, rhwp.Document)


class TestRepr:
    def test_repr_format(self, parsed_hwp: rhwp.Document) -> None:
        r = repr(parsed_hwp)
        assert r.startswith("Document(")
        assert r.endswith(")")

    def test_repr_contains_counts(self, parsed_hwp: rhwp.Document) -> None:
        r = repr(parsed_hwp)
        assert f"sections={parsed_hwp.section_count}" in r
        assert f"paragraphs={parsed_hwp.paragraph_count}" in r
        assert f"pages={parsed_hwp.page_count}" in r


class TestGetters:
    def test_section_count_type(self, parsed_hwp: rhwp.Document) -> None:
        assert isinstance(parsed_hwp.section_count, int)
        assert parsed_hwp.section_count >= 1

    def test_paragraph_count_type(self, parsed_hwp: rhwp.Document) -> None:
        assert isinstance(parsed_hwp.paragraph_count, int)
        assert parsed_hwp.paragraph_count >= 1

    def test_page_count_type(self, parsed_hwp: rhwp.Document) -> None:
        assert isinstance(parsed_hwp.page_count, int)
        assert parsed_hwp.page_count >= 1
