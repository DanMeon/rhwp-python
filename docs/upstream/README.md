# Upstream Issue Drafts — 인덱스

본 디렉토리 (`docs/upstream/`) 는 외부 시스템 (`edwardkim/rhwp` GitHub Issues 등) 으로 흘러가기 전 단계의 staging. 정식 spec 의 일부가 아니며, 각 `<topic>.md` 는 가능한 한 GitHub 이슈 본문에 그대로 등록 가능한 형태로 작성한다 (본 인덱스는 그 외 자체 추적 메타를 보유).

정책 SSOT: [docs/CONVENTIONS.md § upstream/](../CONVENTIONS.md#upstream).

## 활성 / 해결 이슈

| 이슈 | Status | 상류 등록 | RESOLVED | 비고 |
|---|---|---|---|---|
| [issue-find-control-text-positions.md](issue-find-control-text-positions.md) | Frozen | [edwardkim/rhwp#390](https://github.com/edwardkim/rhwp/issues/390) | 2026-04-28 ([PR #405](https://github.com/edwardkim/rhwp/pull/405)) | `Paragraph::control_text_positions(&self)` 옵션 A 채택. v0.3.1 spec 이 본 파일 참조 → 삭제 대신 in-place Frozen |
| [issue-utf16-pos-to-char-idx.md](issue-utf16-pos-to-char-idx.md) | Frozen | [edwardkim/rhwp#484](https://github.com/edwardkim/rhwp/issues/484) | 2026-04-30 ([PR #494](https://github.com/edwardkim/rhwp/pull/494)) | #390 후속 같은 결. `Paragraph::utf16_pos_to_char_idx(&self)` 옵션 A 채택. v0.3.2 spec 이 본 파일 참조 → 삭제 대신 in-place Frozen |
| [issue-macos-png-coretext-hang.md](issue-macos-png-coretext-hang.md) | Frozen | [edwardkim/rhwp#823](https://github.com/edwardkim/rhwp/issues/823) | 2026-06-04 (상류 v0.7.13) | headless macOS PNG 렌더 hang (CoreText IPC). v0.8.0 상류 sync 로 fix 흡수 + `ci.yml` macOS smoke 잡 복원 |
| [issue-hwpx-shapecomment-drawing-shapes.md](issue-hwpx-shapecomment-drawing-shapes.md) | Frozen | [edwardkim/rhwp#1451](https://github.com/edwardkim/rhwp/issues/1451) | 2026-07-07 (상류 commit `2d6d0cf9`+`c0f94fbb`) | legacy 도형 (`render_common_shape_xml`) `hp:shapeComment` 미방출 (#1392 후속). 상류 해결 흡수 (pin `10f5c51e`) → `table-vpos-01.hwpx` round-trip 무손실. v0.8.1 spec 이 본 파일 참조 → 삭제 대신 in-place Frozen |

## Archive 정책

- **Active → Frozen 전환** 두 가지 경로:
  - **삭제** — 다른 spec 이 본 파일을 참조하지 않을 때. 정보는 GitHub permalink + git history 가 보존
  - **in-place Frozen 전환** — 다른 Frozen spec 이 본 파일을 참조할 때. frontmatter `status: Frozen` (`ga` 생략 — 특정 버전 미귀속), 본문 첫 헤더 위에 `> **RESOLVED YYYY-MM-DD** — 상류 PR/commit 참조 …` 한 줄 인용 블록 추가. 기존 body 보존 (historical record)

본 인덱스는 위 전환을 추적 — 파일 본문에는 archive 정책 문장을 두지 않는다 (GitHub 이슈 등록 시 노이즈).
