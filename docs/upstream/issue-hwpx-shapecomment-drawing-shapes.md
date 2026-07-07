---
status: Frozen
description: "업스트림 제안 — HWPX serializer 의 legacy 도형 경로(ellipse/arc/polygon/curve/chart/ole)가 hp:shapeComment 를 미직렬화. #1392 는 pic/equation/container/rect 4경로만 구현, render_common_shape_xml 누락. 실문서 round-trip 으로 polygon 설명 소실 재현. 제안 패치 diff 0 실측. 상류 등록 [#1451](https://github.com/edwardkim/rhwp/issues/1451)."
last_updated: 2026-06-21
---

> **RESOLVED 2026-07-07** — 상류 [#1451](https://github.com/edwardkim/rhwp/issues/1451) 머지로 해결. legacy 도형 shapeComment 직렬화 commit `2d6d0cf9` (1단계) + `c0f94fbb` (Polygon 보존 가드 2단계). rhwp-python pin `10f5c51e` 에 흡수 — `table-vpos-01.hwpx` round-trip 무손실 (v0.8.1). 아래 본문은 제안 시점 historical record.

> 외부 binding (`rhwp-python`) 구현 중 업스트림에서 수정이 필요해 보이는 부분을 발견하여, Claude 로 조사 및 다차례 사실 검증을 거친 결과입니다.

# HWPX serializer: hp:shapeComment 미직렬화 — legacy 도형 경로 (ellipse/arc/polygon/curve)

## 현상

[#1392](https://github.com/edwardkim/rhwp/issues/1392) ([PR #1405](https://github.com/edwardkim/rhwp/pull/1405)) 가 `hp:shapeComment` 직렬화를 picture / equation / container / rectangle 4경로에 추가했으나, **`render_common_shape_xml` 을 경유하는 나머지 도형 (ellipse / arc / polygon / curve / chart / ole) 은 `shapeComment` 가 여전히 방출되지 않습니다.**

실문서 `samples/table-vpos-01.hwpx` 의 다각형 2개에 달린 `<hp:shapeComment>다각형입니다.</hp:shapeComment>` 가 `serialize_hwpx` 출력에서 소실됩니다 (같은 문서의 그림 shapeComment 3건은 #1392 로 보존되어, 도형 종류에 따라 보존 여부가 갈립니다).

## 재현

- 환경: 상류 main `7d9aae7f` (= 현재 HEAD) / devel `d24231a6` — 두 브랜치 모두 동일
- `samples/table-vpos-01.hwpx` 를 parse → `serialize_hwpx` → 출력 section XML 비교:
  - 원본 `<hp:shapeComment` 5건 → 직렬화 출력 3건 (polygon 2건 소실)
  - `serializer::hwpx::roundtrip::diff_documents(원본, 재파싱)` 가 `IrDifference::ObjectComment` 2건 보고:
    ```
    section[0] paragraph[33]/ctrl[0]shape comment: expected="다각형입니다." actual=""
    ```
- 외부 binding `rhwp-python` 의 HWPX round-trip 검증 표면 (`Document.verify_hwpx_roundtrip`) 으로 실문서에서 발견했습니다.

## 원인

`render_shape` dispatcher (`src/serializer/hwpx/section.rs:1077`) 가 Rectangle / Line / Group / Picture 만 전용 라이터로 보내고, Ellipse / Arc / Polygon / Curve / Chart / Ole 는 `render_common_shape_xml` (`section.rs:1141-1182`) 로 fallthrough 합니다 (`section.rs:1123` `ShapeObject::Polygon(p) => ("polygon", &p.common, &p.drawing.caption)`).

`render_common_shape_xml` 이 방출하는 자식 요소는 **`sz` · `pos` · `outMargin` · `caption` 뿐**이고 `shapeComment` (= `CommonObjAttr.description`) 는 빠져 있습니다. `caption` 은 [#1403](https://github.com/edwardkim/rhwp/issues/1403) 으로 legacy 경로에 추가됐으나 (`section.rs:1172` 주석) shapeComment 는 동승하지 않았습니다.

대조 — shapeComment 를 방출하는 경로:

| 도형 | 방출 위치 |
|---|---|
| rectangle | `shape.rs:109` `write_shape_comment` |
| equation | `section.rs:1216` `render_equation` (inline) |
| picture | `picture.rs:104` `write_shape_comment` |
| **ellipse / arc / polygon / curve / chart / ole** | **없음 (`render_common_shape_xml`)** |

`write_shape_comment` (`shape.rs:715`) 는 이미 "도형(rect)·그림·수식·묶음 공유" 로 존재하지만, `render_common_shape_xml` 경로에서는 호출되지 않습니다.

참고로 `roundtrip::diff_documents` 의 `ObjectComment` 게이트 (#1392) 는 이 손실을 이미 검출합니다 — `task1392_shape_comment_loss_in_gate` 가 Ellipse 케이스로 가드 중이라, serializer 만 따라오면 게이트가 자동으로 회귀를 막습니다.

## 제안

`render_common_shape_xml` 의 caption 방출 직후 (`</hp:{tag}>` 닫기 전) 에 shapeComment 를 추가하면 rectangle / equation / picture 와 동일하게 보존됩니다. OWPML `AbstractShapeObjectType` 순서 (`shape.rs:7`: `… outMargin → caption → shapeComment`) 에 맞춰:

```rust
// section.rs render_common_shape_xml — caption push 직후, </hp:{tag}> 닫기 전
if !c.description.is_empty() {
    out.push_str(&format!(
        "<hp:shapeComment>{}</hp:shapeComment>",
        xml_escape(&c.description)
    ));
}
out.push_str(&format!("</hp:{tag}>"));
```

(또는 기존 `shape.rs:715` `write_shape_comment` 를 String 빌더 형태에 맞춰 재사용)

빈 `description` 은 미방출 (#1392 의 picture / equation 규칙과 동일). 변경 후 `diff_documents` 게이트가 polygon / ellipse / arc / curve round-trip 을 자동 보증합니다.

## 검증

위 제안 패치를 `render_common_shape_xml` 에 적용해 외부 binding (`rhwp-python`) 환경에서 빌드 후 실측한 결과 (`maturin develop --release` clean):

| 항목 | 패치 전 | 패치 후 |
|---|---|---|
| `table-vpos-01.hwpx` round-trip diff (`diff_documents`) | `ObjectComment` 2건 (polygon 2개) | **0건** |
| serialize 출력의 `<hp:shapeComment>` 개수 | 3 (polygon 2건 소실) | **5 (다각형 2건 보존)** |
| 보존 fixture (`aift.hwpx` / `tac-img-02.hwpx` / `business_overview.hwpx`) | diff 0 | **diff 0 (회귀 없음)** |

생성 XML 은 원본과 동일 구조 (`<hp:outMargin/><hp:shapeComment>다각형입니다.</hp:shapeComment></hp:polygon>`) 로, parser 가 그대로 재적재합니다 (caption 부재 도형은 outMargin 직후 방출). 검증 후 패치는 원복했습니다.

## 영향

- `render_common_shape_xml` 경유 도형 (ellipse / arc / polygon / curve / chart / ole) 의 shapeComment round-trip 보존
- 알고리즘 / 스키마 변경 없음 — 누락 요소 방출 추가만
- 기존 rectangle / equation / picture / container 경로 무영향 (별도 라이터)

## 참고 위치

- `src/serializer/hwpx/section.rs:1077` (`render_shape` dispatcher)
- `src/serializer/hwpx/section.rs:1123` (Polygon → `render_common_shape_xml` 경로)
- `src/serializer/hwpx/section.rs:1141-1182` (`render_common_shape_xml`, shapeComment 누락 지점)
- `src/serializer/hwpx/section.rs:1172` (#1403 caption 추가 주석)
- `src/serializer/hwpx/shape.rs:715` (`write_shape_comment`, 재사용 후보)
- `src/serializer/hwpx/shape.rs:7` (OWPML AbstractShapeObjectType 순서)
- `src/serializer/hwpx/picture.rs:103-104` (caption 직후 shapeComment 선례)

## 관련 이슈

- [#1392](https://github.com/edwardkim/rhwp/issues/1392) `HWPX serializer: hp:shapeComment 미직렬화 — 도형 설명 소실` (CLOSED, [PR #1405](https://github.com/edwardkim/rhwp/pull/1405)) — picture / equation / container / rectangle 4경로 구현. 본 이슈는 그 범위 밖 legacy 도형 경로의 후속입니다.
- [#1403](https://github.com/edwardkim/rhwp/issues/1403) `HWPX serializer: 그림/도형 캡션(hp:caption) 미직렬화` — `render_common_shape_xml` 에 caption 을 추가했으나 shapeComment 는 동승하지 않았습니다.
