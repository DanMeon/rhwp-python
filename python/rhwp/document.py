"""rhwp.document — Rust ``_Document`` 위의 Python wrapper.

``rhwp._rhwp._Document`` 는 PyO3 가 노출하는 Rust thin core 이고, 본 파일의
``Document`` 는 그것을 감싸는 Python-side wrapper 다. 사용자-대면 API 는 여기
서만 변경한다 — Rust 재빌드 없이 메서드/문서화/타입 힌트를 진화시킬 수 있다.

구조:
- ``__init__(path)`` : 새 경로로 파싱해 ``_Document`` 생성
- ``from_bytes(data)`` : 메모리 bytes 로부터 생성 (네트워크 fetch, async 경로 등)
- ``_from_rust(cls, rust_doc)`` : 내부 factory — ``__init__`` 우회
- ``__slots__`` : 메모리/속성 접근 비용 최소화 + 의도치 않은 속성 추가 차단

### Threading 제약 (매우 중요)

``_Document`` 는 ``#[pyclass(unsendable)]`` 로 **생성 스레드에 묶여 있다**.
이는 upstream ``DocumentCore`` 가 내부 ``RefCell`` 캐시를 가지기 때문 —
여러 스레드에서 동시 접근 시 RefCell borrow panic 이 발생한다.

따라서:
- ``asyncio.to_thread(doc.to_ir)`` 금지 — 스레드 경계 넘으면 panic
- ``asyncio.to_thread(rhwp.parse, path)`` 금지 — 마찬가지
- ``rhwp.Document`` 인스턴스는 생성한 스레드 에서만 사용

async 환경에서 파일 I/O 를 non-blocking 으로 처리하려면 :func:`aparse` 사용 —
``aiofiles`` 가 파일 읽기만 async 로 수행하고, 파싱 (``Document.from_bytes``) 은
호출 스레드에서 동기 실행한다. 파싱 구간의 GIL 은 Rust ``py.detach`` 가 해제.

### IR 캐싱

``doc.to_ir()`` 결과는 Rust ``_Document`` 의 ``OnceCell`` 이 캐시한다 — 같은
Document 객체에 대해 ``to_ir()`` 재호출은 동일 인스턴스를 반환 (identity 보존).
"""

from typing import TYPE_CHECKING

from rhwp._rhwp import _Document

if TYPE_CHECKING:
    from rhwp.ir.nodes import HwpDocument


class Document:
    """파싱된 HWP / HWPX 문서.

    직접 생성자를 호출하거나 :func:`rhwp.parse` / :func:`rhwp.aparse` /
    :meth:`Document.from_bytes` 중 하나를 사용한다. 생성된 Document 는 생성
    스레드에서만 사용해야 한다 (upstream RefCell 제약).

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때.
        PermissionError: 파일 접근 권한이 없을 때.
        OSError: 그 외 I/O 오류.
        ValueError: 파일 포맷이 유효하지 않을 때.
    """

    __slots__ = ("_inner",)

    def __init__(self, path: str) -> None:
        self._inner: _Document = _Document(path)

    @classmethod
    def _from_rust(cls, rust_doc: _Document) -> "Document":
        """내부 factory — ``__init__`` 우회로 기존 ``_Document`` 인스턴스를 감싼다.

        사용자 코드에서 호출할 일은 없다 (underscore prefix).
        """
        obj = cls.__new__(cls)
        obj._inner = rust_doc
        return obj

    @classmethod
    def from_bytes(cls, data: bytes, *, source_uri: str | None = None) -> "Document":
        """메모리 bytes 로부터 Document 구성.

        파일 경로가 아닌 bytes 에서 파싱해야 하는 경우 (네트워크 fetch,
        in-memory archive 등) 또는 :func:`aparse` 의 async 파일 I/O 내부
        경로에서 사용. 파싱은 GIL 해제 구간에서 실행 (``py.detach``).

        Args:
            data: HWP 또는 HWPX binary 바이트.
            source_uri: IR ``source.uri`` 로 전파될 출처 식별자 (기본 ``None``).
                file path, URL, 또는 ``mem://{hash}`` 같은 custom scheme 허용.

        Raises:
            ValueError: binary 포맷이 유효하지 않을 때.
        """
        return cls._from_rust(_Document.from_bytes(data, source_uri=source_uri))

    # * Properties — Rust getter 위임

    @property
    def source_uri(self) -> str | None:
        """생성자에 전달된 원본 경로. IR ``source.uri`` 와 동일 값 — IR 을
        생성하지 않고도 출처 조회 가능."""
        return self._inner.source_uri

    @property
    def section_count(self) -> int:
        """섹션 수."""
        return self._inner.section_count

    @property
    def paragraph_count(self) -> int:
        """전체 섹션에 걸친 총 문단 수."""
        return self._inner.paragraph_count

    @property
    def page_count(self) -> int:
        """페이지네이션 후 총 페이지 수."""
        return self._inner.page_count

    # * Text / structure access

    def extract_text(self) -> str:
        """전체 문서의 텍스트를 개행으로 연결해 반환 (빈 문단 제외)."""
        return self._inner.extract_text()

    def paragraphs(self) -> list[str]:
        """모든 문단의 텍스트 리스트 (빈 문단 포함, ``len == paragraph_count``)."""
        return self._inner.paragraphs()

    # * Document IR

    def to_ir(self) -> "HwpDocument":
        """문서를 Document IR (``HwpDocument``) 로 변환.

        첫 호출 시 문서 트리를 순회하며 IR 을 구성한다. 결과는 Rust ``_Document``
        내부에 캐시되어 재호출은 동일 인스턴스를 즉시 반환한다 — ``frozen=True``
        모델이므로 수정 시 ``ValidationError``. 독립 사본이 필요하면
        ``ir.model_copy(deep=True)`` 를 사용한다.

        Raises:
            pydantic.ValidationError: 내부 구조가 스키마와 불일치할 때 (상류 버그 시).
            ImportError: ``rhwp.ir.nodes`` 모듈 로드 실패 시.
        """
        return self._inner.to_ir()

    def to_ir_json(self, *, indent: int | None = None) -> str:
        """IR 을 JSON 문자열로 반환. ``to_ir()`` 캐시를 공유한다.

        Args:
            indent: 들여쓰기 칸 수 (None 이면 한 줄 직렬화).

        Raises:
            pydantic.ValidationError: IR 변환 중 스키마 불일치가 발생할 때.
        """
        return self._inner.to_ir_json(indent=indent)

    # * Rendering

    def render_svg(self, page: int) -> str:
        """특정 페이지를 SVG 문자열로 렌더링.

        Args:
            page: 0-based 페이지 인덱스.

        Raises:
            ValueError: 페이지 인덱스가 범위를 벗어났거나 렌더링 실패 시.
        """
        return self._inner.render_svg(page)

    def render_all_svg(self) -> list[str]:
        """모든 페이지를 SVG 문자열 리스트로 렌더링 (``len == page_count``).

        Raises:
            ValueError: 렌더링 실패.
        """
        return self._inner.render_all_svg()

    def export_svg(self, output_dir: str, prefix: str | None = None) -> list[str]:
        """모든 페이지를 SVG 파일로 저장.

        Args:
            output_dir: 출력 디렉토리 (자동 생성).
            prefix: 파일명 접두사 (기본 ``"page"``). 다중 페이지 시
                ``{prefix}_{NNN}.svg``, 단일 페이지 시 ``{prefix}.svg``.

        Returns:
            생성된 파일 경로 리스트.

        Raises:
            OSError: 디렉토리 생성 또는 파일 쓰기 실패.
            ValueError: 렌더링 실패.
        """
        return self._inner.export_svg(output_dir, prefix)

    def render_pdf(self) -> bytes:
        """전체 문서를 PDF 바이트로 렌더링.

        Raises:
            ValueError: SVG 렌더링 또는 PDF 변환 실패.
        """
        return self._inner.render_pdf()

    def export_pdf(self, output_path: str) -> int:
        """문서를 PDF 파일로 저장.

        Returns:
            저장된 바이트 수.

        Raises:
            OSError: 파일 쓰기 실패.
            ValueError: 렌더링 실패.
        """
        return self._inner.export_pdf(output_path)

    def __repr__(self) -> str:
        return repr(self._inner)


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
    return Document(path)


async def aparse(path: str) -> Document:
    """:func:`parse` 의 async 변형 — 파일 읽기만 async, 파싱은 sync.

    ``#[pyclass(unsendable)]`` 제약 상 Document 는 스레드 경계를 넘을 수 없다.
    따라서 ``asyncio.to_thread(parse, path)`` 패턴은 panic 을 일으킨다. 대신
    ``aiofiles`` 로 **파일 I/O 만** async 로 수행하고, bytes 파싱은 호출 스레드
    에서 동기 실행 (GIL 은 Rust ``py.detach`` 가 해제). 이 경로는 Document
    인스턴스를 이벤트 루프 스레드에 유지하므로 panic 이 없다.

    ``aiofiles`` 는 optional dependency — ``pip install rhwp-python[async]`` 또는
    ``pip install aiofiles``. 미설치 시 ``ImportError``.

    Args:
        path: HWP 또는 HWPX 파일 경로.

    Returns:
        파싱된 Document. 호출 스레드에 묶인다.

    Raises:
        ImportError: ``aiofiles`` 미설치.
        FileNotFoundError: 파일이 존재하지 않을 때.
        PermissionError: 파일 접근 권한이 없을 때.
        OSError: 그 외 I/O 오류.
        ValueError: 파일 포맷이 유효하지 않을 때.
    """
    try:
        import aiofiles
    except ImportError as e:
        raise ImportError(
            "rhwp.aparse requires aiofiles. "
            "Install via `pip install rhwp-python[async]` or `pip install aiofiles`."
        ) from e

    async with aiofiles.open(path, "rb") as f:
        data = await f.read()
    return Document.from_bytes(data, source_uri=path)
