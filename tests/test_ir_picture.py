"""tests/test_ir_picture.py — Stage S1 PictureBlock + ImageRef + bytes_for_image.

ir-expansion.md §S1 테스트 항목 매핑:

- PictureBlock + ImageRef 직렬화 왕복 — 모델 단독 검증
- mapper 의 bin:// URI 합성 / mime 매핑 / broken reference 폴백
- ``Document.bytes_for_image`` 헬퍼 — bin_data_id 파싱, broken reference,
  unsupported scheme, lookup 실패 케이스
- 실제 샘플에 picture 가 있다면 lookup 성공까지 검증 (lenient — 샘플에 없으면 skip)
"""

import pytest
import rhwp
from pydantic import ValidationError
from rhwp.ir._mapper import _build_picture_block, _mime_for_extension
from rhwp.ir._raw_types import RawImageRef, RawPicture
from rhwp.ir.nodes import (
    HwpDocument,
    ImageRef,
    PictureBlock,
    Provenance,
)

# * 모델 단독 — ImageRef


def test_image_ref_roundtrip():
    img = ImageRef(uri="bin://1", mime_type="image/png", width=640, height=480, dpi=96)
    assert ImageRef.model_validate_json(img.model_dump_json()) == img


def test_image_ref_required_fields():
    """uri / mime_type 만 필수 — 나머지는 None 폴백."""
    img = ImageRef(uri="bin://1", mime_type="image/jpeg")
    assert img.width is None
    assert img.height is None
    assert img.dpi is None


def test_image_ref_extra_forbidden():
    with pytest.raises(ValidationError):
        ImageRef.model_validate({"uri": "bin://1", "mime_type": "image/png", "extra": True})


def test_image_ref_frozen():
    img = ImageRef(uri="bin://1", mime_type="image/png")
    with pytest.raises(ValidationError):
        img.uri = "bin://2"  # type: ignore[misc]


# * 모델 단독 — PictureBlock


def _prov(section_idx: int = 0, para_idx: int = 0) -> Provenance:
    return Provenance(section_idx=section_idx, para_idx=para_idx)


def test_picture_block_roundtrip_with_image():
    pic = PictureBlock(
        image=ImageRef(uri="bin://7", mime_type="image/png"),
        description="회로도",
        prov=_prov(),
    )
    reloaded = PictureBlock.model_validate_json(pic.model_dump_json())
    assert reloaded == pic
    assert reloaded.image is not None
    assert reloaded.image.uri == "bin://7"


def test_picture_block_broken_reference():
    """image=None 은 명시적 broken reference 표현 — 왕복도 보존."""
    pic = PictureBlock(image=None, description=None, prov=_prov())
    reloaded = PictureBlock.model_validate_json(pic.model_dump_json())
    assert reloaded == pic
    assert reloaded.image is None


def test_picture_block_kind_is_picture():
    pic = PictureBlock(prov=_prov())
    assert pic.kind == "picture"


def test_picture_block_extra_forbidden():
    with pytest.raises(ValidationError):
        PictureBlock.model_validate(
            {"kind": "picture", "prov": {"section_idx": 0, "para_idx": 0}, "extra": "x"}
        )


def test_picture_block_routes_via_discriminator():
    """본문에 PictureBlock dict 를 넣으면 picture variant 로 라우팅."""
    raw = {
        "kind": "picture",
        "image": {"uri": "bin://3", "mime_type": "image/jpeg"},
        "prov": {"section_idx": 0, "para_idx": 5},
    }
    doc = HwpDocument.model_validate({"body": [raw]})
    blk = doc.body[0]
    assert isinstance(blk, PictureBlock)
    assert blk.image is not None
    assert blk.image.mime_type == "image/jpeg"


# * mapper — mime 매핑


@pytest.mark.parametrize(
    "ext,expected",
    [
        ("png", "image/png"),
        ("PNG", "image/png"),  # ^ 대소문자 무시
        ("jpg", "image/jpeg"),
        ("jpeg", "image/jpeg"),
        ("bmp", "image/bmp"),
        ("gif", "image/gif"),
        ("tiff", "image/tiff"),
        ("tif", "image/tiff"),
        ("wmf", "image/x-wmf"),
        ("emf", "image/x-emf"),
        ("svg", "image/svg+xml"),
        ("webp", "image/webp"),
    ],
)
def test_mime_mapping_known_extensions(ext: str, expected: str):
    assert _mime_for_extension(ext) == expected


def test_mime_mapping_unknown_falls_back():
    assert _mime_for_extension("xyz") == "application/octet-stream"


def test_mime_mapping_none_falls_back():
    assert _mime_for_extension(None) == "application/octet-stream"


# * mapper — RawPicture → PictureBlock


def _raw_picture(
    *,
    section_idx: int = 0,
    para_idx: int = 0,
    bin_data_id: int = 1,
    extension: str | None = "png",
    has_content: bool = True,
    description: str | None = None,
    image: bool = True,
) -> RawPicture:
    img: RawImageRef | None = None
    if image:
        img = RawImageRef(bin_data_id=bin_data_id, extension=extension, has_content=has_content)
    return RawPicture(
        section_idx=section_idx,
        para_idx=para_idx,
        image=img,
        description=description,
    )


def test_build_picture_block_with_known_extension():
    blk = _build_picture_block(_raw_picture(bin_data_id=4, extension="png"))
    assert blk.image is not None
    assert blk.image.uri == "bin://4"
    assert blk.image.mime_type == "image/png"
    assert blk.prov.section_idx == 0
    assert blk.prov.para_idx == 0
    assert blk.prov.char_start is None
    assert blk.prov.char_end is None


def test_build_picture_block_unknown_extension_falls_back():
    blk = _build_picture_block(_raw_picture(extension="xyz"))
    assert blk.image is not None
    assert blk.image.mime_type == "application/octet-stream"


def test_build_picture_block_no_extension_falls_back():
    blk = _build_picture_block(_raw_picture(extension=None))
    assert blk.image is not None
    assert blk.image.mime_type == "application/octet-stream"


def test_build_picture_block_broken_reference_routes_to_none():
    blk = _build_picture_block(_raw_picture(image=False))
    assert blk.image is None


def test_build_picture_block_preserves_description():
    blk = _build_picture_block(_raw_picture(description="<그림 1> 회로도"))
    assert blk.description == "<그림 1> 회로도"


# * Document.bytes_for_image — 에러 경로 (broken/scheme/parse)


def test_bytes_for_image_raises_on_broken_reference(parsed_hwp: rhwp.Document):
    """image=None 인 PictureBlock 은 ValueError."""
    pic = PictureBlock(image=None, prov=_prov())
    with pytest.raises(ValueError, match="broken reference"):
        parsed_hwp.bytes_for_image(pic)


def test_bytes_for_image_raises_on_unsupported_scheme(parsed_hwp: rhwp.Document):
    pic = PictureBlock(
        image=ImageRef(uri="data:image/png;base64,iVBOR=", mime_type="image/png"),
        prov=_prov(),
    )
    with pytest.raises(ValueError, match="bin://"):
        parsed_hwp.bytes_for_image(pic)


def test_bytes_for_image_raises_on_invalid_uri(parsed_hwp: rhwp.Document):
    pic = PictureBlock(
        image=ImageRef(uri="bin://not_a_number", mime_type="image/png"), prov=_prov()
    )
    with pytest.raises(ValueError, match="invalid bin://"):
        parsed_hwp.bytes_for_image(pic)


def test_bytes_for_image_raises_on_out_of_range(parsed_hwp: rhwp.Document):
    pic = PictureBlock(
        image=ImageRef(uri="bin://99999", mime_type="image/png"),  # ^ u16 초과
        prov=_prov(),
    )
    with pytest.raises(ValueError, match="out of u16 range"):
        parsed_hwp.bytes_for_image(pic)


def test_bytes_for_image_raises_on_lookup_miss(parsed_hwp: rhwp.Document):
    """존재하지 않는 bin_data_id (u16 범위 안) 도 ValueError."""
    pic = PictureBlock(
        image=ImageRef(uri="bin://65000", mime_type="image/png"),
        prov=_prov(),
    )
    with pytest.raises(ValueError, match="not found"):
        parsed_hwp.bytes_for_image(pic)


# * 실제 샘플 — 이미지가 있으면 lookup 성공, 없으면 skip


def _find_pictures(ir: HwpDocument) -> list[PictureBlock]:
    return [b for b in ir.iter_blocks(scope="all", recurse=True) if isinstance(b, PictureBlock)]


def test_real_sample_picture_block_kind_is_picture(parsed_hwp: rhwp.Document):
    """샘플에 그림이 있을 경우 PictureBlock 으로 노출, 없으면 skip."""
    ir = parsed_hwp.to_ir()
    pictures = _find_pictures(ir)
    if not pictures:
        pytest.skip("aift.hwp 샘플에 그림 컨트롤 없음 — 검증 항목 없음")
    for pic in pictures:
        assert pic.kind == "picture"
        assert isinstance(pic.prov, Provenance)


def test_real_sample_picture_uri_is_bin_scheme(parsed_hwp: rhwp.Document):
    ir = parsed_hwp.to_ir()
    pictures_with_image = [p for p in _find_pictures(ir) if p.image is not None]
    if not pictures_with_image:
        pytest.skip("샘플에 image=None 이 아닌 PictureBlock 없음")
    for pic in pictures_with_image:
        assert pic.image is not None
        assert pic.image.uri.startswith("bin://"), pic.image.uri
        # ^ bin_data_id 파싱 가능
        bid = int(pic.image.uri[len("bin://") :])
        assert bid >= 1


def test_real_sample_bytes_for_image_returns_nonempty(parsed_hwp: rhwp.Document):
    """샘플의 PictureBlock 중 lookup 가능한 것이 있으면 bytes 가 비어있지 않아야 함."""
    ir = parsed_hwp.to_ir()
    candidates = [p for p in _find_pictures(ir) if p.image is not None]
    if not candidates:
        pytest.skip("샘플에 lookup 가능한 PictureBlock 없음")
    found_any = False
    for pic in candidates:
        try:
            data = parsed_hwp.bytes_for_image(pic)
        except ValueError:
            # ^ 특정 picture 는 Link/Storage 라 lookup 실패할 수 있음 — 다음 후보로
            continue
        assert isinstance(data, bytes)
        assert len(data) > 0
        found_any = True
        break
    if not found_any:
        pytest.skip("모든 PictureBlock 이 Embedding 이 아니거나 content 누락")
