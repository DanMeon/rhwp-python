"""tests/test_ir_schema_export.py — Stage S4 JSON Schema export / load 검증.

범위:
- ``export_schema()`` 가 ``$id`` / ``$schema`` (Draft 2020-12) 주입
- 모든 IR 노드가 ``additionalProperties: false`` (UnknownBlock 제외 — ``extra="allow"``)
- ``minimum`` / ``maximum`` / ``exclusiveMinimum`` / ``exclusiveMaximum`` 키워드 부재
  (OpenAI strict mode 가 이 키워드를 거부하기 때문 — CLAUDE.md 전역 규칙)
- JSON Schema Draft 2020-12 meta-validation 통과
- ``load_schema()`` 가 반환하는 in-package JSON 이 ``export_schema()`` 결과와 sync
- ``HwpDocument.model_validate`` 로 검증 통과한 인스턴스가 ``jsonschema.validate()`` 도 통과
"""

import json
from typing import Any

import pytest

# ^ jsonschema 는 testing group 에 포함되지만 core-only 환경에서는 없을 수 있음
pytest.importorskip("jsonschema")
from jsonschema import Draft202012Validator  # noqa: E402
from rhwp.ir.nodes import HwpDocument, InlineRun, ParagraphBlock, Provenance
from rhwp.ir.schema import (
    SCHEMA_DIALECT,
    SCHEMA_ID,
    export_schema,
    load_schema,
)

# * export_schema 구조


def test_export_schema_has_id_and_dialect():
    schema = export_schema()
    assert schema["$id"] == SCHEMA_ID
    assert schema["$schema"] == SCHEMA_DIALECT
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_export_schema_root_additional_properties_false():
    schema = export_schema()
    assert schema.get("additionalProperties") is False


def test_export_schema_defs_are_exactly_the_known_nodes():
    """`$defs` 는 HwpDocument (root) 를 제외한 12개 노드 정확히 일치.

    v0.3.0 S1: ImageRef + PictureBlock 추가 (10 → 12). 이후 stage (Formula /
    Footnote / Endnote / ListItem / Caption / Toc / Field) 추가 시 갱신.
    """
    schema = export_schema()
    defs = schema.get("$defs", {})
    expected_nodes = {
        "Provenance",
        "InlineRun",
        "DocumentMetadata",
        "DocumentSource",
        "Section",
        "ParagraphBlock",
        "TableBlock",
        "TableCell",
        "UnknownBlock",
        "Furniture",
        "ImageRef",
        "PictureBlock",
    }
    assert set(defs.keys()) == expected_nodes


def test_export_schema_known_blocks_forbid_additional():
    """모든 IR 노드는 ``additionalProperties: false`` (UnknownBlock 제외).

    UnknownBlock 은 ``extra="allow"`` 이므로 Pydantic 이 ``additionalProperties: true``
    를 명시 출력 — ``False`` 만 아니면 forward-compat 계약 충족.
    """
    schema = export_schema()
    defs = schema.get("$defs", {})
    for name, body in defs.items():
        if name == "UnknownBlock":
            assert body.get("additionalProperties") is not False
        else:
            assert body.get("additionalProperties") is False, (
                f"{name} 은 additionalProperties=false 여야 함"
            )


def test_export_schema_no_numeric_range_keywords():
    """OpenAI strict mode 가 ``minimum``/``maximum`` 등을 400 으로 거부하므로 전부 부재."""
    schema = export_schema()
    forbidden = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"}
    _assert_no_keywords(schema, forbidden)


def _assert_no_keywords(node: Any, forbidden: set[str], path: str = "$") -> None:
    if isinstance(node, dict):
        for key in node:
            if key in forbidden:
                raise AssertionError(f"Forbidden keyword {key!r} found at {path}: {node[key]}")
        for k, v in node.items():
            _assert_no_keywords(v, forbidden, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _assert_no_keywords(v, forbidden, f"{path}[{i}]")


# * Meta-validation — Draft 2020-12 준수


def test_export_schema_passes_meta_validation():
    """Draft 2020-12 meta-schema 로 우리 스키마를 검증."""
    schema = export_schema()
    # ^ check_schema() 는 invalid 시 jsonschema.SchemaError 발생
    Draft202012Validator.check_schema(schema)


# * load_schema — in-package JSON 이 코드와 sync


def test_load_schema_matches_export_schema():
    """Repo 에 체크인된 hwp_ir_v1.json 이 현재 코드의 export_schema() 와 동일해야 한다.

    불일치 시: `python -m rhwp.ir.schema > python/rhwp/ir/schema/hwp_ir_v1.json` 재생성.
    """
    packaged = load_schema()
    current = export_schema()
    assert packaged == current, (
        "Packaged schema out of sync with code. "
        "Regenerate: python -m rhwp.ir.schema > python/rhwp/ir/schema/hwp_ir_v1.json"
    )


def test_load_schema_is_valid_draft_2020_12():
    Draft202012Validator.check_schema(load_schema())


# * 실제 인스턴스가 schema 를 통과


def test_real_hwp_document_validates_against_schema(parsed_hwp):
    """실제 HWP 파싱 결과가 JSON Schema validation 을 통과."""
    schema = export_schema()
    validator = Draft202012Validator(schema)
    doc = parsed_hwp.to_ir()
    instance = doc.model_dump(mode="json")
    # ^ iter_errors 로 모두 수집 후 보고 (첫 오류만이 아니라 전부)
    errors = list(validator.iter_errors(instance))
    assert not errors, (
        f"Schema validation failed with {len(errors)} errors. "
        f"First: {errors[0].message} at {list(errors[0].absolute_path)}"
    )


def test_minimal_hwp_document_validates():
    """빈 HwpDocument 도 스키마를 통과."""
    schema = export_schema()
    Draft202012Validator(schema).validate(HwpDocument().model_dump(mode="json"))


def test_paragraph_block_with_inlines_validates():
    schema = export_schema()
    validator = Draft202012Validator(schema)
    block = ParagraphBlock(
        text="hi",
        inlines=[InlineRun(text="hi", bold=True)],
        prov=Provenance(section_idx=0, para_idx=0),
    )
    doc = HwpDocument(body=[block])
    validator.validate(doc.model_dump(mode="json"))


def test_invalid_kind_fails_schema_validation():
    """스키마 수준에서도 미지의 kind 는 UnknownBlock 으로 라우팅되는데,
    UnknownBlock 은 ``extra="allow"`` 이므로 검증 성공. 반면 ParagraphBlock
    타입에 kind=table 을 억지로 넣으면 Pydantic 파싱 자체가 실패한다.

    Draft 2020-12 는 tagged union 의 callable discriminator 의미를 직접 표현
    못 하지만, ``$defs.ParagraphBlock.properties.kind.const == "paragraph"`` 는
    반영되어 있어 schema 수준에서도 일관성 유지.
    """
    schema = export_schema()
    pb_defn = schema["$defs"]["ParagraphBlock"]
    assert pb_defn["properties"]["kind"].get("const") == "paragraph"
    tb_defn = schema["$defs"]["TableBlock"]
    assert tb_defn["properties"]["kind"].get("const") == "table"


# * SCHEMA_ID / SCHEMA_DIALECT 는 상수


def test_schema_id_has_immutable_v1_path():
    """ir.md §불변 경로 정책 — v1 URL 은 영구. Breaking change 는 v2 새 URL."""
    assert "/v1/" in SCHEMA_ID
    assert SCHEMA_ID.endswith("/schema.json")


def test_load_schema_raises_file_not_found_when_packaged_json_missing(monkeypatch):
    """maturin include 누락 등으로 in-package JSON 이 빠졌을 때 FileNotFoundError.

    ``files("rhwp.ir")`` 로 얻은 Traversable 에 동일한 인터페이스를 제공하지만
    ``is_file()`` 가 False 를 반환하는 객체를 주입해 에러 경로를 재현한다.
    """

    class _MissingResource:
        def joinpath(self, *_parts: str) -> "_MissingResource":
            return self

        def is_file(self) -> bool:
            return False

        def __str__(self) -> str:
            return "<packaged schema missing>"

    import rhwp.ir.schema as schema_mod

    monkeypatch.setattr(schema_mod, "files", lambda _package: _MissingResource())
    with pytest.raises(FileNotFoundError, match="Packaged schema not found"):
        schema_mod.load_schema()
