"""HWP/HWPX를 SVG + PDF로 렌더링하는 예제.

사용법:
    python examples/02_render_svg_pdf.py path/to/file.hwp
    python examples/02_render_svg_pdf.py path/to/file.hwp --output-dir ./out
    python examples/02_render_svg_pdf.py path/to/file.hwp --no-pdf

설치:
    pip install "rhwp-python[examples]"
"""

from pathlib import Path as PathLibPath

import rhwp
import typer


def main(
    path: PathLibPath = typer.Argument(..., help="HWP 또는 HWPX 파일 경로"),
    output_dir: PathLibPath = typer.Option(
        PathLibPath("./render_output"), "--output-dir", "-o", help="출력 디렉토리"
    ),
    no_svg: bool = typer.Option(False, "--no-svg", help="SVG 렌더링 건너뛰기"),
    no_pdf: bool = typer.Option(False, "--no-pdf", help="PDF 렌더링 건너뛰기"),
    prefix: str = typer.Option("page", "--prefix", help="SVG 파일명 접두사"),
) -> None:
    """HWP/HWPX를 파싱한 뒤 페이지별 SVG + 전체 PDF를 생성."""
    if not path.exists():
        typer.echo(f"파일이 없습니다: {path}", err=True)
        raise typer.Exit(code=1)

    output_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(f"파싱 중: {path}")
    doc = rhwp.parse(str(path))
    typer.echo(f"  페이지 수: {doc.page_count}")

    if not no_svg:
        typer.echo(f"\n[SVG] {output_dir}/{prefix}_*.svg")
        svg_paths = doc.export_svg(str(output_dir), prefix=prefix)
        for p in svg_paths:
            size_kb = PathLibPath(p).stat().st_size / 1024
            typer.echo(f"  {p}  ({size_kb:.1f} KB)")

    if not no_pdf:
        pdf_path = output_dir / "document.pdf"
        typer.echo(f"\n[PDF] {pdf_path}")
        # ^ rhwp 코어가 stdout 에 [DEBUG_TAB_POS] / LAYOUT_OVERFLOW 로그를 찍을 수 있음
        byte_size = doc.export_pdf(str(pdf_path))
        typer.echo(f"  {byte_size:,} bytes ({byte_size / 1024 / 1024:.2f} MB)")

    typer.echo(f"\n완료. 결과물: {output_dir}/")


if __name__ == "__main__":
    typer.run(main)
