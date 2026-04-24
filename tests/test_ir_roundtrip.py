"""tests/test_ir_roundtrip.py — Rust → IR 통합 테스트 (Stage S2/S3).

Fixture (``aift.hwp``, ``table-vpos-01.hwpx``) 로 실제 문서 → ``to_ir()`` 검증.

범위:
- ``Document.to_ir()`` 는 Pydantic ``HwpDocument`` 인스턴스 반환
- ``OnceCell`` 캐시 — 재호출 시 동일 객체
- Paragraph 는 ``ParagraphBlock`` 으로, ``Paragraph.controls`` 의 표는 ``TableBlock``
  으로 각각 body 에 평탄화 — S3 에서 "Paragraph → [ParagraphBlock, TableBlock...]"
- ``ParagraphBlock`` 의 Provenance 가 section/paragraph 인덱스에 단조
- ``InlineRun`` 은 단락 텍스트를 런으로 분할
- ``to_ir_json()`` 은 Pydantic 로 재파싱 가능

Table 전용 검증은 ``test_ir_tables.py``.
"""

import pytest
import rhwp
from pydantic import ValidationError
from rhwp.ir.nodes import HwpDocument, ParagraphBlock, TableBlock

# * 반환 타입 / 캐시


def test_to_ir_returns_hwp_document(parsed_hwp: rhwp.Document):
    ir = parsed_hwp.to_ir()
    assert isinstance(ir, HwpDocument)
    assert ir.schema_name == "HwpDocument"
    assert ir.schema_version == "1.0"


def test_to_ir_caches_same_object(parsed_hwp: rhwp.Document):
    """Rust OnceCell 덕에 동일 Document 인스턴스의 재호출은 같은 PyObject 반환."""
    ir1 = parsed_hwp.to_ir()
    ir2 = parsed_hwp.to_ir()
    assert ir1 is ir2


# * sections / body 카운트


def test_ir_section_count_matches_document(parsed_hwp: rhwp.Document):
    ir = parsed_hwp.to_ir()
    assert len(ir.sections) == parsed_hwp.section_count
    # ^ section_idx 는 0..N
    for i, sect in enumerate(ir.sections):
        assert sect.section_idx == i


def test_paragraph_block_count_matches(parsed_hwp: rhwp.Document):
    """S3 계약: body 내 ParagraphBlock 개수 = Rust paragraph_count.

    body 에는 TableBlock 도 섞여 있을 수 있으므로 ParagraphBlock 만 필터한다.
    """
    ir = parsed_hwp.to_ir()
    para_blocks = [b for b in ir.body if isinstance(b, ParagraphBlock)]
    assert len(para_blocks) == parsed_hwp.paragraph_count


def test_body_contains_only_known_block_kinds(parsed_hwp: rhwp.Document):
    """v0.2.0 (S3) 는 ParagraphBlock / TableBlock 둘만 노출. UnknownBlock 출현 금지."""
    ir = parsed_hwp.to_ir()
    for b in ir.body:
        assert isinstance(b, (ParagraphBlock, TableBlock)), (
            f"unexpected block kind: {type(b).__name__}"
        )


def test_ir_body_text_joined_matches_extract_text(parsed_hwp: rhwp.Document):
    """ParagraphBlock 텍스트만 개행으로 연결하면 ``extract_text()`` 와 일치.

    TableBlock 은 extract_text() 에 포함되지 않으므로 필터.
    """
    ir = parsed_hwp.to_ir()
    non_empty_texts = [b.text for b in ir.body if isinstance(b, ParagraphBlock) and b.text]
    assert "\n".join(non_empty_texts) == parsed_hwp.extract_text()


# * Provenance 단조성


def test_provenance_monotonic(parsed_hwp: rhwp.Document):
    """ParagraphBlock 만으로 (section_idx, para_idx) 가 순차 증가하는지 검증.

    TableBlock 은 같은 Paragraph 에서 파생되어 동일 para_idx 를 공유하므로
    본 테스트에서는 제외한다.
    """
    ir = parsed_hwp.to_ir()
    prev = None
    for block in ir.body:
        if not isinstance(block, ParagraphBlock):
            continue
        prov = block.prov
        if prev is None:
            prev = prov
            continue
        assert prov.section_idx >= prev.section_idx
        if prov.section_idx == prev.section_idx:
            assert prov.para_idx == prev.para_idx + 1
        else:
            # ^ 섹션 경계에서 para_idx 는 0 부터 재시작
            assert prov.para_idx == 0
        prev = prov


def test_provenance_char_end_matches_text_length(parsed_hwp: rhwp.Document):
    """ParagraphBlock 의 prov.char_end 는 ``len(block.text)`` 와 일치.

    TableBlock 은 char_start/char_end 가 None 이므로 별도 테스트에서 검증.
    """
    ir = parsed_hwp.to_ir()
    for block in ir.body:
        if not isinstance(block, ParagraphBlock):
            continue
        assert block.prov.char_start == 0
        # ^ codepoint 기준 길이 (ir.md §3) — Python len(str) 과 동일
        assert block.prov.char_end == len(block.text)
        assert block.prov.page_range is None


# * InlineRun 구조


def test_inline_run_text_concatenates_to_paragraph_text(parsed_hwp: rhwp.Document):
    """InlineRun.text 를 이어붙이면 ParagraphBlock.text 와 같아야 한다.

    런 분할은 char_shapes 순회 기반이라 텍스트 전체를 커버해야 한다.
    예외: 빈 문단은 inlines 도 빈 리스트.
    """
    ir = parsed_hwp.to_ir()
    for block in ir.body:
        if not isinstance(block, ParagraphBlock):
            continue
        joined = "".join(r.text for r in block.inlines)
        if not block.text:
            assert joined == ""
        else:
            assert joined == block.text


def test_inline_run_has_styled_runs(parsed_hwp: rhwp.Document):
    """실제 샘플에서 최소 하나의 InlineRun 이 raw_style_id 를 가져야 한다."""
    ir = parsed_hwp.to_ir()
    has_styled = False
    for block in ir.body:
        if not isinstance(block, ParagraphBlock):
            continue
        if any(run.raw_style_id is not None for run in block.inlines):
            has_styled = True
            break
    assert has_styled


# * HWPX 샘플도 동일 계약


def test_to_ir_on_hwpx_sample(parsed_hwpx: rhwp.Document):
    ir = parsed_hwpx.to_ir()
    assert isinstance(ir, HwpDocument)
    assert len(ir.sections) == parsed_hwpx.section_count
    para_blocks = [b for b in ir.body if isinstance(b, ParagraphBlock)]
    assert len(para_blocks) == parsed_hwpx.paragraph_count


# * to_ir_json 왕복


def test_to_ir_json_parses_back(parsed_hwp: rhwp.Document):
    j = parsed_hwp.to_ir_json()
    reloaded = HwpDocument.model_validate_json(j)
    assert reloaded == parsed_hwp.to_ir()


def test_to_ir_json_indent_option(parsed_hwp: rhwp.Document):
    compact = parsed_hwp.to_ir_json()
    pretty = parsed_hwp.to_ir_json(indent=2)
    # ^ indent 가 있으면 최소 한 줄은 개행 포함. indent 가 없으면 개행 없음
    assert "\n" in pretty
    assert "\n" not in compact
    assert len(pretty) > len(compact)


# * frozen — 반환 IR 수정 차단


def test_ir_is_frozen(parsed_hwp: rhwp.Document):
    ir = parsed_hwp.to_ir()
    with pytest.raises(ValidationError):
        ir.body = []  # type: ignore[misc]


# * Furniture / metadata — v0.2.0 은 전부 비어있거나 None


def test_furniture_is_empty(parsed_hwp: rhwp.Document):
    ir = parsed_hwp.to_ir()
    assert ir.furniture.page_headers == []
    assert ir.furniture.page_footers == []
    assert ir.furniture.footnotes == []


def test_metadata_fields_are_none(parsed_hwp: rhwp.Document):
    md = parsed_hwp.to_ir().metadata
    assert md.title is None
    assert md.author is None
    assert md.creation_time is None
    assert md.modification_time is None
