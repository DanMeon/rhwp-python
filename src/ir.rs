//! Document raw 추출기 — Rust `Document` → Python primitive 트리.
//!
//! IR 도메인 변환 (HTML 직렬화, cell role 분류, Pydantic 모델 합성) 은 Python
//! `rhwp.ir._mapper` 에 위임한다. 이 모듈의 책임은:
//!
//! - HWP binary 모델 (rhwp upstream) 을 Python 친화 평탄 구조로 펼치기
//! - upstream 내부 표현 (UTF-16 char offset, char_shape 테이블 등) 을 캡슐화 —
//!   raw 출력은 codepoint index 와 boolean 으로 미리 해소된다
//!
//! `#[derive(IntoPyObject)]` 가 struct field 이름을 PyDict key 로 자동 매핑한다.
//! key 명세는 Python `_mapper.py` 가 소비하는 계약이므로 변경 시 양쪽 동기화 필요.

use pyo3::prelude::*;

use rhwp::model::control::Control;
use rhwp::model::document::{DocInfo, Document};
use rhwp::model::paragraph::Paragraph;
use rhwp::model::style::UnderlineType;
use rhwp::model::table::{Cell, Table};

#[derive(IntoPyObject)]
pub(crate) struct RawCharRun {
    pub start_cp: usize,
    pub end_cp: usize,
    pub char_shape_id: u32,
    pub bold: bool,
    pub italic: bool,
    pub underline: bool,
    pub strikethrough: bool,
}

#[derive(IntoPyObject)]
pub(crate) struct RawCell {
    pub row: usize,
    pub col: usize,
    pub row_span: usize,
    pub col_span: usize,
    pub is_header: bool,
    pub paragraphs: Vec<RawParagraph>,
}

#[derive(IntoPyObject)]
pub(crate) struct RawTable {
    pub rows: usize,
    pub cols: usize,
    pub cells: Vec<RawCell>,
    pub caption: Option<String>,
}

#[derive(IntoPyObject)]
pub(crate) struct RawParagraph {
    pub section_idx: usize,
    pub para_idx: usize,
    pub text: String,
    pub char_runs: Vec<RawCharRun>,
    pub tables: Vec<RawTable>,
}

#[derive(IntoPyObject)]
pub(crate) struct RawDocument {
    pub source_uri: Option<String>,
    pub section_count: usize,
    pub paragraphs: Vec<RawParagraph>,
}

/// 문서 전체를 raw 평탄 구조로 추출한다.
///
/// 호출 경로 전체가 Rust-only — `Python<'_>` 토큰을 받지 않으므로 호출 측이
/// `py.detach()` 로 GIL 을 해제할 수 있다. 결과 반환 시점에 PyO3 derive 가
/// 한 번에 PyDict 트리로 변환한다.
pub(crate) fn build_raw_document(doc: &Document, source_uri: Option<&str>) -> RawDocument {
    let mut paragraphs = Vec::new();
    for (section_idx, section) in doc.sections.iter().enumerate() {
        for (para_idx, para) in section.paragraphs.iter().enumerate() {
            paragraphs.push(build_raw_paragraph(
                section_idx,
                para_idx,
                para,
                &doc.doc_info,
            ));
        }
    }
    RawDocument {
        source_uri: source_uri.map(String::from),
        section_count: doc.sections.len(),
        paragraphs,
    }
}

fn build_raw_paragraph(
    section_idx: usize,
    para_idx: usize,
    para: &Paragraph,
    doc_info: &DocInfo,
) -> RawParagraph {
    let char_runs = build_char_runs(para, doc_info);
    // ^ 문단의 controls 중 Table 만 추출 — 내부 paragraph 들은 외부 (section, para)
    //   를 공유한다 (Provenance 계약: 표는 부모 문단 위치를 가리킨다)
    let tables: Vec<RawTable> = para
        .controls
        .iter()
        .filter_map(|c| match c {
            Control::Table(t) => Some(build_raw_table(t, section_idx, para_idx, doc_info)),
            _ => None,
        })
        .collect();
    RawParagraph {
        section_idx,
        para_idx,
        text: para.text.clone(),
        char_runs,
        tables,
    }
}

/// `char_shapes` (UTF-16 offset 기반) 를 codepoint range 기반 RawCharRun 으로 해소한다.
///
/// 빈 텍스트나 char_shape 부재 시 빈 Vec 반환 — Python mapper 가 단일 style-less
/// 런으로 폴백한다. 이렇게 분리하면 Rust 는 "변환 가능한 런" 만 출고하고
/// 폴백 정책은 Python 도메인에서 결정한다.
fn build_char_runs(para: &Paragraph, doc_info: &DocInfo) -> Vec<RawCharRun> {
    let total_cp = para.text.chars().count();
    if total_cp == 0 || para.char_shapes.is_empty() {
        return Vec::new();
    }

    let mut runs = Vec::with_capacity(para.char_shapes.len());
    for i in 0..para.char_shapes.len() {
        let shape_ref = &para.char_shapes[i];
        let start_utf16 = shape_ref.start_pos;
        let end_utf16 = if i + 1 < para.char_shapes.len() {
            para.char_shapes[i + 1].start_pos
        } else {
            u32::MAX
        };

        let start_cp = utf16_to_cp(&para.char_offsets, start_utf16, total_cp);
        let end_cp = utf16_to_cp(&para.char_offsets, end_utf16, total_cp);

        if start_cp >= end_cp {
            continue;
        }

        let shape_id = shape_ref.char_shape_id;
        let shape = doc_info.char_shapes.get(shape_id as usize);
        runs.push(RawCharRun {
            start_cp,
            end_cp,
            char_shape_id: shape_id,
            bold: shape.map(|s| s.bold).unwrap_or(false),
            italic: shape.map(|s| s.italic).unwrap_or(false),
            underline: shape
                .map(|s| s.underline_type != UnderlineType::None)
                .unwrap_or(false),
            strikethrough: shape.map(|s| s.strikethrough).unwrap_or(false),
        });
    }

    runs
}

/// UTF-16 offset → codepoint index 변환.
///
/// `char_offsets[i]` 는 `text.chars().nth(i)` 에 해당하는 UTF-16 시작 위치.
/// 입력 `utf16` 이상인 첫 번째 codepoint 인덱스를 반환한다. 해당 offset 이
/// 텍스트 끝을 넘어가면 `fallback_end` 를 반환 (텍스트 codepoint 총 길이).
fn utf16_to_cp(char_offsets: &[u32], utf16: u32, fallback_end: usize) -> usize {
    if utf16 == u32::MAX {
        return fallback_end;
    }
    for (i, &off) in char_offsets.iter().enumerate() {
        if off >= utf16 {
            return i;
        }
    }
    fallback_end
}

fn build_raw_table(
    table: &Table,
    outer_section: usize,
    outer_para: usize,
    doc_info: &DocInfo,
) -> RawTable {
    let cells = table
        .cells
        .iter()
        .map(|c| build_raw_cell(c, outer_section, outer_para, doc_info))
        .collect();
    let caption = table.caption.as_ref().and_then(extract_caption_text);
    RawTable {
        rows: table.row_count as usize,
        cols: table.col_count as usize,
        cells,
        caption,
    }
}

fn build_raw_cell(
    cell: &Cell,
    outer_section: usize,
    outer_para: usize,
    doc_info: &DocInfo,
) -> RawCell {
    let paragraphs = cell
        .paragraphs
        .iter()
        .map(|p| build_raw_paragraph(outer_section, outer_para, p, doc_info))
        .collect();
    RawCell {
        row: cell.row as usize,
        col: cell.col as usize,
        row_span: cell.row_span.max(1) as usize,
        col_span: cell.col_span.max(1) as usize,
        is_header: cell.is_header,
        paragraphs,
    }
}

/// Caption 에서 텍스트만 추출한다 (복합 캡션 구조는 미지원).
fn extract_caption_text(caption: &rhwp::model::shape::Caption) -> Option<String> {
    let text: Vec<String> = caption
        .paragraphs
        .iter()
        .map(|p| p.text.clone())
        .filter(|t| !t.is_empty())
        .collect();
    if text.is_empty() {
        None
    } else {
        Some(text.join("\n"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn utf16_to_cp_sentinel_returns_fallback() {
        let offsets = vec![0u32, 1, 2];
        assert_eq!(utf16_to_cp(&offsets, u32::MAX, 3), 3);
    }

    #[test]
    fn utf16_to_cp_matches_first_ge() {
        let offsets = vec![0u32, 1, 3, 4]; // ^ 2번째 codepoint 는 SMP 라 2 code units
        assert_eq!(utf16_to_cp(&offsets, 0, 4), 0);
        assert_eq!(utf16_to_cp(&offsets, 1, 4), 1);
        assert_eq!(utf16_to_cp(&offsets, 2, 4), 2); // offset 2 는 char_offsets 에 없음 → 다음 >=2 인 3을 가진 인덱스 2
        assert_eq!(utf16_to_cp(&offsets, 3, 4), 2);
        assert_eq!(utf16_to_cp(&offsets, 5, 4), 4); // fallback
    }
}
