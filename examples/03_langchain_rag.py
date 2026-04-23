"""HWP → LangChain Document → 텍스트 스플리터 → (선택) 벡터 DB 인제스트.

실제 RAG 파이프라인의 "HWP 로딩 → 청킹" 단계까지 시연. 임베딩/벡터 DB/LLM
쿼리는 사용자 스택(OpenAI/Claude/Chroma/Qdrant 등)에 맡김.

사용법:
    python examples/03_langchain_rag.py path/to/file.hwp
    python examples/03_langchain_rag.py path/to/file.hwp --chunk-size 1000 --chunk-overlap 100

설치:
    pip install "rhwp-python[langchain,examples]" langchain-text-splitters
"""

from pathlib import Path as PathLibPath

import typer
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rhwp.integrations.langchain import HwpLoader


def main(
    path: PathLibPath = typer.Argument(
        PathLibPath("external/rhwp/samples/aift.hwp"),
        exists=False,
        help="HWP 또는 HWPX 파일 경로 (기본값은 submodule 샘플)",
    ),
    chunk_size: int = typer.Option(500, "--chunk-size", help="청크 최대 문자 수"),
    chunk_overlap: int = typer.Option(50, "--chunk-overlap", help="청크 간 오버랩 문자 수"),
) -> None:
    """HwpLoader 의 single / paragraph / lazy_load 3가지 모드 + 청킹 시연."""
    if not path.exists():
        typer.echo(f"파일이 없습니다: {path}", err=True)
        raise typer.Exit(code=1)

    # * 1) single 모드 — 문서 전체를 Document 하나로
    typer.echo("=" * 60)
    typer.echo("[single mode] 문서 전체를 Document 1개로 로드")
    typer.echo("=" * 60)
    single_docs = HwpLoader(str(path)).load()
    assert len(single_docs) == 1
    d = single_docs[0]
    typer.echo(f"  본문 길이: {len(d.page_content):,} 자")
    typer.echo(f"  메타데이터: {d.metadata}")

    # * 2) paragraph 모드 — 빈 문단 제외, 문단 1개당 Document 1개
    typer.echo("\n" + "=" * 60)
    typer.echo("[paragraph mode] 문단 단위로 Document 생성")
    typer.echo("=" * 60)
    para_docs = HwpLoader(str(path), mode="paragraph").load()
    typer.echo(f"  Document 수: {len(para_docs)}")
    if para_docs:
        typer.echo(f"  첫 문단: {para_docs[0].page_content[:100]}...")
        typer.echo(f"  paragraph_index 예시: {para_docs[0].metadata.get('paragraph_index')}")

    # * 3) lazy_load — 메모리 O(1) peak 로 순회
    typer.echo("\n" + "=" * 60)
    typer.echo("[lazy_load] 하나씩 yield — 대용량 문서에서 peak memory 절약")
    typer.echo("=" * 60)
    count = 0
    for _ in HwpLoader(str(path), mode="paragraph").lazy_load():
        count += 1
    typer.echo(f"  순회된 Document 수: {count}")

    # * 4) 청킹 — RecursiveCharacterTextSplitter 에 바로 투입
    typer.echo("\n" + "=" * 60)
    typer.echo(
        f"[chunking] RecursiveCharacterTextSplitter (size={chunk_size}, overlap={chunk_overlap})"
    )
    typer.echo("=" * 60)
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_documents(single_docs)
    typer.echo(f"  chunk 수: {len(chunks)}")
    if chunks:
        typer.echo(f"  첫 chunk 길이: {len(chunks[0].page_content)} 자")

    typer.echo("\n이 시점에서 각 chunk 를 임베딩 → 벡터 DB 에 저장하면 RAG 준비 완료.")
    typer.echo("예: chunks → OpenAIEmbeddings → Chroma.from_documents(chunks, embedding)")


if __name__ == "__main__":
    typer.run(main)
