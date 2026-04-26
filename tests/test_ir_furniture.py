"""tests/test_ir_furniture.py — Stage S1 furniture (page_headers / page_footers) 채움.

ir-expansion.md §S1 + §8 Furniture 채움 + §iter_blocks 순서 계약 검증:

- mapper 가 ``Control::Header`` / ``Control::Footer`` 의 paragraphs 를
  furniture.page_headers / page_footers 로 평탄화
- ``iter_blocks(scope="furniture")`` 순서: page_headers → page_footers → footnotes
- v0.3.0 S1 시점 footnotes 는 빈 리스트 (S2 에서 채움)
- 실제 샘플 (aift.hwp) 에 머리글/꼬리말이 있으면 ParagraphBlock 으로 노출
"""

import rhwp
from pydantic import ValidationError
from rhwp.ir._mapper import build_hwp_document
from rhwp.ir._raw_types import RawDocument, RawParagraph
from rhwp.ir.nodes import (
    Furniture,
    HwpDocument,
    ParagraphBlock,
    Provenance,
    TableBlock,
    TableCell,
)

# * 모델 단독 — Furniture frozen + extra=forbid


def test_furniture_default_lists_are_empty():
    f = Furniture()
    assert f.page_headers == []
    assert f.page_footers == []
    assert f.footnotes == []


def test_furniture_extra_forbidden():
    """ir-expansion.md §8 호환성 메모: extra="forbid" 유지로 v0.2.0 ↔ v0.3.0 schema 차이 강제."""
    import pytest

    with pytest.raises(ValidationError):
        Furniture.model_validate({"page_headers": [], "endnotes": []})  # ^ S2 에서 추가될 키


def test_furniture_frozen_blocks_mutation():
    import pytest

    f = Furniture()
    with pytest.raises(ValidationError):
        f.page_headers = []  # type: ignore[misc]


# * mapper — RawDocument with header/footer paragraphs


def _empty_raw_para(section_idx: int = 0, para_idx: int = 0, text: str = "") -> RawParagraph:
    return RawParagraph(
        section_idx=section_idx,
        para_idx=para_idx,
        text=text,
        char_runs=[],
        tables=[],
        pictures=[],
    )


def test_build_hwp_document_routes_headers_to_furniture():
    raw = RawDocument(
        source_uri=None,
        section_count=1,
        paragraphs=[],
        headers=[_empty_raw_para(text="페이지 머리글")],
        footers=[],
    )
    ir = build_hwp_document(raw)
    assert ir.body == []
    assert len(ir.furniture.page_headers) == 1
    blk = ir.furniture.page_headers[0]
    assert isinstance(blk, ParagraphBlock)
    assert blk.text == "페이지 머리글"


def test_build_hwp_document_routes_footers_to_furniture():
    raw = RawDocument(
        source_uri=None,
        section_count=1,
        paragraphs=[],
        headers=[],
        footers=[_empty_raw_para(text="© 2026 회사명", para_idx=2)],
    )
    ir = build_hwp_document(raw)
    assert len(ir.furniture.page_footers) == 1
    blk = ir.furniture.page_footers[0]
    assert isinstance(blk, ParagraphBlock)
    assert blk.text == "© 2026 회사명"
    # ^ Provenance 는 부모 paragraph 위치 보존 (Header/Footer 컨트롤이 어디서 선언됐는지)
    assert blk.prov.para_idx == 2


def test_build_hwp_document_preserves_header_footer_order():
    """furniture iter 순서: page_headers → page_footers → footnotes."""
    raw = RawDocument(
        source_uri=None,
        section_count=1,
        paragraphs=[],
        headers=[_empty_raw_para(text="H1"), _empty_raw_para(text="H2")],
        footers=[_empty_raw_para(text="F1")],
    )
    ir = build_hwp_document(raw)
    iterated = list(ir.iter_blocks(scope="furniture", recurse=False))
    texts = [b.text for b in iterated if isinstance(b, ParagraphBlock)]
    assert texts == ["H1", "H2", "F1"]


def test_build_hwp_document_footnotes_empty_in_s1():
    """v0.3.0 S1 은 FootnoteBlock 미구현 — footnotes 는 항상 빈 리스트."""
    raw = RawDocument(source_uri=None, section_count=0, paragraphs=[], headers=[], footers=[])
    ir = build_hwp_document(raw)
    assert ir.furniture.footnotes == []


def test_build_hwp_document_furniture_paragraphs_share_section_idx():
    """Header/Footer paragraphs Provenance 는 Rust 가 설정한 외부 위치 그대로 보존."""
    raw = RawDocument(
        source_uri=None,
        section_count=2,
        paragraphs=[],
        headers=[_empty_raw_para(section_idx=1, para_idx=5, text="섹션 2 머리글")],
        footers=[],
    )
    ir = build_hwp_document(raw)
    blk = ir.furniture.page_headers[0]
    assert isinstance(blk, ParagraphBlock)
    assert blk.prov.section_idx == 1
    assert blk.prov.para_idx == 5


def test_build_hwp_document_header_with_table_flattens_to_furniture():
    """Header paragraphs 안의 표는 같은 평탄화 정책 적용 — TableBlock 도 page_headers 에 추가."""
    raw_para_with_table = RawParagraph(
        section_idx=0,
        para_idx=0,
        text="제목 행",
        char_runs=[],
        tables=[
            {
                "rows": 1,
                "cols": 1,
                "caption": None,
                "cells": [
                    {
                        "row": 0,
                        "col": 0,
                        "row_span": 1,
                        "col_span": 1,
                        "is_header": False,
                        "paragraphs": [
                            {
                                "section_idx": 0,
                                "para_idx": 0,
                                "text": "셀",
                                "char_runs": [],
                                "tables": [],
                                "pictures": [],
                            }
                        ],
                    }
                ],
            }
        ],
        pictures=[],
    )
    raw = RawDocument(
        source_uri=None,
        section_count=1,
        paragraphs=[],
        headers=[raw_para_with_table],
        footers=[],
    )
    ir = build_hwp_document(raw)
    assert len(ir.furniture.page_headers) == 2
    assert isinstance(ir.furniture.page_headers[0], ParagraphBlock)
    assert isinstance(ir.furniture.page_headers[1], TableBlock)


# * 실제 샘플 — aift.hwp 가 머리글/꼬리말 포함 여부에 따라 분기


def test_real_sample_furniture_yields_paragraph_blocks(parsed_hwp: rhwp.Document):
    """aift.hwp 에 헤더/푸터가 있으면 ParagraphBlock 으로 노출, 없으면 빈 리스트."""
    ir = parsed_hwp.to_ir()
    for blk in ir.furniture.page_headers + ir.furniture.page_footers:
        # ^ 채워진 경우 모두 알려진 Block 타입
        assert isinstance(blk, (ParagraphBlock, TableBlock))


def test_real_sample_iter_blocks_furniture_matches_lists(parsed_hwp: rhwp.Document):
    """iter_blocks(scope=furniture) 결과가 page_headers + page_footers + footnotes 합과 동일."""
    ir = parsed_hwp.to_ir()
    iterated = list(ir.iter_blocks(scope="furniture", recurse=False))
    expected = (
        list(ir.furniture.page_headers)
        + list(ir.furniture.page_footers)
        + list(ir.furniture.footnotes)
    )
    assert iterated == expected


def test_real_sample_body_excludes_header_footer_text(parsed_hwp: rhwp.Document):
    """body 와 furniture 는 분리된다 — 같은 paragraph 인스턴스가 양쪽 다 나타나면 안 됨."""
    ir = parsed_hwp.to_ir()
    body_ids = {id(b) for b in ir.body}
    for f in ir.furniture.page_headers + ir.furniture.page_footers:
        assert id(f) not in body_ids


# * 호환성 메모 — Furniture extra="forbid" 가 v0.2.0 schema 충돌 가짜 시뮬


def test_furniture_rejects_v0_3_0_endnotes_field_in_s1():
    """ir-expansion.md §호환성: v0.2.0 Furniture 는 endnotes 키를 거부.

    v0.3.0 S1 의 Furniture 도 아직 endnotes 키 미도입 (S2 에서 추가) — 같은 동작 보장.
    """
    import pytest

    with pytest.raises(ValidationError):
        Furniture.model_validate({"endnotes": []})


# * iter_blocks(scope=all) — body → furniture 순서 보존 (수동)


def test_iter_blocks_all_then_furniture_order():
    body = ParagraphBlock(text="본문", prov=Provenance(section_idx=0, para_idx=0))
    header = ParagraphBlock(text="머리글", prov=Provenance(section_idx=0, para_idx=99))
    footer = ParagraphBlock(text="꼬리말", prov=Provenance(section_idx=0, para_idx=100))
    ir = HwpDocument(
        body=[body],
        furniture=Furniture(page_headers=[header], page_footers=[footer]),
    )
    seq = list(ir.iter_blocks(scope="all", recurse=False))
    assert seq == [body, header, footer]


# * recurse 정책 — Header 안의 Table 셀 내부 paragraph 도 진입


def test_iter_blocks_furniture_recurse_enters_header_table_cells():
    inner = ParagraphBlock(text="cell", prov=Provenance(section_idx=0, para_idx=0))
    cell = TableCell(row=0, col=0, grid_index=0, blocks=[inner])
    header_table = TableBlock(
        rows=1, cols=1, cells=[cell], prov=Provenance(section_idx=0, para_idx=0)
    )
    ir = HwpDocument(furniture=Furniture(page_headers=[header_table]))
    recursed = list(ir.iter_blocks(scope="furniture", recurse=True))
    assert recursed == [header_table, inner]
    no_rec = list(ir.iter_blocks(scope="furniture", recurse=False))
    assert no_rec == [header_table]
