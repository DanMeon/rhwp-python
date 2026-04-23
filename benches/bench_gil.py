"""GIL 해제 효과 측정 — 단일 vs 멀티스레드 parse / render_pdf 처리 시간.

`py.detach` 를 적용한 `parse()` 와 `render_pdf()` 가 `ThreadPoolExecutor` 에서
실제 병렬 실행되는지 (GIL 해제 작동) 확인.

`#[pyclass(unsendable)]` 제약: `Document` 객체는 생성된 스레드에서만 유효.
벤치는 각 워커가 parse → 추출 / render_pdf → bytes 까지 완결 후 int 반환 (현업 패턴).
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import rhwp

# ^ 경로: <REPO_ROOT>/benches/bench_gil.py
#   샘플은 rhwp 코어 submodule (external/rhwp) 내부 samples/ 디렉터리에 있음
REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = REPO_ROOT / "external" / "rhwp" / "samples"


def parse_task(path: str) -> int:
    # ^ 워커 스레드 내에서 Document 생성/소멸 완결. int 만 반환
    doc = rhwp.parse(path)
    return doc.paragraph_count


def pdf_task(path: str) -> int:
    # ^ parse + render_pdf 를 한 워커에서 처리. bytes 길이만 반환
    doc = rhwp.parse(path)
    pdf = doc.render_pdf()
    return len(pdf)


def bench(task, file_list: list[str], workers: int, repeats: int) -> float:
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        if workers == 1:
            results = [task(p) for p in file_list]
        else:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                results = list(ex.map(task, file_list))
        times.append(time.perf_counter() - start)
        assert len(results) == len(file_list)
    return min(times)


def main() -> None:
    files = [
        str(SAMPLES / "aift.hwp"),
        str(SAMPLES / "table-vpos-01.hwpx"),
        str(SAMPLES / "tac-img-02.hwpx"),
    ]
    parse_workload = files * 3  # ^ 9 태스크 (3 파일 × 3회 반복)

    print(f"시스템 코어 수: {os.cpu_count()}")
    print(f"rhwp 버전: {rhwp.version()}  /  rhwp core: {rhwp.rhwp_core_version()}")
    print()
    print("=" * 72)
    print("Parse 벤치마크 — 9개 파일 (aift + table-vpos + tac-img, 각 3회)")
    print("=" * 72)
    print(f"{'워커 수':<12} {'처리 시간':<15} {'단일 대비':<15} {'이상적 가속':<15}")
    print("-" * 72)

    baseline = bench(parse_task, parse_workload, workers=1, repeats=3)
    print(f"{'1 (순차)':<12} {f'{baseline * 1000:.0f}ms':<15} {'1.00x':<15} {'1.00x':<15}")

    for workers in [2, 4, 8]:
        t = bench(parse_task, parse_workload, workers=workers, repeats=3)
        speedup = baseline / t
        ideal = min(workers, len(parse_workload))
        print(
            f"{workers:<12} {f'{t * 1000:.0f}ms':<15} "
            f"{f'{speedup:.2f}x':<15} {f'{ideal:.0f}x (이상치)':<15}"
        )

    print()
    print("=" * 72)
    print("PDF 렌더링 벤치마크 — 3개 문서 (parse + render_pdf 워커 내 완결)")
    print("=" * 72)
    print(f"{'워커 수':<12} {'처리 시간':<15} {'단일 대비':<15}")
    print("-" * 72)

    pdf_baseline = bench(pdf_task, files, workers=1, repeats=2)
    print(f"{'1 (순차)':<12} {f'{pdf_baseline * 1000:.0f}ms':<15} {'1.00x':<15}")

    for workers in [2, 3]:
        t = bench(pdf_task, files, workers=workers, repeats=2)
        speedup = pdf_baseline / t
        print(f"{workers:<12} {f'{t * 1000:.0f}ms':<15} {f'{speedup:.2f}x':<15}")


if __name__ == "__main__":
    main()
