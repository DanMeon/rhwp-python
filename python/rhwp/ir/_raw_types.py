"""rhwp.ir._raw_types — Rust `#[derive(IntoPyObject)]` 출력의 TypedDict 미러.

``src/ir.rs`` 의 ``RawDocument`` / ``RawParagraph`` / ``RawTable`` / ``RawCell`` /
``RawCharRun`` struct 가 Python 에 PyDict 로 출고되는데, 그 dict 의 key 구조를
정적 타입으로 고정한다.

### 왜 TypedDict 인가

Rust 계약이 이미 구조를 보장하므로 Python 레이어에서의 재검증은 이중 비용이다.
TypedDict 는 런타임 비용 0, 정적 typing 만으로 ``raw["row"]`` key 오타를 pyright
가 컴파일 타임에 검출한다. 검증 기반 모델 (런타임 validation) 과 비교해 nested
구조에서 수 배 빠르므로 internal raw record 용도에 적합하다.

### 계약 동기화

필드 추가/이름 변경은 ``src/ir.rs`` 의 struct 와 **양방향으로** 갱신해야 한다 —
Rust 는 출고 key 를, 이 파일은 소비 key 를 정의한다.
"""

from typing import TypedDict


class RawCharRun(TypedDict):
    """``src/ir.rs::RawCharRun`` 과 1:1 대응."""

    start_cp: int
    end_cp: int
    char_shape_id: int
    bold: bool
    italic: bool
    underline: bool
    strikethrough: bool


class RawCell(TypedDict):
    """``src/ir.rs::RawCell``. ``paragraphs`` 는 셀 내부 문단 (중첩 표 자연 지원)."""

    row: int
    col: int
    row_span: int
    col_span: int
    is_header: bool
    paragraphs: list["RawParagraph"]


class RawTable(TypedDict):
    """``src/ir.rs::RawTable``. ``rows``/``cols`` 는 upstream 원값 그대로 (보정 없음)."""

    rows: int
    cols: int
    cells: list[RawCell]
    caption: str | None


class RawParagraph(TypedDict):
    """``src/ir.rs::RawParagraph``.

    ``tables`` 는 문단의 ``controls`` 중 ``Control::Table`` 만 추출된 리스트.
    ``section_idx`` / ``para_idx`` 는 외부 paragraph 의 위치 — 셀 내부 문단이라도
    외부 표가 속한 문단의 값을 공유한다 (Provenance 계약).
    """

    section_idx: int
    para_idx: int
    text: str
    char_runs: list[RawCharRun]
    tables: list[RawTable]


class RawDocument(TypedDict):
    """``src/ir.rs::RawDocument`` — ``to_ir`` Rust→Python 경계의 루트."""

    source_uri: str | None
    section_count: int
    paragraphs: list[RawParagraph]
