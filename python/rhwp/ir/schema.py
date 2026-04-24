"""rhwp.ir.schema — Document IR JSON Schema export / load.

배포 경로:

1. **In-package** (1차) — ``python/rhwp/ir/schema/hwp_ir_v1.json``.
   ``load_schema()`` 가 ``importlib.resources`` 로 로드하므로 네트워크 불필요.
2. **GitHub Pages** (공개 URL) — ``danmeon.github.io/rhwp-python/schema/hwp_ir/v1/schema.json``.
   ``$id`` 에 하드코딩. CI (`.github/workflows/publish-schema.yml`) 가 배포.

LLM Structured Outputs strict mode 는 "모든 property required + top-level
additionalProperties false" 를 요구한다. 본 스키마는 ``extra="forbid"`` 로
후자는 충족하지만 Pydantic V2 기본 동작상 default 값 있는 필드는 required
에서 제외되므로, strict 프로필이 필요한 소비자는 후처리가 필요하다.
"""

import json
from importlib.resources import files
from typing import Any, Final

from rhwp.ir.nodes import HwpDocument

__all__ = [
    "SCHEMA_ID",
    "SCHEMA_DIALECT",
    "export_schema",
    "load_schema",
]

SCHEMA_ID: Final = "https://danmeon.github.io/rhwp-python/schema/hwp_ir/v1/schema.json"
SCHEMA_DIALECT: Final = "https://json-schema.org/draft/2020-12/schema"

# ^ In-package JSON 의 위치 — importlib.resources 로 읽을 때 사용
_PACKAGED_SCHEMA_NAME: Final = "hwp_ir_v1.json"


def export_schema() -> dict[str, Any]:
    """Pydantic ``HwpDocument.model_json_schema(mode="serialization")`` 출력에
    ``$id`` / ``$schema`` 를 주입하고 discriminator 후처리를 적용해 반환한다.

    이 함수가 IR 의 권위적 스키마 생성 경로다. CI 가 결과를 파일로 덤프하여
    in-package JSON 및 GitHub Pages 에 배포한다.
    """
    schema = HwpDocument.model_json_schema(mode="serialization")
    # ^ dict 순서 유지를 위해 새 dict 로 재구성 — $schema/$id 를 맨 앞에 배치
    out: dict[str, Any] = {"$schema": SCHEMA_DIALECT, "$id": SCHEMA_ID}
    out.update(schema)
    _harden_unknown_variant(out)
    return out


def _harden_unknown_variant(schema: dict[str, Any]) -> None:
    """UnknownBlock 스키마에 "kind 가 known 값이 아님" 제약을 주입한다.

    Pydantic V2 callable Discriminator 는 JSON Schema ``discriminator`` 키워드로
    표현 불가 — 기본 출력은 단순 ``oneOf`` 이라 UnknownBlock (``extra="allow"``)
    이 ParagraphBlock/TableBlock 인스턴스에도 매치되어 oneOf 가 실패한다.
    known variant 들의 ``kind.const`` 를 모아 UnknownBlock.kind 에 ``not.enum``
    으로 주입하면 oneOf 가 정확히 하나로 수렴한다.
    """
    defs = schema.get("$defs", {})
    unknown = defs.get("UnknownBlock")
    if not unknown:
        return
    known_kinds: list[str] = []
    for name, body in defs.items():
        if name == "UnknownBlock":
            continue
        kind_prop = body.get("properties", {}).get("kind", {})
        const = kind_prop.get("const")
        if isinstance(const, str):
            known_kinds.append(const)
    if not known_kinds:
        return
    kind_schema = unknown.setdefault("properties", {}).setdefault("kind", {})
    kind_schema["not"] = {"enum": sorted(known_kinds)}


def load_schema() -> dict[str, Any]:
    """In-package JSON 파일에서 스키마를 로드한다 (네트워크 불필요).

    jsonschema 소비자·정적 검증 도구의 1차 접근 경로. 공개 URL 이 다운되어도
    패키지 사용자에게 영향 없음.

    Raises:
        FileNotFoundError: 패키지에 스키마 JSON 이 포함되지 않았을 때
            (maturin include 설정 누락 또는 빌드 불완전).
    """

    resource = files("rhwp.ir").joinpath("schema").joinpath(_PACKAGED_SCHEMA_NAME)
    if not resource.is_file():
        raise FileNotFoundError(
            f"Packaged schema not found at {resource!s}. "
            "Regenerate via `python -m rhwp.ir.schema > python/rhwp/ir/schema/hwp_ir_v1.json` "
            "and ensure [tool.maturin] include covers it."
        )
    return json.loads(resource.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import sys

    # ^ `python -m rhwp.ir.schema` → stdout 으로 스키마 출력. 리다이렉트 사용:
    #   python -m rhwp.ir.schema > python/rhwp/ir/schema/hwp_ir_v1.json
    json.dump(export_schema(), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
