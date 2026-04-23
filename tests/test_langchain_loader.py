"""HwpLoader (rhwp[langchain]) pytest 스위트.

``langchain-core`` 미설치 환경에서는 자동 skip (pytest.importorskip).
"""

from pathlib import Path

import pytest

# ^ extras 미설치 환경에서 파일 전체 skip
pytest.importorskip("langchain_core")
pytest.importorskip("langchain_text_splitters")

import rhwp  # noqa: E402
from langchain_core.documents import Document  # noqa: E402
from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402
from rhwp.integrations.langchain import HwpLoader  # noqa: E402

pytestmark = pytest.mark.langchain


# * 생성자
class TestConstruction:
    def test_default_mode_is_single(self, hwp_sample: Path) -> None:
        loader = HwpLoader(str(hwp_sample))
        assert loader.mode == "single"

    def test_explicit_single_mode(self, hwp_sample: Path) -> None:
        loader = HwpLoader(str(hwp_sample), mode="single")
        assert loader.mode == "single"

    def test_explicit_paragraph_mode(self, hwp_sample: Path) -> None:
        loader = HwpLoader(str(hwp_sample), mode="paragraph")
        assert loader.mode == "paragraph"

    def test_invalid_mode_raises(self, hwp_sample: Path) -> None:
        with pytest.raises(ValueError, match="mode"):
            HwpLoader(str(hwp_sample), mode="page")  # type: ignore[arg-type]

    def test_invalid_mode_empty_string(self, hwp_sample: Path) -> None:
        with pytest.raises(ValueError):
            HwpLoader(str(hwp_sample), mode="")  # type: ignore[arg-type]


# * single 모드
class TestSingleMode:
    def test_returns_list_with_one_document(self, hwp_sample: Path) -> None:
        docs = HwpLoader(str(hwp_sample)).load()
        assert isinstance(docs, list)
        assert len(docs) == 1
        assert isinstance(docs[0], Document)

    def test_page_content_matches_extract_text(self, hwp_sample: Path) -> None:
        docs = HwpLoader(str(hwp_sample)).load()
        reference = rhwp.parse(str(hwp_sample)).extract_text()
        assert docs[0].page_content == reference

    def test_metadata_has_required_keys(self, hwp_sample: Path) -> None:
        docs = HwpLoader(str(hwp_sample)).load()
        md = docs[0].metadata
        assert set(md.keys()) >= {
            "source",
            "section_count",
            "paragraph_count",
            "page_count",
            "rhwp_version",
        }

    def test_metadata_source_matches_input(self, hwp_sample: Path) -> None:
        path = str(hwp_sample)
        docs = HwpLoader(path).load()
        assert docs[0].metadata["source"] == path

    def test_metadata_counts_match_rhwp(self, hwp_sample: Path) -> None:
        docs = HwpLoader(str(hwp_sample)).load()
        ref = rhwp.parse(str(hwp_sample))
        md = docs[0].metadata
        assert md["section_count"] == ref.section_count
        assert md["paragraph_count"] == ref.paragraph_count
        assert md["page_count"] == ref.page_count

    def test_metadata_no_paragraph_index_in_single_mode(self, hwp_sample: Path) -> None:
        docs = HwpLoader(str(hwp_sample), mode="single").load()
        assert "paragraph_index" not in docs[0].metadata


# * paragraph 모드
class TestParagraphMode:
    def test_returns_list_of_documents(self, hwp_sample: Path) -> None:
        docs = HwpLoader(str(hwp_sample), mode="paragraph").load()
        assert isinstance(docs, list)
        assert all(isinstance(d, Document) for d in docs)

    def test_count_matches_non_empty_paragraphs(self, hwp_sample: Path) -> None:
        docs = HwpLoader(str(hwp_sample), mode="paragraph").load()
        ref_paragraphs = rhwp.parse(str(hwp_sample)).paragraphs()
        non_empty = [p for p in ref_paragraphs if p.strip()]
        assert len(docs) == len(non_empty)

    def test_each_doc_has_paragraph_index(self, hwp_sample: Path) -> None:
        docs = HwpLoader(str(hwp_sample), mode="paragraph").load()
        for d in docs:
            assert "paragraph_index" in d.metadata
            assert isinstance(d.metadata["paragraph_index"], int)

    def test_paragraph_indices_are_from_original_list(self, hwp_sample: Path) -> None:
        docs = HwpLoader(str(hwp_sample), mode="paragraph").load()
        ref_paragraphs = rhwp.parse(str(hwp_sample)).paragraphs()
        for d in docs:
            idx = d.metadata["paragraph_index"]
            assert ref_paragraphs[idx] == d.page_content

    def test_paragraph_indices_are_ascending(self, hwp_sample: Path) -> None:
        docs = HwpLoader(str(hwp_sample), mode="paragraph").load()
        indices = [d.metadata["paragraph_index"] for d in docs]
        assert indices == sorted(indices)

    def test_no_empty_paragraphs(self, hwp_sample: Path) -> None:
        docs = HwpLoader(str(hwp_sample), mode="paragraph").load()
        for d in docs:
            assert d.page_content.strip()

    def test_base_metadata_shared_across_docs(self, hwp_sample: Path) -> None:
        docs = HwpLoader(str(hwp_sample), mode="paragraph").load()
        first_source = docs[0].metadata["source"]
        first_section_count = docs[0].metadata["section_count"]
        for d in docs:
            assert d.metadata["source"] == first_source
            assert d.metadata["section_count"] == first_section_count


# * HWPX 포맷
class TestHwpxFormat:
    def test_single_mode_works(self, hwpx_sample: Path) -> None:
        docs = HwpLoader(str(hwpx_sample)).load()
        assert len(docs) == 1
        assert len(docs[0].page_content) > 100

    def test_paragraph_mode_works(self, hwpx_sample: Path) -> None:
        docs = HwpLoader(str(hwpx_sample), mode="paragraph").load()
        assert len(docs) > 0
        assert all(d.page_content.strip() for d in docs)


# * lazy_load
class TestLazyLoad:
    def test_yields_same_count_as_load(self, hwp_sample: Path) -> None:
        loader = HwpLoader(str(hwp_sample), mode="paragraph")
        eager = loader.load()
        lazy = list(loader.lazy_load())
        assert len(eager) == len(lazy)

    def test_yields_same_content(self, hwp_sample: Path) -> None:
        loader = HwpLoader(str(hwp_sample), mode="paragraph")
        eager_contents = [d.page_content for d in loader.load()]
        lazy_contents = [d.page_content for d in loader.lazy_load()]
        assert eager_contents == lazy_contents

    def test_returns_iterator(self, hwp_sample: Path) -> None:
        loader = HwpLoader(str(hwp_sample))
        result = loader.lazy_load()
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__")


# * 에러 전파
class TestErrors:
    def test_file_not_found(self) -> None:
        loader = HwpLoader("/nonexistent/path.hwp")
        with pytest.raises(FileNotFoundError):
            loader.load()

    def test_invalid_format(self, tmp_path: Path) -> None:
        garbage = tmp_path / "garbage.hwp"
        garbage.write_bytes(b"NOT A REAL HWP FILE" * 100)
        loader = HwpLoader(str(garbage))
        with pytest.raises(ValueError):
            loader.load()


# * 텍스트 스플리터와의 통합
class TestTextSplitterIntegration:
    @pytest.fixture(scope="class")
    def splitter(self) -> RecursiveCharacterTextSplitter:
        return RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def test_split_produces_chunks(
        self, hwp_sample: Path, splitter: RecursiveCharacterTextSplitter
    ) -> None:
        docs = HwpLoader(str(hwp_sample)).load()
        chunks = splitter.split_documents(docs)
        assert len(chunks) > 1

    def test_chunk_size_respected(
        self, hwp_sample: Path, splitter: RecursiveCharacterTextSplitter
    ) -> None:
        docs = HwpLoader(str(hwp_sample)).load()
        chunks = splitter.split_documents(docs)
        oversized = [c for c in chunks if len(c.page_content) > 500 + 50]
        assert not oversized, f"chunks exceed chunk_size+overlap: {len(oversized)}"

    def test_metadata_propagates_to_chunks(
        self, hwp_sample: Path, splitter: RecursiveCharacterTextSplitter
    ) -> None:
        docs = HwpLoader(str(hwp_sample)).load()
        chunks = splitter.split_documents(docs)
        original_source = docs[0].metadata["source"]
        for chunk in chunks:
            assert chunk.metadata["source"] == original_source
            assert "section_count" in chunk.metadata
            assert "rhwp_version" in chunk.metadata

    def test_paragraph_mode_chunks_preserve_paragraph_index(
        self, hwp_sample: Path, splitter: RecursiveCharacterTextSplitter
    ) -> None:
        docs = HwpLoader(str(hwp_sample), mode="paragraph").load()
        chunks = splitter.split_documents(docs)
        for chunk in chunks:
            assert "paragraph_index" in chunk.metadata
