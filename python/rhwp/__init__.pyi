"""rhwp — HWP/HWPX parser and renderer (Korean word processor format)."""

__all__ = [
    "Document",
    "parse",
    "rhwp_core_version",
    "version",
]

def version() -> str:
    """rhwp Python 패키지 버전 (예: "0.1.0")."""
    ...

def rhwp_core_version() -> str:
    """rhwp Rust 코어 버전 (예: "0.7.3")."""
    ...

def parse(path: str) -> Document:
    """HWP5 또는 HWPX 파일을 파싱하여 Document 반환.

    Args:
        path: HWP 또는 HWPX 파일 경로.

    Returns:
        파싱된 Document.

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때.
        PermissionError: 파일 접근 권한이 없을 때.
        OSError: 그 외 I/O 오류.
        ValueError: 파일 포맷이 유효하지 않을 때.
    """
    ...

class Document:
    """파싱된 HWP/HWPX 문서.

    직접 생성자를 호출하거나 :func:`parse` 를 사용할 수 있다.
    """

    section_count: int
    """섹션 수."""

    paragraph_count: int
    """전체 섹션에 걸친 총 문단 수."""

    page_count: int
    """페이지네이션 후 총 페이지 수."""

    def __init__(self, path: str) -> None:
        """HWP/HWPX 파일 경로로부터 파싱.

        Raises:
            FileNotFoundError: 파일이 존재하지 않을 때.
            PermissionError: 파일 접근 권한이 없을 때.
            OSError: 그 외 I/O 오류.
            ValueError: 파일 포맷이 유효하지 않을 때.
        """
        ...

    def extract_text(self) -> str:
        """전체 문서의 텍스트를 개행으로 연결해 반환 (빈 문단 제외)."""
        ...

    def paragraphs(self) -> list[str]:
        """모든 문단의 텍스트 리스트 (빈 문단 포함, len == paragraph_count)."""
        ...

    def render_svg(self, page: int) -> str:
        """특정 페이지를 SVG 문자열로 렌더링.

        Args:
            page: 0-based 페이지 인덱스.

        Raises:
            ValueError: 페이지 인덱스가 범위를 벗어났거나 렌더링 실패 시.
        """
        ...

    def render_all_svg(self) -> list[str]:
        """모든 페이지를 SVG 문자열 리스트로 렌더링 (len == page_count).

        Raises:
            ValueError: 렌더링 실패.
        """
        ...

    def export_svg(self, output_dir: str, prefix: str | None = None) -> list[str]:
        """모든 페이지를 SVG 파일로 저장.

        Args:
            output_dir: 출력 디렉토리 (자동 생성).
            prefix: 파일명 접두사 (기본 "page"). 다중 페이지 시 `{prefix}_{NNN}.svg`,
                단일 페이지 시 `{prefix}.svg`.

        Returns:
            생성된 파일 경로 리스트.

        Raises:
            OSError: 디렉토리 생성 또는 파일 쓰기 실패.
            ValueError: 렌더링 실패.
        """
        ...

    def render_pdf(self) -> bytes:
        """전체 문서를 PDF 바이트로 렌더링 (usvg + pdf-writer 경로).

        Raises:
            ValueError: SVG 렌더링 또는 PDF 변환 실패.
        """
        ...

    def export_pdf(self, output_path: str) -> int:
        """문서를 PDF 파일로 저장.

        Returns:
            저장된 바이트 수.

        Raises:
            OSError: 파일 쓰기 실패.
            ValueError: 렌더링 실패.
        """
        ...

    def __repr__(self) -> str: ...
