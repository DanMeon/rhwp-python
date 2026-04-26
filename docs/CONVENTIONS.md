# Documentation Conventions

본 프로젝트의 문서 관리 정책. **Spec-driven + immutable per-version** 패턴을 채택한다. 새 문서를 작성하거나 기존 문서를 수정하기 전 본 문서를 확인.

## 문서 수명 4 분류

| 분류 | 의미 | 갱신 정책 | 예시 |
|---|---|---|---|
| **Living** | 항상 최신 — 다른 문서의 위치 포인터 + 시간선 + 규칙 | 자유 갱신, 매 변경 시 손봐도 무방 | `docs/CONVENTIONS.md` (자체), `docs/roadmap/README.md`, `CHANGELOG.md`, `CLAUDE.md`, `README.md` |
| **Active** | 현재 진행 중 — 의도/스코프 수준의 진화하는 문서 | 큰 변경만, in-place 갱신 OK | `docs/roadmap/phase-N.md`, `docs/design/pyo3-bindings.md` (cross-version reference) |
| **Draft** | 작성 중인 spec — 해당 버전 GA 전까지 활발 갱신 | 버전 GA 전까지 자유 갱신, GA 후 Frozen 으로 전환 | `docs/roadmap/v0.3.0/*.md` (현재 v0.3.0 GA 전) |
| **Frozen** | GA 완료된 spec / 완료된 stage / 완료된 검증 | **변경 금지** — 오타·링크 수정만 in-place 허용. 큰 변경은 새 spec + supersede | `docs/roadmap/v0.2.0/ir.md` (v0.2.0 GA 완료), `docs/implementation/v0.2.0/stages/*.md` |

`Frozen` 은 [Rust RFC](https://rust-lang.github.io/rfcs/) / [Python PEP](https://peps.python.org/) 의 운영 모델. 결정의 historical record 가 보존되어 "왜 그렇게 설계됐는지" 가 명확해진다.

## Status 헤더 형식

`Living` 을 제외한 모든 spec 의 첫 헤더 직후에 metadata block 을 둔다:

```markdown
# <문서 제목>

**Status**: <Active | Draft | Frozen | Superseded by [link]> · **GA**: <vX.Y.Z> 또는 **Target**: <vX.Y.Z> · **Last updated**: YYYY-MM-DD

<본문 시작>
```

- **Status**: 현재 분류
- **GA** (Frozen 일 때): 어느 버전에서 GA 됐는지. **Target** (Draft 일 때): 어느 버전을 향한 작업인지. Active 면 둘 다 생략 가능
- **Last updated**: 본문에 의미 있는 변경이 있었던 날짜 (오타·링크 수정 제외)
- 모든 spec 변경 시 `Last updated` 만큼은 갱신

`Living` 문서는 정의상 항상 최신이므로 Status 헤더 없음. 대신 README 같은 인덱스가 다른 문서들의 Status 를 노출.

## 디렉토리별 정책

```
docs/
├── CONVENTIONS.md                    Living  — 본 문서. 정책 SSOT
├── roadmap/
│   ├── README.md                     Living  — 활성 spec 인덱스
│   ├── phase-{2,3,4}.md              Active  — Phase 의도/스코프 (구체 결정 미포함)
│   └── v<X.Y.Z>/<topic>.md           Draft → Frozen on GA — per-version spec
├── design/
│   ├── pyo3-bindings.md              Active  — 버전 무관 cross-version reference
│   └── v<X.Y.Z>/<topic>-research.md  Draft → Frozen on GA — ADR-style 결정 증거
├── implementation/
│   └── v<X.Y.Z>/...                  Frozen  — 완료된 stage 작업 로그
└── verification/
    └── v<X.Y.Z>/...                  Frozen  — 완료된 검증 리포트
```

### roadmap/

- `README.md` (Living) — 활성 spec 인덱스. 어느 spec 이 어느 버전을 향하는지의 SSOT
- `phase-N.md` (Active) — Phase 의 의도/스코프만. **구체 결정/미결 이슈는 두지 않음** — 그것들은 `vX.Y.Z/*.md` 의 영역. Phase 의 대상 버전이 바뀌거나 phase boundary 가 이동할 때만 갱신
- `vX.Y.Z/<topic>.md` (Draft → Frozen) — per-version spec. v0.2.0 의 `ir.md` 처럼 한 릴리스의 한 큰 주제 = 한 파일

### design/

- `pyo3-bindings.md` (Active) — 버전 무관 reference. PyO3 / abi3 / unsendable 같은 cross-version 제약을 모은 참조 문서
- `vX.Y.Z/<topic>-research.md` (Draft → Frozen) — ADR-style 결정 증거. 결정 매트릭스 + 항목별 (팩트/검증자 반박/최종 결정/출처). 짝이 되는 roadmap spec 과 1:1 페어

### implementation/

- `vX.Y.Z/migration.md` 또는 `vX.Y.Z/stages/stage-N.md` (Frozen) — 작업 로그. 완료 즉시 Frozen. 산출물 / 검증 결과 / 이월 사항 기록
- 작은 작업 (단일 세션·수일 규모) 은 단일 `migration.md`. 큰 작업 (여러 주, 의존성 추적 필요) 은 `stages/stage-N.md` 분할

### verification/

- `vX.Y.Z/<scope>-review.md` (Frozen) — 독립 검증 리포트. 검증 시점·검증자·판정 기록

## Cross-link 방향성 규칙

문서 간 의존성을 단방향화하여 "한 문서 변경이 다른 문서 갱신을 강제하는" 연쇄를 끊는다.

```
Living  ───→  Active  ───→  Draft  ───→  Frozen
  ↑              ↑             ↑             ↑
  └──────────────┴─────────────┴─────────────┘
           (위로 거슬러 link 만 OK)
```

- **Living → 모든 곳** OK (인덱스 역할)
- **Active → Draft / Frozen** OK (Phase 가 spec 을 가리킴)
- **Draft → Active / Living / Frozen** OK
- **Frozen → 다른 곳** 가급적 자제 (Frozen 후에 새 cross-link 추가하면 본문 수정이 됨)

### Spec ↔ spec 직접 link 금지 (예외 1 종)

- **금지**: 같은 디렉토리 안의 spec 끼리 직접 link (예: `v0.3.0/cli.md` ↔ `v0.3.0/ir-expansion.md`). 새 spec 추가 시 기존 spec 도 손봐야 하는 연쇄 발생
- **대신**: `roadmap/README.md` 또는 `phase-N.md` 가 묶어서 노출
- **예외**: **짝 페어** — `roadmap/vX.Y.Z/<topic>.md` 와 `design/vX.Y.Z/<topic>-research.md` 는 1:1 짝 (spec ↔ ADR). 짝끼리는 직접 link 유지 (두 문서가 사실상 한 결정의 두 면)

## 새 spec 추가 절차

### v<X.Y.Z> 신설 시

1. 디렉토리 생성: `docs/roadmap/v<X.Y.Z>/`, `docs/design/v<X.Y.Z>/`
2. spec 파일 작성 (Status: Draft, Target: vX.Y.Z, Last updated: 오늘)
3. 짝이 되는 design research 파일 작성 (Status: Draft, Target: vX.Y.Z)
4. `docs/roadmap/README.md` 의 인덱스 표에 행 추가
5. 해당 phase 가 있다면 `phase-N.md` 의 § 대상 버전 / § 산하 spec 갱신 (Active 갱신은 자유)

### 버전 GA 후

1. 해당 vX.Y.Z 디렉토리 안의 spec 들 Status: Draft → Frozen, GA: vX.Y.Z 로 전환
2. `Last updated` 를 GA 일자로
3. `docs/roadmap/README.md` 인덱스 갱신 (Status 컬럼)
4. `CHANGELOG.md` 의 해당 버전 섹션 마무리
5. 구현 로그 작성 — `docs/implementation/v<X.Y.Z>/...` (작성 즉시 Frozen)

### Frozen 후 결정 변경이 필요한 경우

1. **새 spec 작성** — 기존 파일 수정 금지. 새 파일 (예: `docs/roadmap/v0.4.0/ir-correction.md`)
2. **기존 Frozen spec 의 Status** 만 단일 라인 갱신: `Status: Superseded by [link to new spec]`
3. 새 spec 본문에 § Supersedes 섹션 추가하여 무엇을 어떻게 바꾸는지 명시
4. CHANGELOG 에 변경 사유 기록

오타·깨진 링크·외부 URL 변경 같은 비-의미 변경은 in-place 가능 (Last updated 갱신).

## 명명 규칙

- 파일명: kebab-case (`ir-expansion.md`, not `ir_expansion.md`)
- 디렉토리: `v` prefix + SemVer (`v0.3.0/`, not `0.3.0/`)
- ADR 파일: `<topic>-research.md` (roadmap spec `<topic>.md` 와 stem 일치)
- stage 파일: `stage-<N>.md` (1-indexed)

## 본 문서의 갱신

CONVENTIONS.md 자체는 Living. 정책 변경 시 in-place 갱신. **단** 본 문서의 변경은 모든 spec 작성에 영향을 주므로:

- 큰 변경 (예: Status 분류 추가/삭제) 시 PR 에 영향 받는 기존 문서 일괄 마이그레이션 포함
- 작은 변경 (예: 명명 규칙 추가) 는 in-place + 신규 문서부터 적용, 기존은 점진 정리

## 참조

- Rust RFC 운영: <https://rust-lang.github.io/rfcs/>
- Python PEP 절차: <https://peps.python.org/pep-0001/>
- ADR 패턴 (Architecture Decision Records): <https://adr.github.io/>
- Diátaxis 4-axis: <https://diataxis.fr/>
- GitHub Spec Kit: <https://github.com/github/spec-kit>
