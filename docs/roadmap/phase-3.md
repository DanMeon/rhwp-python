# Phase 3 — view 렌더러 + RAG 프레임워크 통합

**대상 버전**: v0.4.0 ~ v0.6.0
**선행 조건**: Phase 2 IR 확장 (v0.3.0) 안정

> 원안 대비 버전이 한 번씩 당겨짐 (v0.5~v0.7 → v0.4~v0.6) — v0.2.0 에서 IR 도입이 앞당겨지면서 후속 Phase 도 일괄 하향 이동.

## 목표

v0.2.0/v0.3.0 에서 확정된 IR 을 다른 포맷으로 렌더링(view) 하고, LangChain 외의 RAG 프레임워크와 통합한다. HtmlRAG (WWW 2025, arXiv:2411.02959) 등 최근 연구는 LLM 에 문서를 제공할 때 **구조를 보존하는 HTML** 이 평문화 대비 우수함을 보고하므로, view 변환 품질이 RAG 체감 성능과 직결된다.

## 범위

### view 렌더러 (v0.4.0)

- `HwpDocument.to_markdown()` — IR → CommonMark + GFM 확장
  - 표는 GFM `|a|b|` 형태. `rowspan`/`colspan` 이 있는 셀은 GFM 으로 표현 불가 → HTML 인라인으로 폴백
  - 머리글·꼬리말은 YAML frontmatter (선택) 또는 주석 블록
  - 각주/미주는 CommonMark footnote 확장
  - 수식은 `$$ ... $$` (KaTeX 호환) — `FormulaBlock.tex` 가 있을 때만
- `HwpDocument.to_html()` — IR → HTML5
  - `<article>`, `<section>`, `<table>` 등 시맨틱 태그
  - 접근성: `<caption>`, `<th scope>`, `aria-*` 기본 포함
  - CSS 는 기본 미동봉, 별도 `to_html(include_css=True)` 옵션
  - 이미지 처리: `Picture.ref_mode` 를 따름 (`placeholder` → `<img alt>`, `embedded` → base64 `src=`, `external` → 외부 파일 + 경로 반환)

HTML 은 `TableBlock.html` 과 별개 — TableBlock 수준 HTML 은 표 하나의 HTML 조각 (RAG 주입용), 문서 전체 `to_html()` 은 완전한 HTML5 문서 (브라우저 표시용).

### RAG 통합 확장 (v0.5.0 ~ v0.6.0)

- **v0.5.0** — `rhwp.integrations.llamaindex.HwpReader` (LlamaIndex `BaseReader` 구현)
  - `load_data()` / `lazy_load_data()` 동기 + async
  - IR → `Document`/`TextNode` 변환, `parent_id`/`prev`/`next` 링크 보존 (연구 결과 § 1 참조)
  - 섹션·단락을 `NodeRelationship.PARENT/CHILD` 로 표현 → `AutoMergingRetriever` 호환
- **v0.6.0** — `rhwp.integrations.haystack.HwpConverter` (Haystack 2.x `Converter`) — **커뮤니티 수요 확인 후**
  - Haystack `Document` 로 변환, `meta` 에 섹션 경계 힌트 저장

## 릴리스 분할

| 버전 | 범위 |
|---|---|
| v0.4.0 | `to_markdown()` / `to_html()` view — 표 rowspan/colspan HTML 인라인 처리 포함 |
| v0.5.0 | LlamaIndex 통합 (`HwpReader`, AutoMergingRetriever 호환 node 트리) |
| v0.6.0 | Haystack 통합 (커뮤니티 수요 확인 후) + LangChain 로더의 IR 직접 활용 (breadcrumb 자동 삽입 등 Anthropic Contextual Retrieval 스타일) |

## 미확정 이슈

- **Markdown 방언** — CommonMark / GFM / Pandoc Markdown / MyST. 기본값 GFM (표·각주 지원). Pandoc-compatible 플래그는 별도 옵션
- **HTML 출력의 CSS 동봉 여부** — 기본 미동봉, `include_css: bool` 또는 별도 `style_bundle()` 함수
- **LlamaIndex 가 IR 스키마를 그대로 소비 가능한가** — 현재 LlamaIndex `BaseNode` 는 자유형 `metadata: dict`. 완전 호환은 불가 (IR 의 Pydantic 타입 손실). 변환 레이어 필수 — 메타데이터에 `rhwp.ir.json` 키로 원본 IR 직렬화 보존하여 라운드트립 가능하게 설계
- **Contextual Retrieval 자동 지원 여부** — Anthropic 기법은 LLM 호출 비용 유발. rhwp-python 이 이를 내장하면 비용이 사용자에게 불투명 → **미내장**. 대신 `doc.breadcrumb(node_id)` 헬퍼로 사용자가 수동 결합 가능하게 설계
