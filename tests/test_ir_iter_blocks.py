"""tests/test_ir_iter_blocks.py — Stage S5 iter_blocks 메서드 검증.

``HwpDocument.iter_blocks(*, scope, recurse)`` 의 계약:

- ``scope="body"`` (기본): 본문 블록만
- ``scope="furniture"``: 머리글/꼬리말/각주만 (v0.2.0 은 빈 리스트)
- ``scope="all"``: 본문 먼저, 이어서 장식
- ``recurse=True`` (기본): ``TableCell.blocks`` 재귀
- ``recurse=False``: 최상위 body 만
"""

import rhwp
from rhwp.ir.nodes import (
    Furniture,
    HwpDocument,
    ParagraphBlock,
    Provenance,
    TableBlock,
    TableCell,
)

# * 반환 타입 / 기본 scope


def test_iter_blocks_default_equals_body(parsed_hwpx: rhwp.Document):
    ir = parsed_hwpx.to_ir()
    default = list(ir.iter_blocks())
    body_explicit = list(ir.iter_blocks(scope="body"))
    assert default == body_explicit


def test_iter_blocks_body_recurse_enters_table_cells(parsed_hwpx: rhwp.Document):
    """recurse=True 면 중첩 블록 개수 > 최상위만 센 개수."""
    ir = parsed_hwpx.to_ir()
    recursed = list(ir.iter_blocks(scope="body", recurse=True))
    top_only = list(ir.iter_blocks(scope="body", recurse=False))
    assert len(recursed) >= len(top_only)
    assert len(top_only) == len(ir.body)


def test_iter_blocks_recurse_false_matches_body_len(parsed_hwpx: rhwp.Document):
    ir = parsed_hwpx.to_ir()
    blocks = list(ir.iter_blocks(scope="body", recurse=False))
    assert len(blocks) == len(ir.body)
    # ^ recurse=False 는 직접 yield 순서 = ir.body 순서
    for got, want in zip(blocks, ir.body):
        assert got is want


# * furniture scope


def test_iter_blocks_furniture_yields_consistent_with_lists(parsed_hwpx: rhwp.Document):
    """v0.3.0 S1 부터 furniture 가 채워질 수 있다 — yield 결과 == 리스트 직접 합산.

    실제 채워진 개수는 샘플에 따라 0 일 수도 있다 (table-vpos-01.hwpx 가
    헤더/푸터 없으면 빈 리스트). 본 테스트는 iter_blocks(furniture) 가 항상
    page_headers + page_footers + footnotes 를 순서대로 평탄화하는 계약만 검증.
    """
    ir = parsed_hwpx.to_ir()
    blocks = list(ir.iter_blocks(scope="furniture", recurse=False))
    expected = (
        list(ir.furniture.page_headers)
        + list(ir.furniture.page_footers)
        + list(ir.furniture.footnotes)
    )
    assert blocks == expected


def test_iter_blocks_all_scope_body_first_then_furniture():
    """scope="all" 은 body 를 먼저, 이어서 furniture.

    수동 Furniture 주입으로 검증 — v0.2.0 Furniture 는 실제 파싱에서 항상 비어있음.
    """
    prov = Provenance(section_idx=0, para_idx=0)
    body_block = ParagraphBlock(text="body", prov=prov)
    furniture_block = ParagraphBlock(text="header", prov=Provenance(section_idx=0, para_idx=99))
    ir = HwpDocument(
        body=[body_block],
        furniture=Furniture(page_headers=[furniture_block]),
    )
    all_blocks = list(ir.iter_blocks(scope="all"))
    assert len(all_blocks) == 2
    assert all_blocks[0] is body_block
    assert all_blocks[1] is furniture_block


def test_iter_blocks_furniture_order_is_headers_footers_footnotes():
    """Furniture 내부는 항상 page_headers → page_footers → footnotes 순 (ir.md 계약)."""
    header = ParagraphBlock(text="H", prov=Provenance(section_idx=0, para_idx=1))
    footer = ParagraphBlock(text="F", prov=Provenance(section_idx=0, para_idx=2))
    footnote = ParagraphBlock(text="N", prov=Provenance(section_idx=0, para_idx=3))
    ir = HwpDocument(
        furniture=Furniture(
            page_headers=[header],
            page_footers=[footer],
            footnotes=[footnote],
        ),
    )
    assert list(ir.iter_blocks(scope="furniture")) == [header, footer, footnote]


# * 재귀 순회 — 수동 구성 중첩 표로 계약 확정


def test_iter_blocks_recurse_visits_nested_table_cells():
    """TableCell.blocks 안의 블록이 recurse=True 에서 yield 된다."""
    prov = Provenance(section_idx=0, para_idx=0)
    inner_para = ParagraphBlock(text="inside cell", prov=prov)
    cell = TableCell(row=0, col=0, grid_index=0, blocks=[inner_para])
    table = TableBlock(rows=1, cols=1, cells=[cell], prov=prov)
    top_para = ParagraphBlock(text="top", prov=prov)
    ir = HwpDocument(body=[top_para, table])

    recursed = list(ir.iter_blocks(scope="body", recurse=True))
    # ^ top_para, table, inner_para (순서)
    assert len(recursed) == 3
    assert recursed[0] is top_para
    assert recursed[1] is table
    assert recursed[2] is inner_para


def test_iter_blocks_recurse_false_skips_nested_blocks():
    prov = Provenance(section_idx=0, para_idx=0)
    inner_para = ParagraphBlock(text="inside", prov=prov)
    cell = TableCell(row=0, col=0, grid_index=0, blocks=[inner_para])
    table = TableBlock(rows=1, cols=1, cells=[cell], prov=prov)
    ir = HwpDocument(body=[table])

    no_rec = list(ir.iter_blocks(scope="body", recurse=False))
    assert len(no_rec) == 1
    assert no_rec[0] is table
    # ^ inner_para 는 cell.blocks 안이라 recurse=False 에서 제외됨


# * 깊은 재귀 (3단 중첩)


def test_iter_blocks_handles_three_level_nesting():
    prov = Provenance(section_idx=0, para_idx=0)
    leaf = ParagraphBlock(text="leaf", prov=prov)
    innermost_tbl = TableBlock(
        rows=1,
        cols=1,
        cells=[TableCell(row=0, col=0, grid_index=0, blocks=[leaf])],
        prov=prov,
    )
    middle_tbl = TableBlock(
        rows=1,
        cols=1,
        cells=[TableCell(row=0, col=0, grid_index=0, blocks=[innermost_tbl])],
        prov=prov,
    )
    outer_tbl = TableBlock(
        rows=1,
        cols=1,
        cells=[TableCell(row=0, col=0, grid_index=0, blocks=[middle_tbl])],
        prov=prov,
    )
    ir = HwpDocument(body=[outer_tbl])
    recursed = list(ir.iter_blocks(scope="body", recurse=True))
    # ^ outer, middle, innermost, leaf (4개)
    assert len(recursed) == 4
    assert recursed[0] is outer_tbl
    assert recursed[-1] is leaf


# * 실제 HWPX 샘플 스냅샷 — recurse 가 실제로 더 많이 yield


def test_iter_blocks_recurse_yields_more_on_real_sample(parsed_hwpx: rhwp.Document):
    ir = parsed_hwpx.to_ir()
    with_recurse = sum(1 for _ in ir.iter_blocks(recurse=True))
    without_recurse = sum(1 for _ in ir.iter_blocks(recurse=False))
    assert with_recurse > without_recurse
    # ^ 표가 있는 샘플이므로 recurse 시 TableCell.blocks 내부 블록이 추가됨


# * 타입 안전 — 모든 yield 는 Block 유니온 멤버


def test_iter_blocks_yields_only_known_block_types(parsed_hwpx: rhwp.Document):
    ir = parsed_hwpx.to_ir()
    from rhwp.ir.nodes import PictureBlock, UnknownBlock

    for block in ir.iter_blocks(scope="all", recurse=True):
        assert isinstance(block, (ParagraphBlock, TableBlock, PictureBlock, UnknownBlock))
