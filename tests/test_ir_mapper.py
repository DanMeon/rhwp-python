"""rhwp.ir._mapper 단위 테스트 — Rust 에 있던 동작의 Python 이전 후 regression 방어.

이전 src/ir.rs 에는 ``escape_html``, ``cell_role``, ``utf16_to_cp`` 등의 Rust
``#[cfg(test)]`` 단위 테스트가 있었다. 로직이 Python 으로 이동했으므로 동일한
규약을 Python 단위 테스트로 보존한다. 통합 테스트 (test_ir_tables, test_ir_roundtrip)
는 실제 샘플 문서의 텍스트가 대부분 escape 대상 문자를 포함하지 않아 escape
순서·폴백 정책의 regression 을 직접 감지하기 어렵다.

raw payload 는 ``rhwp.ir._raw_types`` 의 TypedDict 로 타입이 고정되어 있으므로
테스트 fixture 도 모든 필드를 채운 완전한 dict 여야 pyright 가 통과한다.
"""

from rhwp.ir._mapper import (
    _build_inline_runs,
    _cell_role,
    _escape_html,
    _table_to_html,
)
from rhwp.ir._raw_types import RawCell, RawCharRun, RawParagraph, RawTable

# * escape_html — & 우선 치환 규칙 보존 (이중 escape 방지)


def test_escape_html_ampersand_first():
    # ^ & 를 먼저 치환하지 않으면 &lt; 의 & 가 재치환되어 &amp;lt; 가 됨
    assert _escape_html("&lt;") == "&amp;lt;"


def test_escape_html_all_special_chars():
    assert _escape_html("<b>A & B</b>") == "&lt;b&gt;A &amp; B&lt;/b&gt;"


def test_escape_html_quote():
    assert _escape_html('"hello"') == "&quot;hello&quot;"


def test_escape_html_does_not_escape_apostrophe():
    # ^ html.escape 는 ' 도 escape — 기존 Rust escape_html 과 불일치하므로 미사용
    assert _escape_html("it's") == "it's"


def test_escape_html_preserves_non_ascii():
    assert _escape_html("한글 & テスト") == "한글 &amp; テスト"


# * cell_role — HWP → DocLayNet 어휘 매핑 3갈래


def _paragraph(text: str) -> RawParagraph:
    return RawParagraph(section_idx=0, para_idx=0, text=text, char_runs=[], tables=[])


def _cell(
    *,
    is_header: bool = False,
    row_span: int = 1,
    col_span: int = 1,
    texts: tuple[str, ...] = (),
) -> RawCell:
    return RawCell(
        row=0,
        col=0,
        row_span=row_span,
        col_span=col_span,
        is_header=is_header,
        paragraphs=[_paragraph(t) for t in texts],
    )


def test_cell_role_header():
    assert _cell_role(_cell(is_header=True)) == "column_header"


def test_cell_role_unmerged_is_data():
    assert _cell_role(_cell(texts=("content",))) == "data"


def test_cell_role_unmerged_empty_is_data():
    # ^ 병합이 아니면 빈 셀이어도 data — layout 은 구조 유지용 병합 셀 전용
    assert _cell_role(_cell(texts=("",))) == "data"


def test_cell_role_merged_nonempty_is_data():
    assert _cell_role(_cell(col_span=2, texts=("content",))) == "data"


def test_cell_role_merged_empty_is_layout():
    assert _cell_role(_cell(row_span=2, texts=())) == "layout"


def test_cell_role_merged_whitespace_only_is_layout():
    # ^ trim 후 empty 여야 layout — 탭/개행만 있어도 layout 취급
    assert _cell_role(_cell(row_span=3, texts=("   \n\t",))) == "layout"


# * build_inline_runs — 폴백 정책 3갈래


def _char_run(
    *,
    start_cp: int,
    end_cp: int,
    char_shape_id: int = 0,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    strikethrough: bool = False,
) -> RawCharRun:
    return RawCharRun(
        start_cp=start_cp,
        end_cp=end_cp,
        char_shape_id=char_shape_id,
        bold=bold,
        italic=italic,
        underline=underline,
        strikethrough=strikethrough,
    )


def test_build_inline_runs_empty_text_returns_empty():
    assert _build_inline_runs("", []) == []


def test_build_inline_runs_empty_char_runs_fallback():
    # ^ char_runs 없는 정상 문단은 style-less 단일 런으로 폴백
    runs = _build_inline_runs("hello", [])
    assert len(runs) == 1
    assert runs[0].text == "hello"
    assert runs[0].raw_style_id is None


def test_build_inline_runs_prepends_prefix_when_first_run_not_at_zero():
    # ^ 손상 파일 대비: 첫 char_run 이 0 부터 시작 안 하면 앞쪽 style-less prepend
    runs = _build_inline_runs(
        "ABCDEF",
        [_char_run(start_cp=2, end_cp=4, char_shape_id=7, bold=True)],
    )
    assert [r.text for r in runs] == ["AB", "CD"]
    assert runs[0].raw_style_id is None
    assert runs[1].raw_style_id == 7
    assert runs[1].bold is True


def test_build_inline_runs_all_zero_width_from_zero_triggers_fallback():
    # ^ first_start=0 이고 모든 run 이 zero-width 면 prefix 도 없어 runs 가 비고
    #   최종 폴백으로 style-less 단일 런이 출고된다
    runs = _build_inline_runs("xyz", [_char_run(start_cp=0, end_cp=0)])
    assert len(runs) == 1
    assert runs[0].text == "xyz"
    assert runs[0].raw_style_id is None


def test_build_inline_runs_preserves_prefix_when_rest_zero_width():
    # ^ 손상 파일에서 첫 run 이 start_cp>0 이고 나머지가 zero-width 면 prefix 만 출고
    #   (최종 폴백은 "runs 가 비었을 때" 만 작동 — prefix 가 이미 들어 있으면 skip)
    runs = _build_inline_runs("xyz", [_char_run(start_cp=1, end_cp=1)])
    assert [r.text for r in runs] == ["x"]
    assert runs[0].raw_style_id is None


# * table_to_html — attribute 순서 (rowspan → colspan) 및 tag 선택


def _table(cells: list[RawCell]) -> RawTable:
    return RawTable(rows=1, cols=1, caption=None, cells=cells)


def test_table_to_html_rowspan_before_colspan():
    # ^ dedup hash 안정성 위해 attribute 순서 고정 — ir.md §2
    raw = _table([RawCell(row=0, col=0, row_span=2, col_span=3, is_header=False, paragraphs=[])])
    html = _table_to_html(raw)
    assert 'rowspan="2" colspan="3"' in html
    assert 'colspan="3" rowspan="2"' not in html


def test_table_to_html_span_one_omits_attribute():
    raw = _table(
        [
            RawCell(
                row=0,
                col=0,
                row_span=1,
                col_span=1,
                is_header=False,
                paragraphs=[_paragraph("x")],
            )
        ]
    )
    html = _table_to_html(raw)
    assert "rowspan" not in html
    assert "colspan" not in html


def test_table_to_html_header_uses_th():
    raw = _table(
        [
            RawCell(
                row=0,
                col=0,
                row_span=1,
                col_span=1,
                is_header=True,
                paragraphs=[_paragraph("Name")],
            )
        ]
    )
    html = _table_to_html(raw)
    assert "<th>Name</th>" in html
    assert "<td>" not in html


def test_table_to_html_escapes_cell_text():
    raw = _table(
        [
            RawCell(
                row=0,
                col=0,
                row_span=1,
                col_span=1,
                is_header=False,
                paragraphs=[_paragraph('<a> & "b"')],
            )
        ]
    )
    html = _table_to_html(raw)
    assert "&lt;a&gt; &amp; &quot;b&quot;" in html
