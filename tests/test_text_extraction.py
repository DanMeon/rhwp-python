"""extract_text / paragraphs API 검증."""

import rhwp


class TestExtractText:
    def test_returns_string(self, parsed_hwp: rhwp.Document) -> None:
        assert isinstance(parsed_hwp.extract_text(), str)

    def test_contains_korean(self, parsed_hwp: rhwp.Document) -> None:
        # ^ aift.hwp 는 "사업계획서" 문구 포함 (sandbox 에서 확인)
        text = parsed_hwp.extract_text()
        assert len(text) > 10000
        assert "사업계획서" in text

    def test_hwpx_extract_text(self, parsed_hwpx: rhwp.Document) -> None:
        text = parsed_hwpx.extract_text()
        assert isinstance(text, str)
        assert len(text) > 0


class TestParagraphs:
    def test_returns_list_of_str(self, parsed_hwp: rhwp.Document) -> None:
        paras = parsed_hwp.paragraphs()
        assert isinstance(paras, list)
        assert all(isinstance(p, str) for p in paras)

    def test_length_matches_paragraph_count(self, parsed_hwp: rhwp.Document) -> None:
        # ^ paragraphs() 는 raw 리스트 — 빈 문단 포함
        paras = parsed_hwp.paragraphs()
        assert len(paras) == parsed_hwp.paragraph_count

    def test_hwpx_paragraphs(self, parsed_hwpx: rhwp.Document) -> None:
        paras = parsed_hwpx.paragraphs()
        assert len(paras) == parsed_hwpx.paragraph_count


class TestExtractTextConsistency:
    def test_extract_text_equals_join_nonempty_paragraphs(self, parsed_hwp: rhwp.Document) -> None:
        # ^ extract_text() = 빈 문단 제외 후 "\n" join (Rust 측 filter(!is_empty))
        paras = parsed_hwp.paragraphs()
        expected = "\n".join(p for p in paras if p)
        assert parsed_hwp.extract_text() == expected
