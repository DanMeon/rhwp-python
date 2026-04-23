"""실제 HWP/HWPX 파일을 파싱하고 텍스트를 추출하는 기본 예제.

사용법:
    python examples/01_parse_basic.py path/to/your/file.hwp
    python examples/01_parse_basic.py --preview 200 ~/Documents/report.hwp

설치:
    pip install "rhwp-python[examples]"
"""

from pathlib import Path as PathLibPath

import rhwp
import typer


def main(
    path: PathLibPath = typer.Argument(
        PathLibPath("external/rhwp/samples/aift.hwp"),
        exists=False,  # ^ 기본값이 submodule 경로라 clone 여부에 따라 없을 수 있음 — 직접 확인
        help="HWP 또는 HWPX 파일 경로 (기본값은 submodule 샘플)",
    ),
    preview_chars: int = typer.Option(500, "--preview", "-p", help="본문 프리뷰 문자 수"),
) -> None:
    """HWP/HWPX 파일을 파싱하고 메타데이터 + 텍스트 프리뷰를 출력."""
    if not path.exists():
        typer.echo(f"파일이 없습니다: {path}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"파싱 중: {path}  ({path.stat().st_size / 1024:.1f} KB)")
    doc = rhwp.parse(str(path))

    # * 메타데이터
    typer.echo("\n[메타데이터]")
    typer.echo(f"  섹션 수:   {doc.section_count}")
    typer.echo(f"  문단 수:   {doc.paragraph_count}")
    typer.echo(f"  페이지 수: {doc.page_count}")
    typer.echo(f"  rhwp 버전: {rhwp.version()}  /  core: {rhwp.rhwp_core_version()}")

    # * 전체 텍스트 추출 (빈 문단 제외, "\n" 으로 join)
    full_text = doc.extract_text()
    typer.echo(f"\n[본문 — 총 {len(full_text):,} 문자]")
    preview = full_text[:preview_chars]
    typer.echo(preview + ("..." if len(full_text) > preview_chars else ""))

    # * 문단 리스트 (빈 문단 포함)
    paragraphs = doc.paragraphs()
    non_empty = [p for p in paragraphs if p.strip()]
    typer.echo(f"\n[문단 통계] 전체 {len(paragraphs)} / 비어있지 않음 {len(non_empty)}")


if __name__ == "__main__":
    typer.run(main)
