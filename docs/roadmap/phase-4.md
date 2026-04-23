# Phase 4 — JSON IR → HWP 역생성

**대상 버전**: v0.7.0 ~ v1.0.0 (안정화 + writeback 지원)
**선행 조건**: Phase 3 (v0.6.0 까지) GA + rhwp Rust 코어의 HWP writer API 안정

## 목표

IR 을 축으로 한 양방향 변환 — 사용자가 IR 을 편집해 새 HWP/HWPX 를 생성할 수 있게 함.

## 외부 의존성

Phase 4 는 rhwp **Rust 코어의 쓰기 API 성숙도** 에 좌우됨. 업스트림 `edwardkim/rhwp` 가 HWP writer 를 안정화해야 진행 가능.

- Phase 4 시작 전 업스트림 상태 재평가
- 필요 시 rhwp 코어에 writer PR 기여로 진입

## 범위

- IR → **HWPX** 역직렬화 (HWPX 가 XML 기반이라 먼저)
- IR → **HWP5** 역직렬화 (OLE 컴파운드 파일 — 더 복잡)
- 왕복 (round-trip) 보장 테스트: parse → IR → write → parse 결과가 의미적으로 동일
- Python API: `rhwp.write(ir, path)` / `rhwp.Document.from_ir(ir).save(path)`

## 릴리스 분할

| 버전 | 범위 |
|---|---|
| v0.7.0 | HWPX writeback baseline (단순 문서 왕복) |
| v0.8.0 | HWPX writeback 확장 (표·이미지·수식) |
| v0.9.0 | HWP5 writeback baseline |
| v1.0.0 | HWP5 writeback 확장 + API 안정 선언 |

## 1.0 안정화 기준

- HWPX 왕복 무결성 ≥ 99% (bytewise 는 불가능, 의미적 동등성 기준)
- HWP5 왕복 최소 가능
- Breaking change 없이 12개월 유지된 API
- 공식 메인테이너 (또는 공신력 있는 커뮤니티) 검토 통과

## 비범위

- 완전한 레이아웃 보존 (폰트 embedding 미포함 상태의 재생성) — 뷰어 차이 허용
- 매크로·폼 필드·OLE 임베딩 — HWP 독자 확장 기능은 장기 과제
