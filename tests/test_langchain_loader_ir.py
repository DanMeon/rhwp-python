"""Stage S5 — HwpLoader(mode="ir-blocks") pytest 스위트.

``test_langchain_loader.py`` 는 CLAUDE.md 규약상 exactly 29 테스트 유지 —
IR 모드 추가 테스트는 본 파일로 분리한다. 둘 모두 ``langchain_core`` 미설치
시 파일 레벨 importorskip 으로 auto-skip.
"""

from pathlib import Path

import pytest

pytest.importorskip("langchain_core")

import rhwp  # noqa: E402
from langchain_core.documents import Document  # noqa: E402
from rhwp.integrations.langchain import HwpLoader  # noqa: E402

pytestmark = pytest.mark.langchain


# * 생성자


def test_ir_blocks_mode_accepted(hwp_sample: Path) -> None:
    loader = HwpLoader(str(hwp_sample), mode="ir-blocks")
    assert loader.mode == "ir-blocks"


# * load / lazy_load


def test_ir_blocks_mode_returns_list_of_documents(hwpx_sample: Path) -> None:
    docs = HwpLoader(str(hwpx_sample), mode="ir-blocks").load()
    assert isinstance(docs, list)
    assert len(docs) > 0
    assert all(isinstance(d, Document) for d in docs)


def test_ir_blocks_mode_lazy_load_yields_documents(hwpx_sample: Path) -> None:
    it = HwpLoader(str(hwpx_sample), mode="ir-blocks").lazy_load()
    first = next(it)
    assert isinstance(first, Document)


# * metadata 구조 — kind / prov


def test_ir_blocks_metadata_has_base_fields(hwpx_sample: Path) -> None:
    docs = HwpLoader(str(hwpx_sample), mode="ir-blocks").load()
    for d in docs:
        md = d.metadata
        assert md["source"] == str(hwpx_sample)
        assert "section_count" in md
        assert "paragraph_count" in md
        assert "page_count" in md
        assert "rhwp_version" in md
        assert "kind" in md
        assert "section_idx" in md
        assert "para_idx" in md


def test_ir_blocks_includes_both_paragraph_and_table(hwpx_sample: Path) -> None:
    """HWPX 샘플은 표를 포함 — ir-blocks 로 로드 시 kind=paragraph + kind=table 혼합."""
    docs = HwpLoader(str(hwpx_sample), mode="ir-blocks").load()
    kinds = {d.metadata["kind"] for d in docs}
    assert "paragraph" in kinds
    assert "table" in kinds


def test_ir_blocks_paragraph_content_is_text(hwpx_sample: Path) -> None:
    docs = HwpLoader(str(hwpx_sample), mode="ir-blocks").load()
    para_docs = [d for d in docs if d.metadata["kind"] == "paragraph"]
    assert para_docs  # ^ 최소 하나는 존재
    for d in para_docs:
        # ^ paragraph page_content 는 단순 텍스트 (HTML 태그 없음)
        assert "<table>" not in d.page_content


def test_ir_blocks_table_content_is_html(hwpx_sample: Path) -> None:
    docs = HwpLoader(str(hwpx_sample), mode="ir-blocks").load()
    table_docs = [d for d in docs if d.metadata["kind"] == "table"]
    assert table_docs
    for d in table_docs:
        # ^ 표 page_content 는 HTML — HtmlRAG 호환 (ir.md §테이블 표현)
        assert d.page_content.startswith("<table>")
        assert d.page_content.endswith("</table>")
        # ^ 메타데이터에 구조화 정보 + 평문 병기
        assert d.metadata["rows"] > 0
        assert d.metadata["cols"] > 0
        assert "text" in d.metadata


# * 빈 블록 필터링


def test_ir_blocks_skips_empty_paragraphs(hwpx_sample: Path) -> None:
    """page_content 가 빈 문단은 RAG 노이즈 — 스킵."""
    docs = HwpLoader(str(hwpx_sample), mode="ir-blocks").load()
    for d in docs:
        assert d.page_content.strip(), f"empty doc: {d}"


# * HWP5 샘플도 같은 계약


def test_ir_blocks_mode_works_on_hwp5_sample(hwp_sample: Path) -> None:
    docs = HwpLoader(str(hwp_sample), mode="ir-blocks").load()
    assert len(docs) > 0
    kinds = {d.metadata["kind"] for d in docs}
    # ^ HWP5 샘플은 paragraph 는 반드시 있음, table 은 있을 수도 없을 수도
    assert "paragraph" in kinds


# * Provenance 일치


def test_ir_blocks_provenance_matches_ir(hwpx_sample: Path) -> None:
    """loader 가 반환한 metadata 의 (section_idx, para_idx) 가 to_ir() 블록과 일치."""
    parsed = rhwp.parse(str(hwpx_sample))
    ir = parsed.to_ir()
    docs = HwpLoader(str(hwpx_sample), mode="ir-blocks").load()

    # ^ iter_blocks 의 순서와 loader 의 순서가 동일해야 함
    ir_blocks = [b for b in ir.iter_blocks(scope="body", recurse=True)]
    loader_provs = [(d.metadata["section_idx"], d.metadata["para_idx"]) for d in docs]
    ir_provs = [(b.prov.section_idx, b.prov.para_idx) for b in ir_blocks]

    # ^ 빈 블록이 loader 에서 스킵되므로 길이는 다를 수 있음 — loader prov 는 ir prov 의 부분집합
    loader_set = set(loader_provs)
    ir_set = set(ir_provs)
    assert loader_set <= ir_set


# * 기본 mode 목록 검증 — invalid mode 는 여전히 거부


def test_invalid_mode_still_rejects_after_ir_addition(hwp_sample: Path) -> None:
    with pytest.raises(ValueError, match="mode"):
        HwpLoader(str(hwp_sample), mode="page")  # type: ignore[arg-type]
