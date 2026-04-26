"""rhwp.ir._mapper — Rust raw dict → ``HwpDocument`` 합성.

``src/ir.rs`` 의 ``#[derive(IntoPyObject)]`` struct 들이 내보내는 dict 트리를
입력으로 받아 ``rhwp.ir.nodes`` 의 모델 트리를 구성한다. 도메인 규칙 (cell role
분류, HTML 직렬화, mime 매핑, inline run 폴백 정책) 은 여기서 결정하여 IR 진화 시
maturin rebuild 를 회피한다.

Rust 출력 계약은 ``src/ir.rs`` 의 struct field 이름과 1:1 대응 — 구조는
``rhwp.ir._raw_types`` 의 TypedDict 가 정적으로 고정한다. key 변경 시 양쪽
동기화 필요. underscore prefix 모듈명은 "rhwp-python 내부 사용 전용" 관례를
따른다 (소비자는 ``rhwp.ir.nodes`` 의 공개 IR 모델만 사용).
"""

from typing import Final, Literal

from rhwp.ir._raw_types import (
    RawCell,
    RawCharRun,
    RawDocument,
    RawImageRef,
    RawParagraph,
    RawPicture,
    RawTable,
)
from rhwp.ir.nodes import (
    Block,
    DocumentSource,
    Furniture,
    HwpDocument,
    ImageRef,
    InlineRun,
    ParagraphBlock,
    PictureBlock,
    Provenance,
    Section,
    TableBlock,
    TableCell,
)

# ^ 상류 BinData.extension → 표준 mime type. 누락/미지 확장자는 폴백.
#   Embedding 만 채워지므로 PDF 등 비-이미지 확장자는 등장하지 않음.
_MIME_BY_EXT: Final[dict[str, str]] = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "bmp": "image/bmp",
    "gif": "image/gif",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "wmf": "image/x-wmf",
    "emf": "image/x-emf",
    "svg": "image/svg+xml",
    "webp": "image/webp",
}
_FALLBACK_MIME: Final = "application/octet-stream"


def build_hwp_document(raw: RawDocument) -> HwpDocument:
    """Rust raw dict → Pydantic ``HwpDocument``.

    ``src/document.rs`` 의 ``to_ir`` 에서 호출되며 반환값은 Rust ``ir_cache`` 에
    저장된다 — 따라서 동일 인스턴스 재사용 계약 (``test_to_ir_caches_same_object``)
    과 ``frozen=True`` 를 모두 만족한다.
    """
    source = DocumentSource(uri=raw["source_uri"]) if raw["source_uri"] is not None else None
    sections = [Section(section_idx=i) for i in range(raw["section_count"])]

    body: list[Block] = []
    for raw_para in raw["paragraphs"]:
        body.extend(_flatten_paragraph(raw_para))

    page_headers: list[Block] = []
    for raw_hdr in raw["headers"]:
        page_headers.extend(_flatten_paragraph(raw_hdr))
    page_footers: list[Block] = []
    for raw_ftr in raw["footers"]:
        page_footers.extend(_flatten_paragraph(raw_ftr))

    return HwpDocument(
        source=source,
        sections=sections,
        body=body,
        furniture=Furniture(
            page_headers=page_headers,
            page_footers=page_footers,
        ),
    )


def _flatten_paragraph(raw_para: RawParagraph) -> list[Block]:
    """Paragraph → ParagraphBlock + 표/그림 파생 블록.

    파생 블록들은 외부 paragraph 의 ``(section_idx, para_idx)`` Provenance 를
    공유 — iter_blocks 소비자가 동일 문단 파생임을 식별 가능. ``_build_table_cell``
    이 본 함수를 재호출해 셀 내부 문단까지 평탄화 — 중첩 표 (표 안의 표) 를
    자연스럽게 지원.

    출고 순서는 ParagraphBlock → tables → pictures (S1 단순 정책).
    HWP controls 의 원래 시각 순서 보존은 v0.4.0+ 에서 ``order: int`` 필드 검토.
    """
    blocks: list[Block] = [_build_paragraph_block(raw_para)]
    for raw_table in raw_para["tables"]:
        blocks.append(_build_table_block(raw_para, raw_table))
    for raw_pic in raw_para["pictures"]:
        blocks.append(_build_picture_block(raw_pic))
    return blocks


def _build_paragraph_block(raw_para: RawParagraph) -> ParagraphBlock:
    text = raw_para["text"]
    return ParagraphBlock(
        text=text,
        inlines=_build_inline_runs(text, raw_para["char_runs"]),
        prov=Provenance(
            section_idx=raw_para["section_idx"],
            para_idx=raw_para["para_idx"],
            char_start=0,
            char_end=len(text),
        ),
    )


def _build_inline_runs(text: str, char_runs: list[RawCharRun]) -> list[InlineRun]:
    """``char_runs`` 는 Rust 에서 codepoint range 로 해소된 상태로 입고된다.

    비어있거나 유효 런이 0개면 전체 텍스트를 style-less 단일 런으로 폴백 —
    손상 파일 대비. 첫 런이 0 부터 시작하지 않으면 앞쪽 prefix 를 style-less
    런으로 prepend (HWP 관례상 정상 파일은 0 부터 시작).
    """
    if not text:
        return []
    if not char_runs:
        return [InlineRun(text=text)]

    runs: list[InlineRun] = []
    first_start = char_runs[0]["start_cp"]
    if first_start > 0:
        prefix = text[:first_start]
        if prefix:
            runs.append(InlineRun(text=prefix))

    for run in char_runs:
        slice_text = text[run["start_cp"] : run["end_cp"]]
        if not slice_text:
            continue
        runs.append(
            InlineRun(
                text=slice_text,
                bold=run["bold"],
                italic=run["italic"],
                underline=run["underline"],
                strikethrough=run["strikethrough"],
                raw_style_id=run["char_shape_id"],
            )
        )

    if not runs:
        return [InlineRun(text=text)]
    return runs


def _build_table_block(raw_para: RawParagraph, raw_table: RawTable) -> TableBlock:
    cols = raw_table["cols"]
    cells = [_build_table_cell(c, cols) for c in raw_table["cells"]]
    return TableBlock(
        rows=raw_table["rows"],
        cols=cols,
        cells=cells,
        html=_table_to_html(raw_table),
        text=_table_to_text(raw_table),
        caption=raw_table["caption"],
        prov=Provenance(
            section_idx=raw_para["section_idx"],
            para_idx=raw_para["para_idx"],
            char_start=None,
            char_end=None,
        ),
    )


def _build_table_cell(raw_cell: RawCell, table_cols: int) -> TableCell:
    cell_blocks: list[Block] = []
    for inner_para in raw_cell["paragraphs"]:
        cell_blocks.extend(_flatten_paragraph(inner_para))

    return TableCell(
        row=raw_cell["row"],
        col=raw_cell["col"],
        row_span=raw_cell["row_span"],
        col_span=raw_cell["col_span"],
        grid_index=raw_cell["row"] * table_cols + raw_cell["col"],
        role=_cell_role(raw_cell),
        blocks=cell_blocks,
    )


def _cell_role(
    raw_cell: RawCell,
) -> Literal["data", "column_header", "row_header", "layout"]:
    """HWP cell 속성 → DocLayNet role 어휘.

    - ``is_header=True`` → ``"column_header"`` (HWP 는 row/column 구분 없음)
    - 병합 셀이면서 텍스트 전부 공백 → ``"layout"`` (구조 유지용 비의미 셀)
    - 그 외 → ``"data"``
    """
    if raw_cell["is_header"]:
        return "column_header"
    merged = raw_cell["row_span"] > 1 or raw_cell["col_span"] > 1
    if merged and all(not p["text"].strip() for p in raw_cell["paragraphs"]):
        return "layout"
    return "data"


def _build_picture_block(raw_pic: RawPicture) -> PictureBlock:
    """RawPicture → PictureBlock.

    image=None 케이스: 상류 Picture 가 bin_data_id=0 (미할당) 으로 들어왔거나
    bin_data_list 에서 lookup 실패 — broken reference 로 그대로 보존한다 (소비자가
    ``picture.image is None`` 으로 분기 가능).
    """
    image: ImageRef | None = None
    raw_img = raw_pic["image"]
    if raw_img is not None:
        image = ImageRef(
            uri=_image_uri(raw_img),
            mime_type=_mime_for_extension(raw_img["extension"]),
        )
    return PictureBlock(
        image=image,
        description=raw_pic["description"],
        prov=Provenance(
            section_idx=raw_pic["section_idx"],
            para_idx=raw_pic["para_idx"],
            char_start=None,
            char_end=None,
        ),
    )


def _image_uri(raw_img: RawImageRef) -> str:
    """기본 ``bin://<bin_data_id>`` URI — embedded/external 모드는 v0.4.0+ opt-in."""
    return f"bin://{raw_img['bin_data_id']}"


def _mime_for_extension(extension: str | None) -> str:
    """확장자 → 표준 mime. 누락/미지 시 ``application/octet-stream`` 폴백.

    HWP BinData 는 Embedding 타입에만 ``extension`` 을 채운다 — Link 타입은
    extension=None 이라 폴백. 사용자가 mime 정확도가 필요하면 magic byte 검증을
    별도 적용한다 (예: ``Document.bytes_for_image`` 로 raw 받아 imghdr/PIL).
    """
    if extension is None:
        return _FALLBACK_MIME
    return _MIME_BY_EXT.get(extension.lower(), _FALLBACK_MIME)


def _table_to_html(raw_table: RawTable) -> str:
    """Table → HTML 문자열 (HtmlRAG 호환, ir.md §테이블 표현).

    Attribute 순서 고정 (rowspan → colspan) 으로 dedup hash 안정성 보장 —
    "동일 패키지 버전 내" 스코프 (ir.md §2 결정사항).
    """
    parts: list[str] = ["<table>"]
    current_row: int | None = None
    for cell in raw_table["cells"]:
        if current_row != cell["row"]:
            if current_row is not None:
                parts.append("</tr>")
            parts.append("<tr>")
            current_row = cell["row"]
        tag = "th" if cell["is_header"] else "td"
        attrs = ""
        if cell["row_span"] > 1:
            attrs += f' rowspan="{cell["row_span"]}"'
        if cell["col_span"] > 1:
            attrs += f' colspan="{cell["col_span"]}"'
        escaped = _escape_html(_cell_plain_text(cell, " "))
        parts.append(f"<{tag}{attrs}>{escaped}</{tag}>")
    if current_row is not None:
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


def _table_to_text(raw_table: RawTable) -> str:
    r"""Table → 평문. 행은 ``\n``, 셀은 ``\t`` 구분. 단순 검색·diff 용 폴백."""
    lines: list[str] = []
    current_row: int | None = None
    current_cells: list[str] = []
    for cell in raw_table["cells"]:
        if current_row != cell["row"]:
            if current_row is not None:
                lines.append("\t".join(current_cells))
            current_cells = []
            current_row = cell["row"]
        current_cells.append(_cell_plain_text(cell, " "))
    if current_row is not None:
        lines.append("\t".join(current_cells))
    return "\n".join(lines)


def _cell_plain_text(raw_cell: RawCell, para_sep: str) -> str:
    return para_sep.join(p["text"] for p in raw_cell["paragraphs"] if p["text"])


def _escape_html(s: str) -> str:
    """HTML 속성·텍스트 escape.

    ``&`` 를 반드시 **최초** 치환한다 — 이후 치환이 만들어내는 ``&amp;``, ``&lt;``,
    ``&gt;``, ``&quot;`` 의 ``&`` 가 재치환되면 이중 escape (``&amp;lt;``) 가
    발생하기 때문. ``<``, ``>``, ``"`` 간 순서는 교환 가능. Python 표준
    ``html.escape`` 는 ``'`` 까지 escape 해 기존 IR 출력과 달라지므로 사용 불가.
    """
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
