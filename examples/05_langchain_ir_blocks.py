"""HwpLoader(mode="ir-blocks") — 표는 HTML content, 단락은 text, Provenance 메타.

03 예제는 single/paragraph 모드 + 청킹만 다룬다. 본 예제는 ir-blocks 모드로
표 구조 (rowspan/colspan) 를 보존하면서 RAG 인덱스를 구성할 때 얻는 이점을
보여준다 — HtmlRAG 패턴에서 LLM 이 병합 셀의 의미를 읽을 수 있게 한다.

사용법:
    python examples/05_langchain_ir_blocks.py path/to/your/file.hwp
    python examples/05_langchain_ir_blocks.py path/to/your/file.hwp --kind-filter table

설치:
    pip install "rhwp-python[langchain,examples]"
"""

from pathlib import Path as PathLibPath

import typer
from rhwp.integrations.langchain import HwpLoader


def main(
    path: PathLibPath = typer.Argument(
        PathLibPath("external/rhwp/samples/table-vpos-01.hwpx"),
        exists=False,
        help="HWP 또는 HWPX 파일 경로 (기본값은 표 9개 포함 샘플)",
    ),
    kind_filter: str = typer.Option(
        "all",
        "--kind-filter",
        "-k",
        help="표시할 블록 종류: all | paragraph | table",
    ),
    limit: int = typer.Option(10, "--limit", "-n", help="표시할 Document 최대 개수"),
) -> None:
    """ir-blocks 모드의 Document 매핑을 단락/표 유형별로 미리본다."""
    if not path.exists():
        typer.echo(f"파일이 없습니다: {path}", err=True)
        raise typer.Exit(code=1)
    if kind_filter not in ("all", "paragraph", "table"):
        typer.echo(f"잘못된 --kind-filter: {kind_filter!r}", err=True)
        raise typer.Exit(code=1)

    docs = HwpLoader(str(path), mode="ir-blocks").load()

    # * 전체 요약
    by_kind: dict[str, int] = {}
    for d in docs:
        k = d.metadata.get("kind", "?")
        by_kind[k] = by_kind.get(k, 0) + 1

    typer.echo("=" * 60)
    typer.echo("[ir-blocks 모드 요약]")
    typer.echo("=" * 60)
    typer.echo(f"  총 Document 수: {len(docs)}")
    for k, v in sorted(by_kind.items()):
        typer.echo(f"    {k:12s} {v}")

    # * 종류별 미리보기
    if kind_filter == "all":
        to_show = docs
    else:
        to_show = [d for d in docs if d.metadata.get("kind") == kind_filter]

    typer.echo("\n" + "=" * 60)
    typer.echo(f"[Document 미리보기 — kind={kind_filter}, 최대 {limit}개]")
    typer.echo("=" * 60)

    for i, d in enumerate(to_show[:limit]):
        kind = d.metadata.get("kind", "?")
        prov = f"s={d.metadata.get('section_idx')} p={d.metadata.get('para_idx')}"
        typer.echo(f"\n[{i + 1}] kind={kind}  {prov}")

        if kind == "paragraph":
            typer.echo(f"    page_content: {d.page_content[:80]!r}")
            typer.echo(
                f"    char range:   [{d.metadata.get('char_start')}, {d.metadata.get('char_end')})"
            )
        elif kind == "table":
            rows, cols = d.metadata.get("rows"), d.metadata.get("cols")
            typer.echo(f"    shape:        {rows}x{cols}")
            typer.echo(f"    caption:      {d.metadata.get('caption')!r}")
            typer.echo(f"    HTML[:120]:   {d.page_content[:120]}")
            typer.echo(f"    text[:80]:    {d.metadata.get('text', '')[:80]!r}")

    if len(to_show) > limit:
        typer.echo(f"\n  ... ({len(to_show) - limit} more)")

    typer.echo("\n" + "=" * 60)
    typer.echo("RAG 팁: 표 Document 의 page_content 는 HTML 이라 LLM 이 rowspan/colspan 의")
    typer.echo("의미를 해석할 수 있다. 검색 색인에는 metadata['text'] (평문) 를 사용하고")
    typer.echo("LLM 프롬프트에 HTML 을 넘기는 dual-track RAG 가 손실 없이 동작한다.")


if __name__ == "__main__":
    typer.run(main)
