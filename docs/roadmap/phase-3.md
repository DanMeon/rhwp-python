# Phase 3 — view 렌더러 + RAG 로더 확장

**대상 버전**: v0.5.0 ~ v0.7.0
**선행 조건**: Phase 2 IR 스키마 안정 (v0.4.x)

## 목표

IR 을 다른 포맷으로 렌더링하고, LangChain 외 RAG 프레임워크로 통합 확장.

## 범위

### view 렌더러

- `to_markdown()` — IR → CommonMark
  - 표는 GFM `|a|b|` 형태, 중첩 표는 GFM fenced block 또는 HTML 인라인
  - 머리글·꼬리글은 frontmatter 또는 주석 처리
- `to_html()` — IR → HTML
  - minimal CSS, 접근성 고려 (semantic tags)
  - 이미지는 base64 inline 또는 외부 파일 참조 선택

### RAG 통합 확장

- `rhwp.integrations.llamaindex.HwpReader` — LlamaIndex `BaseReader` 구현
- (선택) `rhwp.integrations.haystack.HwpConverter` — Haystack 2.x `Converter`

## 릴리스 분할

| 버전 | 범위 |
|---|---|
| v0.5.0 | `to_markdown()` / `to_html()` view |
| v0.6.0 | LlamaIndex 통합 |
| v0.7.0 | (선택) Haystack 통합 — 커뮤니티 수요 확인 후 |

## 미확정 이슈

- Markdown 방언 (CommonMark vs GFM vs Pandoc) — 기본 GFM, 확장 옵션 플래그
- HTML 출력의 CSS 동봉 여부 — 기본 미동봉, 별도 함수로 제공
- LlamaIndex 가 IR 스키마를 그대로 소비 가능할지, 혹은 LlamaIndex-native 타입으로 변환 레이어 필요할지
