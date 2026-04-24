"""tests/test_ir_schema.py — Stage S1 Pydantic IR 단위 테스트.

ir.md §테스트 전략 §단위 테스트 항목 1:1 매핑. 통합 테스트 (샘플 HWP 왕복)
는 S2 이후, JSON Schema conformance / LLM strict-mode 테스트는 S4 이후.
"""

import warnings

import pytest
from pydantic import ValidationError
from rhwp.ir.nodes import (
    CURRENT_SCHEMA_VERSION,
    DocumentMetadata,
    HwpDocument,
    InlineRun,
    ParagraphBlock,
    Provenance,
    Section,
    TableBlock,
    TableCell,
    UnknownBlock,
)

# * 공통 픽스처 헬퍼


def _prov(section_idx: int = 0, para_idx: int = 0) -> Provenance:
    return Provenance(section_idx=section_idx, para_idx=para_idx)


def _paragraph(text: str = "hello", para_idx: int = 0) -> ParagraphBlock:
    return ParagraphBlock(
        text=text,
        inlines=[InlineRun(text=text)],
        prov=_prov(para_idx=para_idx),
    )


def _simple_table(para_idx: int = 1) -> TableBlock:
    return TableBlock(
        rows=2,
        cols=2,
        cells=[
            TableCell(row=0, col=0, grid_index=0, blocks=[_paragraph("A")]),
            TableCell(row=0, col=1, grid_index=1, blocks=[_paragraph("B")]),
            TableCell(row=1, col=0, grid_index=2, blocks=[_paragraph("C")]),
            TableCell(row=1, col=1, grid_index=3, blocks=[_paragraph("D")]),
        ],
        html="<table><tr><td>A</td><td>B</td></tr><tr><td>C</td><td>D</td></tr></table>",
        text="A\tB\nC\tD",
        prov=_prov(para_idx=para_idx),
    )


# * Test 1 — HwpDocument 왕복


def test_hwp_document_roundtrip():
    doc = HwpDocument(
        metadata=DocumentMetadata(title="test", author="kevin"),
        sections=[Section(section_idx=0), Section(section_idx=1)],
        body=[_paragraph("first"), _simple_table()],
    )
    dumped = doc.model_dump_json()
    reloaded = HwpDocument.model_validate_json(dumped)
    assert reloaded == doc
    assert reloaded.schema_name == "HwpDocument"
    assert reloaded.schema_version == CURRENT_SCHEMA_VERSION


# * Test 2 — ParagraphBlock 왕복


def test_paragraph_block_roundtrip():
    p = ParagraphBlock(
        text="hello world",
        inlines=[
            InlineRun(text="hello", bold=True),
            InlineRun(text=" "),
            InlineRun(text="world", italic=True, href="https://example.com"),
        ],
        prov=_prov(),
    )
    reloaded = ParagraphBlock.model_validate_json(p.model_dump_json())
    assert reloaded == p
    assert reloaded.inlines[0].bold is True
    assert reloaded.inlines[2].href == "https://example.com"


# * Test 3 — TableBlock 단순 왕복


def test_table_block_simple_roundtrip():
    t = _simple_table()
    assert TableBlock.model_validate_json(t.model_dump_json()) == t


# * Test 4 — 3단 중첩: TableCell → Block → TableCell


def test_table_nested_three_levels():
    innermost = TableBlock(
        rows=1,
        cols=1,
        cells=[TableCell(row=0, col=0, grid_index=0, blocks=[_paragraph("deep")])],
        prov=_prov(para_idx=3),
    )
    middle = TableBlock(
        rows=1,
        cols=1,
        cells=[TableCell(row=0, col=0, grid_index=0, blocks=[innermost])],
        prov=_prov(para_idx=2),
    )
    outer = TableBlock(
        rows=1,
        cols=1,
        cells=[TableCell(row=0, col=0, grid_index=0, blocks=[middle])],
        prov=_prov(para_idx=1),
    )
    doc = HwpDocument(body=[outer])

    reloaded = HwpDocument.model_validate_json(doc.model_dump_json())
    assert reloaded == doc

    # * 재귀 타입이 보존되는지 직접 확인 — isinstance narrowing 동작
    outer_blk = reloaded.body[0]
    assert isinstance(outer_blk, TableBlock)
    middle_blk = outer_blk.cells[0].blocks[0]
    assert isinstance(middle_blk, TableBlock)
    innermost_blk = middle_blk.cells[0].blocks[0]
    assert isinstance(innermost_blk, TableBlock)
    leaf_para = innermost_blk.cells[0].blocks[0]
    assert isinstance(leaf_para, ParagraphBlock)
    assert leaf_para.text == "deep"


# * Test 5 — 미지의 kind 는 UnknownBlock 으로 라우팅


def test_discriminator_routes_unknown_kind():
    raw = {
        "kind": "picture",
        "prov": {"section_idx": 0, "para_idx": 0},
        "src": "foo.png",  # ^ extra="allow" 로 payload 보존 확인
    }
    doc = HwpDocument.model_validate({"body": [raw]})
    blk = doc.body[0]
    assert isinstance(blk, UnknownBlock)
    assert blk.kind == "picture"
    # ^ extra="allow" — 임의 필드 보존
    assert blk.model_extra == {"src": "foo.png"}


# * Test 6 — 알려진 kind 는 해당 Block 으로 라우팅


def test_discriminator_routes_known_kinds():
    para_raw = {
        "kind": "paragraph",
        "text": "p",
        "inlines": [{"text": "p"}],
        "prov": {"section_idx": 0, "para_idx": 0},
    }
    tbl_raw = {
        "kind": "table",
        "rows": 1,
        "cols": 1,
        "cells": [],
        "prov": {"section_idx": 0, "para_idx": 1},
    }
    doc = HwpDocument.model_validate({"body": [para_raw, tbl_raw]})
    assert isinstance(doc.body[0], ParagraphBlock)
    assert isinstance(doc.body[1], TableBlock)


# * Test 7 — extra=forbid (UnknownBlock 제외)


@pytest.mark.parametrize(
    "model_cls, base_data",
    [
        (Provenance, {"section_idx": 0, "para_idx": 0}),
        (InlineRun, {"text": "x"}),
        (DocumentMetadata, {}),
        (Section, {"section_idx": 0}),
        (ParagraphBlock, {"prov": {"section_idx": 0, "para_idx": 0}}),
        (
            TableBlock,
            {"rows": 1, "cols": 1, "prov": {"section_idx": 0, "para_idx": 0}},
        ),
        (
            TableCell,
            {"row": 0, "col": 0, "grid_index": 0},
        ),
        (HwpDocument, {}),
    ],
)
def test_extra_forbid_raises_on_unknown_field(model_cls, base_data):
    with pytest.raises(ValidationError):
        model_cls.model_validate({**base_data, "definitely_not_a_field": 1})


# * Test 8 — frozen=True 로 직접 변경 차단


def test_frozen_raises_on_mutation():
    p = _paragraph()
    with pytest.raises(ValidationError):
        p.text = "mutated"  # type: ignore[misc]


def test_frozen_unknown_block_cannot_be_mutated():
    """UnknownBlock 은 extra="allow" 지만 frozen 이므로 여전히 불변."""
    u = UnknownBlock(kind="custom", prov=_prov())
    with pytest.raises(ValidationError):
        u.kind = "other"  # type: ignore[misc]


# * Test 9/10 — schema_version pattern


@pytest.mark.parametrize("ver", ["1.0", "1.1", "2.0.3", "10.20.30"])
def test_schema_version_accepts_valid(ver):
    # ^ major > current 는 UserWarning 나지만 validation 통과
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        d = HwpDocument(schema_version=ver)
    assert d.schema_version == ver


@pytest.mark.parametrize("ver", ["banana", "", "1", "1.", ".1", "1.0.0.0", "v1.0"])
def test_schema_version_rejects_invalid(ver):
    with pytest.raises(ValidationError):
        HwpDocument(schema_version=ver)


# * Test 11 — major 상향 시 UserWarning


def test_schema_version_warns_on_future_major():
    with pytest.warns(UserWarning, match="newer than supported"):
        d = HwpDocument(schema_version="2.0")
    assert d.schema_version == "2.0"


def test_schema_version_minor_bump_does_not_warn():
    """같은 major 안의 minor 상향은 warning 없음."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        # ^ 경고가 나면 error 로 raise — warning 없으면 정상 통과
        d = HwpDocument(schema_version="1.5")
    assert d.schema_version == "1.5"


# * Test 12 — UnknownBlock 은 임의 kind 수용


@pytest.mark.parametrize("k", ["picture", "custom_x", "footnote", "hwp_field"])
def test_unknown_block_preserves_arbitrary_kind(k):
    u = UnknownBlock(kind=k, prov=_prov())
    assert u.kind == k
    reloaded = UnknownBlock.model_validate_json(u.model_dump_json())
    assert reloaded.kind == k


# * Test 13 — Provenance codepoint offset 은 Python str slicing 과 호환


def test_provenance_char_offsets_are_codepoint_based():
    """이모지 (SMP, UTF-16 surrogate pair) 포함 텍스트에서 offset 이 올바른지."""
    text = "회의록 🙂 요약"
    target = "요약"
    start = text.index(target)  # ^ Python str.index 는 codepoint 인덱스
    prov = Provenance(
        section_idx=0,
        para_idx=0,
        char_start=start,
        char_end=start + len(target),
    )
    assert prov.char_start is not None
    assert prov.char_end is not None
    assert text[prov.char_start : prov.char_end] == target


# * Test 14 — InlineRun 기본값


def test_inline_run_defaults():
    r = InlineRun(text="x")
    assert r.text == "x"
    assert r.bold is False
    assert r.italic is False
    assert r.underline is False
    assert r.strikethrough is False
    assert r.href is None
    assert r.ruby is None
    assert r.raw_style_id is None
