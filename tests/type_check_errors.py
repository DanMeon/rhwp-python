"""타입 스텁 검증 — 의도된 오류. pyright 가 4건 검출해야 함.

pytest 는 test_*.py 패턴만 수집하므로 이 파일은 자동 제외된다.
pyright 전용: `uv run pyright tests/type_check_errors.py` → `4 errors` 기대.
"""

import rhwp


def intentional_type_errors() -> None:
    # ^ 아래 4줄 각각이 pyright 오류 1건을 유발해야 함 (총 4 errors)
    rhwp.parse(123)  # expect: reportArgumentType (int → str 파라미터)

    doc = rhwp.parse("a.hwp")

    n: int = doc.extract_text()  # expect: reportAssignmentType (str → int)
    s: str = doc.section_count  # expect: reportAssignmentType (int → str)
    doc.nonexistent_method()  # expect: reportAttributeAccessIssue

    print(n, s)
