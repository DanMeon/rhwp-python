# Roadmap

rhwp-python 의 버전별 로드맵 + **활성 spec 인덱스 SSOT**. 모든 spec 의 Status / GA / Target 을 본 페이지에서 추적한다. 문서 관리 정책은 [docs/CONVENTIONS.md](../CONVENTIONS.md) 참조.

본 문서는 Living — 자유 갱신.

## 현재 상태 (2026-06-21)

- **v0.1.0 / v0.1.1** — Frozen, PyPI 배포 완료
- **v0.2.0** — Frozen, Document IR v1 GA (2026-04-25)
- **v0.3.0** — Frozen, Phase 2 (IR 확장 + `rhwp-py` CLI) GA (2026-04-28)
- **v0.3.1** — Frozen, inline 컨트롤 마커 char offset 출고 GA (2026-05-03)
- **v0.3.2** — Frozen, UTF-16 → codepoint 변환 SSOT 단일화 GA (2026-05-03)
- **v0.4.0** — Frozen, IR view 렌더러 (Markdown / HTML) GA (2026-05-05)
- **v0.5.0** — Frozen, MCP server (`rhwp-mcp`) GA (2026-05-06)
- **v0.5.1** — Frozen, MCP tool 출력 schema 강타입화 GA (2026-05-07)
- **v0.6.0** — Frozen, 페이지 PNG 렌더링 (VLM 입력) GA (2026-05-10)
- **v0.7.0** — Frozen, HWPX writeback baseline (parse → HWPX round-trip, 텍스트·문단 보존) GA (2026-06-04)
- **v0.8.0** — Frozen, HWPX writeback round-trip 검증 (`verify_hwpx_roundtrip` + 보존 boundary 를 상류 `diff_documents` 검증 필드로 확대) GA (2026-06-21)

## 활성 spec 인덱스

각 row 는 spec 한 개 + 짝이 되는 design research (있으면). Status 는 [CONVENTIONS.md § 문서 수명 4 분류](../CONVENTIONS.md) 정의에 따름.

| 버전 | Status | Roadmap spec | Design research (ADR) |
|---|---|---|---|
| v0.1.0 / v0.1.1 | Frozen | [v0.1.0/rhwp-python.md](v0.1.0/rhwp-python.md) | — |
| v0.2.0 | Frozen | [v0.2.0/ir.md](v0.2.0/ir.md) | [design/v0.2.0/ir-research.md](../design/v0.2.0/ir-research.md) |
| v0.3.0 (IR 확장) | Frozen | [v0.3.0/ir-expansion.md](v0.3.0/ir-expansion.md) | [design/v0.3.0/ir-expansion-research.md](../design/v0.3.0/ir-expansion-research.md) |
| v0.3.0 (CLI) | Frozen | [v0.3.0/cli.md](v0.3.0/cli.md) | [design/v0.3.0/cli-research.md](../design/v0.3.0/cli-research.md) |
| v0.3.1 (IR marker char offset) | Frozen | [v0.3.1/ir-marker-char-offset.md](v0.3.1/ir-marker-char-offset.md) | [design/v0.3.1/ir-marker-char-offset-research.md](../design/v0.3.1/ir-marker-char-offset-research.md) |
| v0.3.2 (IR upstream UTF-16 helper) | Frozen | [v0.3.2/ir-upstream-utf16-helper.md](v0.3.2/ir-upstream-utf16-helper.md) | [design/v0.3.2/ir-upstream-utf16-helper-research.md](../design/v0.3.2/ir-upstream-utf16-helper-research.md) |
| v0.4.0 (view 렌더러) | Frozen | [v0.4.0/view-renderer.md](v0.4.0/view-renderer.md) | [design/v0.4.0/view-renderer-research.md](../design/v0.4.0/view-renderer-research.md) |
| v0.5.0 (MCP server) | Frozen | [v0.5.0/mcp.md](v0.5.0/mcp.md) | [design/v0.5.0/mcp-research.md](../design/v0.5.0/mcp-research.md) |
| v0.5.1 (MCP typed output) | Frozen | [v0.5.1/mcp-typed-output.md](v0.5.1/mcp-typed-output.md) | [design/v0.5.1/mcp-typed-output-research.md](../design/v0.5.1/mcp-typed-output-research.md) |
| v0.6.0 (png-vlm-render) | Frozen | [v0.6.0/png-vlm-render.md](v0.6.0/png-vlm-render.md) | [design/v0.6.0/png-vlm-render-research.md](../design/v0.6.0/png-vlm-render-research.md) |
| v0.7.0 (hwpx-writeback-baseline) | Frozen | [v0.7.0/hwpx-writeback-baseline.md](v0.7.0/hwpx-writeback-baseline.md) | [design/v0.7.0/hwpx-writeback-baseline-research.md](../design/v0.7.0/hwpx-writeback-baseline-research.md) |
| v0.8.0 (hwpx-writeback-expansion) | Frozen | [v0.8.0/hwpx-writeback-expansion.md](v0.8.0/hwpx-writeback-expansion.md) | [design/v0.8.0/hwpx-writeback-expansion-research.md](../design/v0.8.0/hwpx-writeback-expansion-research.md) |
| v0.8.1 (hwpx-fidelity-sync) | Draft | [v0.8.1/hwpx-fidelity-sync.md](v0.8.1/hwpx-fidelity-sync.md) | [design/v0.8.1/hwpx-fidelity-sync-research.md](../design/v0.8.1/hwpx-fidelity-sync-research.md) |

## 미착수 작업 계획

본 섹션은 결정 미정 narrative — `vX.Y.Z` 디렉토리가 아직 없는 minor 들의 의도/스코프. 작업 시점이 가까워지면 `/new-spec <version> <topic>` 으로 정식 spec 으로 promote.

### v0.8.0 ~ v1.0.0 — JSON IR → HWP 역생성 (확장)

선행 조건: v0.7.0 (HWPX writeback baseline) GA 완료 (2026-06-04) — Frozen spec [v0.7.0/hwpx-writeback-baseline.md](v0.7.0/hwpx-writeback-baseline.md) 가 텍스트·문단 round-trip + HWP5 → HWPX 변환을 연다. 본 라인은 그 위에 표·이미지·수식 의미 보존과 HWP5 binary 출력을 쌓는 확장 단계.

상류 `edwardkim/rhwp` 는 표·그림까지 직렬화 코드를 보유하나 보존 검증의 성숙도가 포맷별로 비대칭이다. HWPX round-trip 의미 보존 검증 (IrDiff) 은 아직 골격 카운트 수준 (섹션·문단·리소스 카운트 비교, 문단 텍스트 내용 미비교) 이고, 반대로 HWP5 binary writeback (`serialize_hwp`) 은 한컴 호환 byte-perfect 수준으로 성숙했다 (v0.7.0 GA 직전 상류 sync `1899ef9 → ce45231c` 에서 확인). 따라서 v0.8.0 (HWPX 표·그림 의미 보존) 은 상류 IrDiff 확장에 lock-step 으로 묶이고, v0.9.0 (HWP5 binary writeback) 은 상류 성숙도상 앞당김 여지가 있다 — 분할 순서는 착수 시점 상류 진척으로 재확인. 사용자가 IR 을 편집해 새 HWP/HWPX 를 생성하는 mutable IR 빌더 API 는 v1.0 API 안정 선언 시점에 통합 검토.

범위:
- IR → **HWPX** 역직렬화 (HWPX 가 XML 기반이라 먼저)
- IR → **HWP5** 역직렬화 (OLE 컴파운드 파일 — 더 복잡)
- 왕복 (round-trip) 보장 테스트: parse → IR → write → parse 결과가 의미적으로 동일
- Python API: `Document.to_hwpx_bytes()` / `Document.export_hwpx(path)` (v0.7.0~), `Document.to_hwp_bytes()` / `Document.export_hwp(path)` (v0.9.0~)

릴리스 분할:

| 버전 | 범위 |
|---|---|
| v0.8.0 | HWPX writeback 확장 (표·이미지·수식) |
| v0.9.0 | HWP5 writeback baseline |
| v1.0.0 | HWP5 writeback 확장 + API 안정 선언 |

SemVer 0.x.y 단계에서 minor 는 단조 증가. v1.0.0 은 API 안정 선언과 함께 별도 도달 — round-trip 무결성 / breaking change 부재 / 외부 검토 기준 충족 시점에 도달.

1.0 안정화 기준:
- HWPX 왕복 무결성 ≥ 99% (bytewise 는 불가능, 의미적 동등성 기준)
- HWP5 왕복 최소 가능
- Breaking change 없이 12개월 유지된 API
- 공식 메인테이너 (또는 공신력 있는 커뮤니티) 검토 통과

비범위:
- 완전한 레이아웃 보존 (폰트 embedding 미포함 상태의 재생성) — 뷰어 차이 허용
- 매크로·폼 필드·OLE 임베딩 — HWP 독자 확장 기능은 장기 과제

### IR 노출 확장 — 상류 파싱 정보의 미노출 갭 해소

2026-07-07 갭 조사 결과: 상류 `model` 은 완전한 문서 모델 (글자·문단 스타일, 문서 메타데이터, 하이퍼링크, 차트 데이터 등) 을 파싱하나 우리 IR 은 텍스트 + 기본 구조만 노출한다. 대부분 상류가 이미 파싱해 두므로 얇은 wire-through 로 메울 수 있다 (신규 파싱 구현 아님). v0.3.0 "IR 확장" 라인의 연장이며 위 writeback 라인과 독립 축. 버전 분할은 착수 시점 `/new-spec` 으로 확정.

우선순위 (RAG/문서이해 가치 × 노력):

- **티어 1 — 값싼 노출, 즉시 가치** (상류 파싱 완료, 현재 IR 이 버림): 문서 메타데이터 (제목·작성자·작성일, 현재 항상 빈값) · 글자 스타일 확장 (크기·색상·폰트, 현재 굵기/기울임/밑줄/취소선 4개만) · 문단 속성 (정렬·들여쓰기·줄간격, 현재 head_type/level 만) · 하이퍼링크 URL (현재 컨트롤 통째 미노출).
- **티어 2 — 중간 노력, 큰 기능**: 차트 구조화 데이터 추출 (`series{name, values}` — 읽기 전용, 현재 SVG 렌더만) · 페이지 단위 Markdown / 레이아웃 인식 텍스트 (RAG 청킹, 현재 전체 IR 순서 `extract_text` 만) · HWP5 binary writeback (`to_hwp`, 상류 준비 완료 — 위 writeback 라인과 합류).
- **티어 3 — 상황별**: 표 스타일 (제목행 반복·테두리·셀 정렬) · 그림 기하·효과·alt-text · 전체 텍스트 검색 · HTML 렌더.

양식개체 (체크박스/버튼) 는 위 비범위의 "폼 필드" 와 일치 — 장기 과제로 유지. 편집 commands (에디터 지향) 와 문서 생성 빌더는 "문서 이해·변환" 정체성 밖.

> 과거 GA 완료된 minor (v0.1.x ~ v0.3.0) 의 historical record 는 [v0.1.0/rhwp-python.md](v0.1.0/rhwp-python.md) / [v0.2.0/ir.md](v0.2.0/ir.md) / [v0.3.0/ir-expansion.md](v0.3.0/ir-expansion.md) / [v0.3.0/cli.md](v0.3.0/cli.md) 가 보유.

## 구현 / 검증 로그 (Frozen)

작업 완료 후 로그. Frozen — 변경 없음.

| 버전 | 구현 로그 | 검증 리포트 |
|---|---|---|
| v0.1.0 | [implementation/v0.1.0/migration.md](../implementation/v0.1.0/migration.md) | [verification/v0.1.0/spinoff-review.md](../verification/v0.1.0/spinoff-review.md) |
| v0.2.0 | [implementation/v0.2.0/stages/](../implementation/v0.2.0/stages/) (S1~S5) | — |
| v0.3.0 | [implementation/v0.3.0/stages/](../implementation/v0.3.0/stages/) (S1~S4) + [aparse-cleanup.md](../implementation/v0.3.0/aparse-cleanup.md) | — |
| v0.3.1 | [implementation/v0.3.1/migration.md](../implementation/v0.3.1/migration.md) | — |
| v0.4.0 | [implementation/v0.4.0/migration.md](../implementation/v0.4.0/migration.md) | — |
| v0.5.0 | [implementation/v0.5.0/stages/](../implementation/v0.5.0/stages/) (S1~S5) | — |
| v0.5.1 | [implementation/v0.5.1/migration.md](../implementation/v0.5.1/migration.md) | — |
| v0.6.0 | [implementation/v0.6.0/migration.md](../implementation/v0.6.0/migration.md) | — |
| v0.7.0 | [implementation/v0.7.0/migration.md](../implementation/v0.7.0/migration.md) | — |
| v0.8.0 | [implementation/v0.8.0/migration.md](../implementation/v0.8.0/migration.md) | — |

## 원칙

- **MINOR 단위 증분** — 기능 한 덩어리씩. 깨지는 변경 없이 누적
- **Phase 경계는 breaking 없음** — Phase 1 → 2 이동해도 기존 API 유지
- **Rust 코어 커밋 고정** — 각 릴리스는 `external/rhwp` submodule 의 특정 upstream commit 에 pin. 코어 업그레이드 시 CHANGELOG 에 명시
- **버전은 git tag 와 동일한 `v` prefix** — 디렉토리명·문서명 일관성
- **Spec 라이프사이클**: Draft → (GA) → Frozen → (필요 시) → Superseded by …. 상세: [CONVENTIONS.md § 새 spec 추가 절차](../CONVENTIONS.md)
- **Stage 분할 기준** — 단일 세션/수일 규모는 단일 `migration.md` 로. 여러 주 이상·의존성 추적이 필요한 대형 작업 (v0.2.0 IR 구현 등) 만 `stages/stage-N.md` 로 분할

## 연표 (대략)

| 버전 | 대략 목표 시점 |
|---|---|
| v0.1.0 / v0.1.1 | 2026 Q2 (GA 완료) |
| v0.2.0 | 2026 Q2 (GA 완료) |
| v0.3.0 | 2026 Q3 |
| v0.4.0 ~ v0.6.0 | 2027 |
| v1.0.0 | 2027+ |

타임라인은 **유동적** — 상류 `edwardkim/rhwp` 진척과 커뮤니티 수요에 따라 변경.

## 비범위 (영구)

- rhwp 코어 자체의 수정 — 모두 업스트림 PR 로
- HWP/HWPX 가 아닌 다른 한국 문서 포맷 (ARX / GUL 등) — rhwp 범위 밖
- OCR / 이미지 내 텍스트 인식 — 별도 도메인
