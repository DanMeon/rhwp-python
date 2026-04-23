"""에러 전파 검증 — FileNotFoundError / ValueError (크로스플랫폼 안전)."""

from pathlib import Path

import pytest
import rhwp


class TestFileNotFound:
    # ^ FileNotFoundError 는 OSError 서브클래스. 메시지는 OS 마다 다르므로 타입만 검증.
    #   (macOS/Linux: "No such file...", Windows: "The system cannot find...")

    def test_parse_raises_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            rhwp.parse("/nonexistent/path/to/nothing.hwp")

    def test_constructor_raises_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            rhwp.Document("/nonexistent/path/to/nothing.hwp")


class TestInvalidFormat:
    def test_garbage_bytes_raises_valueerror(self, tmp_path: Path) -> None:
        garbage = tmp_path / "garbage.hwp"
        garbage.write_bytes(b"NOT A REAL HWP FILE" * 100)
        with pytest.raises(ValueError, match="parse failed"):
            rhwp.parse(str(garbage))

    def test_empty_file_raises_valueerror(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.hwp"
        empty.write_bytes(b"")
        with pytest.raises(ValueError):
            rhwp.parse(str(empty))

    def test_constructor_empty_file(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.hwp"
        empty.write_bytes(b"")
        with pytest.raises(ValueError):
            rhwp.Document(str(empty))
