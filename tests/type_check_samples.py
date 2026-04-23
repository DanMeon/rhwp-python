"""타입 스텁 검증 — 정상 케이스. pyright 가 오류 0건을 보고해야 함.

pytest 는 test_*.py 패턴만 수집하므로 이 파일은 자동 제외된다.
pyright 전용: `uv run pyright tests/type_check_samples.py`
"""

import rhwp


def valid_usage() -> None:
    pkg_ver: str = rhwp.version()
    core_ver: str = rhwp.rhwp_core_version()
    print(pkg_ver, core_ver)

    doc: rhwp.Document = rhwp.parse("a.hwp")
    sections: int = doc.section_count
    paras: int = doc.paragraph_count
    pages: int = doc.page_count
    text: str = doc.extract_text()
    plist: list[str] = doc.paragraphs()
    repr_str: str = repr(doc)
    print(sections, paras, pages, len(text), len(plist), repr_str)


def direct_constructor() -> None:
    doc = rhwp.Document("a.hwp")
    text: str = doc.extract_text()
    print(text)


def rendering_usage() -> None:
    # ^ Stage 3: SVG/PDF 렌더링 타입 검증
    doc = rhwp.parse("a.hwp")

    svg: str = doc.render_svg(0)
    svgs: list[str] = doc.render_all_svg()
    written: list[str] = doc.export_svg("/tmp/out", prefix="page")
    written_default: list[str] = doc.export_svg("/tmp/out")

    pdf: bytes = doc.render_pdf()
    size: int = doc.export_pdf("/tmp/out.pdf")

    print(len(svg), len(svgs), len(written), len(written_default), len(pdf), size)
