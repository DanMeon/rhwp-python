"""tests/test_ir_tables.py — Stage S3 TableBlock 전용 통합 테스트.

HWPX 샘플 ``table-vpos-01.hwpx`` 는 표 9개를 포함한 실제 문서 — TableBlock
출력, HTML/text 직렬화, 셀 배열, Provenance 공유, 중첩 지원을 검증한다.
"""

import pytest
import rhwp
from rhwp.ir.nodes import HwpDocument, ParagraphBlock, TableBlock

# * 샘플에 TableBlock 이 실제로 나타나는가


def test_hwpx_sample_has_tables(parsed_hwpx: rhwp.Document):
    """샘플 문서는 표가 있어 TableBlock 이 최소 1개 이상 생성되어야 한다."""
    ir = parsed_hwpx.to_ir()
    tables = [b for b in ir.body if isinstance(b, TableBlock)]
    assert len(tables) > 0, "샘플 문서는 표를 포함해야 함"


# * TableBlock 필수 필드


def test_table_block_fields_populated(parsed_hwpx: rhwp.Document):
    ir = parsed_hwpx.to_ir()
    tables = [b for b in ir.body if isinstance(b, TableBlock)]
    for t in tables:
        assert t.rows > 0
        assert t.cols > 0
        # ^ 병합이 없으면 cells == rows * cols, 병합이 있으면 < (unique anchor cells 만)
        assert 0 < len(t.cells) <= t.rows * t.cols
        assert t.html.startswith("<table>")
        assert t.html.endswith("</table>")
        assert isinstance(t.text, str)
        # ^ kind discriminator 확인
        assert t.kind == "table"


# * HTML 직렬화 형식 검증


def test_table_html_tr_td_structure(parsed_hwpx: rhwp.Document):
    """각 TableBlock 의 HTML 은 <tr>/<td>|<th> 중첩을 가진다.

    ``<tr>`` 개수는 ``rows`` 이하 — row-span 으로 덮인 중간 행은 anchor cell
    이 없어 <tr> 을 방출하지 않을 수 있다 (HTML 표준: rowspan 이 다음 행을 자동 span).
    """
    ir = parsed_hwpx.to_ir()
    tables = [b for b in ir.body if isinstance(b, TableBlock)]
    for t in tables:
        tr_open = t.html.count("<tr>")
        tr_close = t.html.count("</tr>")
        # ^ 열고 닫는 쌍이 맞고, rows 를 초과하지 않음
        assert tr_open == tr_close
        assert 0 < tr_open <= t.rows
        # td 또는 th 셀 마커가 cells 개수와 일치
        cell_opens = t.html.count("<td") + t.html.count("<th")
        assert cell_opens == len(t.cells)


# ^ HTML escape 의 실질 검증은 src/ir.rs 의 Rust unit tests (escape_html_*) 에서 수행.
#   Python 측은 실제 문서에 특수문자가 없을 수 있어 커버리지 공백 — Rust 에서 보장


# * text 직렬화


def test_table_text_row_and_cell_separators(parsed_hwpx: rhwp.Document):
    """표 text 는 행 `\\n`, 셀 `\\t` 구분.

    row-span 으로 덮인 중간 행은 anchor cell 이 없어 해당 행이 생략될 수 있다.
    따라서 개행 수 ≤ rows - 1 (rows=1 이면 0).
    """
    ir = parsed_hwpx.to_ir()
    for t in (b for b in ir.body if isinstance(b, TableBlock)):
        newlines = t.text.count("\n")
        assert 0 <= newlines <= max(0, t.rows - 1)


# * TableCell 구조


def test_table_cells_have_valid_coordinates(parsed_hwpx: rhwp.Document):
    ir = parsed_hwpx.to_ir()
    for t in (b for b in ir.body if isinstance(b, TableBlock)):
        for cell in t.cells:
            assert 0 <= cell.row < t.rows
            assert 0 <= cell.col < t.cols
            assert cell.row_span >= 1
            assert cell.col_span >= 1
            # ^ span 이 표 경계를 넘지 않음
            assert cell.row + cell.row_span <= t.rows
            assert cell.col + cell.col_span <= t.cols
            assert cell.grid_index == cell.row * t.cols + cell.col
            assert cell.role in ("data", "column_header", "row_header", "layout")


def test_table_cells_blocks_are_paragraph_or_table(parsed_hwpx: rhwp.Document):
    """TableCell.blocks 는 ParagraphBlock 또는 TableBlock (중첩 표) 만."""
    ir = parsed_hwpx.to_ir()
    for t in (b for b in ir.body if isinstance(b, TableBlock)):
        for cell in t.cells:
            for blk in cell.blocks:
                assert isinstance(blk, (ParagraphBlock, TableBlock))


# * Provenance — ParagraphBlock 과 같은 para_idx 를 공유


def test_table_block_shares_provenance_with_paragraph(parsed_hwpx: rhwp.Document):
    """각 TableBlock 은 직전에 있는 ParagraphBlock 과 section_idx + para_idx 를 공유.

    S3 평탄화 규칙 "ParagraphBlock 1 + 포함 표마다 TableBlock" 의 검증.
    """
    ir = parsed_hwpx.to_ir()
    last_para_prov = None
    for block in ir.body:
        if isinstance(block, ParagraphBlock):
            last_para_prov = block.prov
        elif isinstance(block, TableBlock):
            assert last_para_prov is not None
            assert block.prov.section_idx == last_para_prov.section_idx
            assert block.prov.para_idx == last_para_prov.para_idx
            # ^ TableBlock 의 char 오프셋은 "문단 텍스트 밖" 이므로 None
            assert block.prov.char_start is None
            assert block.prov.char_end is None


# * JSON 왕복 — TableBlock 도 포함


def test_table_block_survives_json_roundtrip(parsed_hwpx: rhwp.Document):
    ir = parsed_hwpx.to_ir()
    reloaded = HwpDocument.model_validate_json(parsed_hwpx.to_ir_json())
    orig_tables = [b for b in ir.body if isinstance(b, TableBlock)]
    reload_tables = [b for b in reloaded.body if isinstance(b, TableBlock)]
    assert len(orig_tables) == len(reload_tables)
    for a, b in zip(orig_tables, reload_tables):
        assert a == b


# * 중첩 표 — 샘플이 중첩을 포함한다면 검증, 없으면 skip


def test_nested_tables_are_block_compatible(parsed_hwpx: rhwp.Document):
    """샘플에 중첩 표가 있으면 TableCell.blocks 안의 TableBlock 이 TableBlock 으로 인식된다.

    중첩이 없으면 skip — 실제 HWP 파일에 중첩 표가 흔하지 않다.
    """
    ir = parsed_hwpx.to_ir()
    nested_count = 0
    for t in (b for b in ir.body if isinstance(b, TableBlock)):
        for cell in t.cells:
            for blk in cell.blocks:
                if isinstance(blk, TableBlock):
                    nested_count += 1
                    # ^ 중첩 표도 동일 스키마 계약
                    assert blk.rows > 0
                    assert blk.cols > 0
                    assert blk.html.startswith("<table>")
    if nested_count == 0:
        pytest.skip("샘플에 중첩 표 없음")


# * HWP5 샘플 — 표가 있을 수도 없을 수도. 있으면 동일 계약, 없으면 skip


def test_hwp5_sample_tables_follow_contract(parsed_hwp: rhwp.Document):
    ir = parsed_hwp.to_ir()
    tables = [b for b in ir.body if isinstance(b, TableBlock)]
    if not tables:
        pytest.skip("HWP5 샘플에 표 없음")
    for t in tables:
        assert t.rows > 0
        assert t.cols > 0
        assert t.html.startswith("<table>")
