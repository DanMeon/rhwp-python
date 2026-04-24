"""HWP → Document IR (Pydantic HwpDocument) 변환 + 블록 순회 + JSON 직렬화 시연.

Document IR 은 구역/단락/표/셀을 계층 구조로 보존하며, 표는 cells 배열 + HTML
+ 평문 3중 표현을 병기한다. 병합된 빈 셀은 ``role="layout"`` 으로 자동 태깅된다.

사용법:
    python examples/04_document_ir.py path/to/your/file.hwp
    python examples/04_document_ir.py path/to/your/file.hwp --limit 20
    python examples/04_document_ir.py path/to/your/file.hwp --out ir.json

설치:
    pip install "rhwp-python[examples]"
"""

from pathlib import Path as PathLibPath

import rhwp
import typer
from rhwp.ir.nodes import ParagraphBlock, TableBlock, UnknownBlock


def main(
    path: PathLibPath = typer.Argument(
        PathLibPath("external/rhwp/samples/table-vpos-01.hwpx"),
        exists=False,
        help="HWP 또는 HWPX 파일 경로 (기본값은 submodule 샘플 — 표가 9개 포함됨)",
    ),
    limit: int = typer.Option(15, "--limit", "-n", help="미리보기할 블록 최대 개수"),
    out: PathLibPath = typer.Option(
        None,
        "--out",
        "-o",
        help="IR 전체를 JSON 파일로 저장 (예: ir.json)",
    ),
) -> None:
    """Document IR 구조를 탐색하고 선택적으로 JSON 으로 덤프한다."""
    if not path.exists():
        typer.echo(f"파일이 없습니다: {path}", err=True)
        raise typer.Exit(code=1)

    doc = rhwp.parse(str(path))
    ir = doc.to_ir()

    # * 문서 요약
    typer.echo("=" * 60)
    typer.echo("[문서 메타]")
    typer.echo("=" * 60)
    typer.echo(f"  schema:     {ir.schema_name} v{ir.schema_version}")
    typer.echo(f"  sections:   {len(ir.sections)}")
    typer.echo(f"  body:       {len(ir.body)} 블록 (top-level)")

    # * 블록 타입 분포 (recurse=True 로 중첩 표 내부까지)
    type_counts: dict[str, int] = {}
    layout_cells = 0
    for block in ir.iter_blocks(scope="body", recurse=True):
        type_counts[type(block).__name__] = type_counts.get(type(block).__name__, 0) + 1
        if isinstance(block, TableBlock):
            layout_cells += sum(1 for c in block.cells if c.role == "layout")

    typer.echo("\n[블록 분포 — recurse=True]")
    for name, cnt in sorted(type_counts.items()):
        typer.echo(f"  {name:20s} {cnt}")
    if layout_cells:
        typer.echo(f"  {'layout cells':20s} {layout_cells}  (병합된 비의미 셀)")

    # * 블록 리스트 미리보기
    typer.echo("\n" + "=" * 60)
    typer.echo(f"[body 미리보기 — 최대 {limit} 블록]")
    typer.echo("=" * 60)
    for i, block in enumerate(ir.iter_blocks(scope="body")):
        if i >= limit:
            typer.echo(f"  ... ({len(ir.body) - limit} more)")
            break
        prov = f"s={block.prov.section_idx} p={block.prov.para_idx}"
        if isinstance(block, ParagraphBlock):
            text = block.text[:60].replace("\n", "⏎")
            typer.echo(f"  [P  {prov}] {text!r}")
        elif isinstance(block, TableBlock):
            cap = f" caption={block.caption!r}" if block.caption else ""
            typer.echo(f"  [T  {prov}] {block.rows}x{block.cols} cells={len(block.cells)}{cap}")
            # ^ 첫 행만 간단 덤프
            first_row = [c for c in block.cells if c.row == 0]
            for c in first_row[:4]:
                snippet = block.text.split("\n")[0][:50]
                typer.echo(f"      cell(0,{c.col}) role={c.role}  row1={snippet!r}")
                break  # first row 한 줄만
        elif isinstance(block, UnknownBlock):
            typer.echo(f"  [?  {prov}] kind={block.kind!r} (forward-compat)")

    # * 첫 TableBlock 의 HTML 미리보기
    first_table = next((b for b in ir.iter_blocks(scope="body") if isinstance(b, TableBlock)), None)
    if first_table:
        typer.echo("\n" + "=" * 60)
        typer.echo(f"[첫 표의 HTML — HtmlRAG 호환, {first_table.rows}x{first_table.cols}]")
        typer.echo("=" * 60)
        typer.echo(first_table.html)

    # * 선택: JSON 파일로 덤프
    if out is not None:
        json_str = doc.to_ir_json(indent=2)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json_str, encoding="utf-8")
        typer.echo(f"\n전체 IR 을 {out} 에 저장 ({len(json_str):,} 바이트).")

    typer.echo(
        "\n다음 단계: `rhwp.ir.schema.export_schema()` 또는 `load_schema()` 로 JSON Schema 확보."
    )
    typer.echo("  또는 `examples/05_langchain_ir_blocks.py` 로 LangChain ir-blocks 모드 시연.")


if __name__ == "__main__":
    typer.run(main)
