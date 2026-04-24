//! Document IR v1 매퍼 — Rust `Document` → Python dict → Pydantic `HwpDocument`.
//!
//! 설계 근거: `docs/roadmap/v0.2.0/ir.md` §Rust 경계 패턴 + §테이블 표현.
//!
//! Stage S3 범위: Paragraph + InlineRun + Provenance + Table (셀 배열 / HTML /
//! text 3중 표현) + 중첩 표. 표가 있는 문단은 "ParagraphBlock 1 + 포함 표마다
//! TableBlock 1" 로 body 에 평탄화 (text/table 정확 interleaving 은 v0.3.0+).
//!
//! Table 분리 추출의 부산물로 같은 Paragraph 가 생성한 여러 블록은 동일
//! `(section_idx, para_idx)` Provenance 를 공유한다.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use rhwp::model::control::Control;
use rhwp::model::document::{DocInfo, Document};
use rhwp::model::paragraph::Paragraph;
use rhwp::model::style::{CharShape, UnderlineType};
use rhwp::model::table::{Cell, Table};

/// 문서 전체를 Python dict 로 변환 후 Pydantic `HwpDocument` 로 검증한다.
///
/// 결과는 `Py<PyAny>` — 호출자가 `OnceCell` 에 캐시 저장. GIL 이 필요하므로
/// 호출 경로 전체가 GIL 유지 구간에서 실행된다.
pub fn build_hwp_document(py: Python<'_>, doc: &Document) -> PyResult<Py<PyAny>> {
    let raw = build_document_dict(py, doc)?;
    let module = py.import("rhwp.ir.nodes")?;
    let hwp_class = module.getattr("HwpDocument")?;
    let ir = hwp_class.call_method1("model_validate", (raw,))?;
    Ok(ir.unbind())
}

fn build_document_dict<'py>(py: Python<'py>, doc: &Document) -> PyResult<Bound<'py, PyDict>> {
    let dict = PyDict::new(py);

    // ^ schema_name / schema_version 은 Pydantic 기본값 사용 — 명시 설정 불필요

    // * metadata — v0.2.0 S3 는 전부 None 출고 (HWP Summary Information 매핑은 v0.3.0+)
    let metadata = PyDict::new(py);
    metadata.set_item("title", py.None())?;
    metadata.set_item("author", py.None())?;
    metadata.set_item("creation_time", py.None())?;
    metadata.set_item("modification_time", py.None())?;
    dict.set_item("metadata", metadata)?;

    // * sections — S3 도 section_idx 만 (용지/단 매핑은 v0.3.0+)
    let sections = PyList::empty(py);
    for (section_idx, _section) in doc.sections.iter().enumerate() {
        let sect = PyDict::new(py);
        sect.set_item("section_idx", section_idx)?;
        sections.append(sect)?;
    }
    dict.set_item("sections", sections)?;

    // * body — 전 섹션의 모든 문단을 평탄화 (Paragraph → [ParagraphBlock, TableBlock...])
    let body = PyList::empty(py);
    for (section_idx, section) in doc.sections.iter().enumerate() {
        for (para_idx, para) in section.paragraphs.iter().enumerate() {
            let blocks = flatten_paragraph_to_blocks(py, section_idx, para_idx, para, &doc.doc_info)?;
            for blk in blocks {
                body.append(blk)?;
            }
        }
    }
    dict.set_item("body", body)?;

    // * furniture — v0.2.0 은 빈 컨테이너만 (ir.md §비목표)
    let furniture = PyDict::new(py);
    furniture.set_item("page_headers", PyList::empty(py))?;
    furniture.set_item("page_footers", PyList::empty(py))?;
    furniture.set_item("footnotes", PyList::empty(py))?;
    dict.set_item("furniture", furniture)?;

    Ok(dict)
}

/// 한 Paragraph 를 Block dict 리스트로 평탄화한다.
///
/// - 항상 ParagraphBlock 하나 생성 (text + inlines)
/// - Paragraph 의 `controls` 에서 `Control::Table` 만 TableBlock 으로 각각 생성
/// - 동일 `(section_idx, para_idx)` Provenance 를 공유. text 내 컨트롤 위치 기반
///   정확한 interleaving 은 v0.3.0+ 이월
/// - 재귀: TableCell.blocks 가 이 함수를 다시 호출하여 중첩 표 자연 지원
fn flatten_paragraph_to_blocks<'py>(
    py: Python<'py>,
    section_idx: usize,
    para_idx: usize,
    para: &Paragraph,
    doc_info: &DocInfo,
) -> PyResult<Vec<Bound<'py, PyDict>>> {
    let mut blocks = Vec::with_capacity(1 + para.controls.len());
    blocks.push(build_paragraph_block(py, section_idx, para_idx, para, doc_info)?);
    for control in &para.controls {
        if let Control::Table(table) = control {
            blocks.push(build_table_block(py, section_idx, para_idx, table, doc_info)?);
        }
    }
    Ok(blocks)
}

fn build_paragraph_block<'py>(
    py: Python<'py>,
    section_idx: usize,
    para_idx: usize,
    para: &Paragraph,
    doc_info: &DocInfo,
) -> PyResult<Bound<'py, PyDict>> {
    let dict = PyDict::new(py);
    dict.set_item("kind", "paragraph")?;
    dict.set_item("text", &para.text)?;
    dict.set_item("inlines", build_inline_runs(py, para, doc_info)?)?;

    let prov = PyDict::new(py);
    prov.set_item("section_idx", section_idx)?;
    prov.set_item("para_idx", para_idx)?;
    prov.set_item("char_start", 0usize)?;
    prov.set_item("char_end", para.text.chars().count())?;
    prov.set_item("page_range", py.None())?;
    dict.set_item("prov", prov)?;

    Ok(dict)
}

/// 문단의 `char_shapes` 를 InlineRun 리스트로 변환한다.
///
/// 상류 `start_pos` 는 UTF-16 위치 — codepoint 인덱스로 변환해 InlineRun 에
/// 실어보낸다 (ir.md §단락 내 InlineRun + §3 char 오프셋). `char_shapes` 가
/// 비어 있거나 전부 컨트롤 뒤 위치인 경우 단일 런으로 폴백한다.
///
/// 관례상 HWP 는 `char_shapes[0].start_pos == 0` 을 보장하지만, 손상된 파일
/// 대비로 첫 shape 앞 prefix 가 있으면 style-less 런으로 prepend 한다.
fn build_inline_runs<'py>(
    py: Python<'py>,
    para: &Paragraph,
    doc_info: &DocInfo,
) -> PyResult<Bound<'py, PyList>> {
    let runs = PyList::empty(py);
    let total_cp = para.text.chars().count();
    if total_cp == 0 {
        return Ok(runs);
    }

    if para.char_shapes.is_empty() {
        runs.append(make_inline_run(py, &para.text, None, None)?)?;
        return Ok(runs);
    }

    let text_chars: Vec<char> = para.text.chars().collect();

    // ^ 첫 shape 의 start_pos 가 0 보다 큰 경우, 앞부분 텍스트를 style-less 런으로 prepend
    let first_start_utf16 = para.char_shapes[0].start_pos;
    if first_start_utf16 > 0 {
        let prefix_end = utf16_to_cp(&para.char_offsets, first_start_utf16, total_cp);
        if prefix_end > 0 {
            let prefix: String = text_chars[..prefix_end].iter().collect();
            if !prefix.is_empty() {
                runs.append(make_inline_run(py, &prefix, None, None)?)?;
            }
        }
    }

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

        let text_slice: String = text_chars[start_cp..end_cp].iter().collect();
        if text_slice.is_empty() {
            continue;
        }

        let shape_id = shape_ref.char_shape_id;
        let shape = doc_info.char_shapes.get(shape_id as usize);
        runs.append(make_inline_run(py, &text_slice, Some(shape_id), shape)?)?;
    }

    // ^ 전부 컨트롤 뒤 위치라 런이 하나도 생성 안 됐으면 텍스트 전체를 단일 런으로 폴백
    if runs.is_empty() {
        runs.append(make_inline_run(py, &para.text, None, None)?)?;
    }

    Ok(runs)
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

fn make_inline_run<'py>(
    py: Python<'py>,
    text: &str,
    raw_style_id: Option<u32>,
    shape: Option<&CharShape>,
) -> PyResult<Bound<'py, PyDict>> {
    let dict = PyDict::new(py);
    dict.set_item("text", text)?;
    dict.set_item("bold", shape.map(|s| s.bold).unwrap_or(false))?;
    dict.set_item("italic", shape.map(|s| s.italic).unwrap_or(false))?;
    dict.set_item(
        "underline",
        shape
            .map(|s| s.underline_type != UnderlineType::None)
            .unwrap_or(false),
    )?;
    dict.set_item(
        "strikethrough",
        shape.map(|s| s.strikethrough).unwrap_or(false),
    )?;
    // ^ href/ruby 는 상류 Control 트리에서 별도 노출 — 후속 스테이지
    dict.set_item("href", py.None())?;
    dict.set_item("ruby", py.None())?;
    match raw_style_id {
        Some(id) => dict.set_item("raw_style_id", id)?,
        None => dict.set_item("raw_style_id", py.None())?,
    }
    Ok(dict)
}

// * Table — S3 범위 (ir.md §테이블 표현)

fn build_table_block<'py>(
    py: Python<'py>,
    section_idx: usize,
    para_idx: usize,
    table: &Table,
    doc_info: &DocInfo,
) -> PyResult<Bound<'py, PyDict>> {
    let dict = PyDict::new(py);
    dict.set_item("kind", "table")?;
    dict.set_item("rows", table.row_count as usize)?;
    dict.set_item("cols", table.col_count as usize)?;
    dict.set_item(
        "cells",
        build_table_cells(py, section_idx, para_idx, table, doc_info)?,
    )?;
    dict.set_item("html", table_to_html(table))?;
    dict.set_item("text", table_to_text(table))?;
    // ^ caption 은 단순 텍스트 추출만 — 복합 캡션 (캡션 안의 블록) 은 v0.3.0+ 이월
    let caption_text = table.caption.as_ref().and_then(extract_caption_text);
    match caption_text {
        Some(s) => dict.set_item("caption", s)?,
        None => dict.set_item("caption", py.None())?,
    }

    // ^ TableBlock 의 Provenance — char_start/char_end 는 "표 위치" 로 해석이 모호하므로
    //   부모 Paragraph 의 text 범위 밖임을 나타내기 위해 None 출고
    let prov = PyDict::new(py);
    prov.set_item("section_idx", section_idx)?;
    prov.set_item("para_idx", para_idx)?;
    prov.set_item("char_start", py.None())?;
    prov.set_item("char_end", py.None())?;
    prov.set_item("page_range", py.None())?;
    dict.set_item("prov", prov)?;

    Ok(dict)
}

fn build_table_cells<'py>(
    py: Python<'py>,
    section_idx: usize,
    para_idx: usize,
    table: &Table,
    doc_info: &DocInfo,
) -> PyResult<Bound<'py, PyList>> {
    let cols = table.col_count.max(1) as usize;
    let list = PyList::empty(py);
    for cell in &table.cells {
        let d = PyDict::new(py);
        d.set_item("row", cell.row as usize)?;
        d.set_item("col", cell.col as usize)?;
        d.set_item("row_span", cell.row_span.max(1) as usize)?;
        d.set_item("col_span", cell.col_span.max(1) as usize)?;
        // ^ grid_index: row-major 선형 인덱스. 병합 span 내부가 아닌 앵커 위치
        d.set_item(
            "grid_index",
            (cell.row as usize) * cols + (cell.col as usize),
        )?;
        d.set_item("role", cell_role(cell))?;

        // * 셀 내부: 각 inner paragraph 를 flatten — 중첩 표 재귀 지원
        let blocks = PyList::empty(py);
        for inner in &cell.paragraphs {
            // ^ 내부 문단의 para_idx 는 외부 표의 para_idx 를 그대로 공유 (간단화)
            //   더 정밀한 식별자 (cell-local idx) 는 v0.3.0+ 검토
            for blk in flatten_paragraph_to_blocks(py, section_idx, para_idx, inner, doc_info)? {
                blocks.append(blk)?;
            }
        }
        d.set_item("blocks", blocks)?;

        list.append(d)?;
    }
    Ok(list)
}

fn cell_role(cell: &Cell) -> &'static str {
    // ^ HWP 는 header 가 row/column 구분 없음 — row_header/column_header 어느 쪽으로
    //   확정하기 어려우므로 단순화: is_header → "column_header", 그 외 → "data".
    //   "layout" (간격용 빈 셀 감지) 는 DocLayNet 어휘지만 HWP 에서 자동 식별이
    //   불가능하므로 S3 는 제공하지 않는다 (ir.md §테이블 표현)
    if cell.is_header {
        "column_header"
    } else {
        "data"
    }
}

/// Caption 에서 텍스트만 추출 — 복합 캡션은 v0.3.0+ 이월
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

/// Table → HTML 문자열 직렬화 (HtmlRAG 호환, ir.md §테이블 표현).
///
/// Attribute 순서 고정 (rowspan → colspan) 으로 dedup hash 안정성 보장 —
/// "동일 패키지 버전 내" 스코프 (ir.md §2 결정사항).
fn table_to_html(table: &Table) -> String {
    let mut html = String::from("<table>");
    let mut current_row: Option<u16> = None;
    for cell in &table.cells {
        if current_row != Some(cell.row) {
            if current_row.is_some() {
                html.push_str("</tr>");
            }
            html.push_str("<tr>");
            current_row = Some(cell.row);
        }
        let tag = if cell.is_header { "th" } else { "td" };
        html.push('<');
        html.push_str(tag);
        // ^ attribute 순서: rowspan 먼저, colspan 다음. 값이 1 이면 생략
        if cell.row_span > 1 {
            html.push_str(" rowspan=\"");
            html.push_str(&cell.row_span.to_string());
            html.push('"');
        }
        if cell.col_span > 1 {
            html.push_str(" colspan=\"");
            html.push_str(&cell.col_span.to_string());
            html.push('"');
        }
        html.push('>');
        html.push_str(&escape_html(&cell_plain_text(cell, " ")));
        html.push_str("</");
        html.push_str(tag);
        html.push('>');
    }
    if current_row.is_some() {
        html.push_str("</tr>");
    }
    html.push_str("</table>");
    html
}

/// Table → 평문 (행: `\n` 구분, 셀: `\t` 구분). 단순 검색·diff 용 폴백.
fn table_to_text(table: &Table) -> String {
    let mut lines: Vec<String> = Vec::new();
    let mut current_row: Option<u16> = None;
    let mut current_cells: Vec<String> = Vec::new();
    for cell in &table.cells {
        if current_row != Some(cell.row) {
            if current_row.is_some() {
                lines.push(current_cells.join("\t"));
            }
            current_cells = Vec::new();
            current_row = Some(cell.row);
        }
        current_cells.push(cell_plain_text(cell, " "));
    }
    if current_row.is_some() {
        lines.push(current_cells.join("\t"));
    }
    lines.join("\n")
}

fn cell_plain_text(cell: &Cell, para_sep: &str) -> String {
    cell.paragraphs
        .iter()
        .map(|p| p.text.as_str())
        .filter(|t| !t.is_empty())
        .collect::<Vec<_>>()
        .join(para_sep)
}

fn escape_html(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for ch in s.chars() {
        match ch {
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '&' => out.push_str("&amp;"),
            '"' => out.push_str("&quot;"),
            _ => out.push(ch),
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn escape_html_all_special_chars() {
        assert_eq!(
            escape_html("<b>A & B</b>"),
            "&lt;b&gt;A &amp; B&lt;/b&gt;"
        );
    }

    #[test]
    fn escape_html_quote() {
        assert_eq!(escape_html("\"hello\""), "&quot;hello&quot;");
    }

    #[test]
    fn escape_html_plain_passes_through() {
        assert_eq!(escape_html("hello world 한글"), "hello world 한글");
    }

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
