# Phase 2 — 계층 JSON IR 스키마

**대상 버전**: v0.3.0 ~ v0.4.0
**선행 조건**: v0.1.x (Phase 1 바인딩) GA, v0.2.x (CLI) 안정

## 목표

HWP 문서를 구조화된 JSON (Intermediate Representation) 으로 추출해 RAG 파이프라인에서 **의미 단위**로 활용. 텍스트 추출만 가능했던 Phase 1 을 넘어 문서의 계층 구조를 유지.

## 범위

- 재귀 중첩 표 (`TableCell` 안의 또 다른 `Table`) 를 IR 노드로 재구성
- `rowspan` / `colspan` 병합 셀 보존
- 비의미 셀 (레이아웃용 빈 셀 등) 에 시맨틱 태그 부여 — RAG 가 노이즈로 필터링 가능
- 문단·섹션·페이지 경계 보존

## 예시 IR (초안)

```json
{
  "type": "Document",
  "metadata": { "source": "a.hwp", "page_count": 3 },
  "sections": [
    {
      "type": "Section",
      "blocks": [
        { "type": "Paragraph", "text": "..." },
        {
          "type": "Table",
          "rows": [
            [
              { "type": "Cell", "rowspan": 2, "colspan": 1, "blocks": [...] },
              { "type": "Cell", "semantic": "placeholder" }
            ]
          ]
        }
      ]
    }
  ]
}
```

## Python API (초안)

```python
doc = rhwp.parse("a.hwp")
ir = doc.to_ir()              # Python dict (JSON-serializable)
ir_json: str = doc.to_ir_json()
```

## 릴리스 분할

| 버전 | 범위 |
|---|---|
| v0.3.0 | IR 기본 스키마 (Paragraph / Section / Table) |
| v0.4.0 | IR 확장 (이미지 / 수식 / 각주 / 머리글꼬리) |

## 미확정 이슈

- IR 스키마를 Pydantic 모델로 노출할지 / dict 만 반환할지
- JSON Schema 버전 관리 (`$schema` URL) 정책
- 대용량 문서 스트리밍 IR (generator 기반 `iter_blocks()`)
