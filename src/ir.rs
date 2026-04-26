//! Document raw 추출기 — Rust `Document` → Python primitive 트리.
//!
//! IR 도메인 변환 (HTML 직렬화, cell role 분류, mime 매핑, Pydantic 모델 합성)
//! 은 Python `rhwp.ir._mapper` 에 위임한다. 이 모듈의 책임은:
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
use rhwp::model::image::Picture;
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
pub(crate) struct RawImageRef {
    pub bin_data_id: u16,
    // ^ 상류 BinData 의 extension (e.g. "jpg", "png", "bmp"). Python mapper 가 mime 매핑.
    //   Embedding 이 아닌 타입 (Link 등) 또는 누락 시 None — mapper 가
    //   "application/octet-stream" 으로 폴백한다.
    pub extension: Option<String>,
    // ^ Embedding 타입에 대해 binary 가 실제 로드됐는지 — broken reference 진단.
    //   true: bin_data_content 에 entry 존재. false: 누락 또는 Link/Storage 타입.
    pub has_content: bool,
}

#[derive(IntoPyObject)]
pub(crate) struct RawPicture {
    // ^ 그림 자체의 위치 = 부모 paragraph 의 (section_idx, para_idx) 공유.
    //   Provenance 계약: 컨트롤은 부모 문단 위치를 가리킨다 (Table 과 동일).
    pub section_idx: usize,
    pub para_idx: usize,
    pub image: Option<RawImageRef>,
    // ^ caption.paragraphs 첫 비-빈 텍스트 — S1 임시 alt-text. S3 에서
    //   `CaptionBlock` 도입 시 이 단순 필드는 PictureBlock.description 으로
    //   유지되고 caption_block 이 추가된다.
    pub description: Option<String>,
}

#[derive(IntoPyObject)]
pub(crate) struct RawParagraph {
    pub section_idx: usize,
    pub para_idx: usize,
    pub text: String,
    pub char_runs: Vec<RawCharRun>,
    pub tables: Vec<RawTable>,
    pub pictures: Vec<RawPicture>,
}

#[derive(IntoPyObject)]
pub(crate) struct RawDocument {
    pub source_uri: Option<String>,
    pub section_count: usize,
    pub paragraphs: Vec<RawParagraph>,
    // ^ furniture.page_headers / page_footers 로 매핑. S1 시점은 Header/Footer
    //   컨트롤만 (각주/미주 본문은 S2 에서 추가).
    pub headers: Vec<RawParagraph>,
    pub footers: Vec<RawParagraph>,
}

/// 문서 전체를 raw 평탄 구조로 추출한다.
///
/// 호출 경로 전체가 Rust-only — `Python<'_>` 토큰을 받지 않으므로 호출 측이
/// `py.detach()` 로 GIL 을 해제할 수 있다. 결과 반환 시점에 PyO3 derive 가
/// 한 번에 PyDict 트리로 변환한다.
pub(crate) fn build_raw_document(doc: &Document, source_uri: Option<&str>) -> RawDocument {
    let mut paragraphs = Vec::new();
    let mut headers = Vec::new();
    let mut footers = Vec::new();
    for (section_idx, section) in doc.sections.iter().enumerate() {
        for (para_idx, para) in section.paragraphs.iter().enumerate() {
            paragraphs.push(build_raw_paragraph(section_idx, para_idx, para, doc));
            collect_headers_footers_from_paragraph(
                section_idx,
                para_idx,
                para,
                doc,
                &mut headers,
                &mut footers,
            );
        }
        // ^ 바탕쪽 안의 Header/Footer 컨트롤도 furniture 로 라우팅 (spec § 8 매퍼 정책).
        //   바탕쪽 paragraph 자체는 furniture 에 넣지 않는다 — 페이지 배경 템플릿이지
        //   머리글/꼬리말이 아니므로. Header/Footer 컨트롤이 그 안에 있을 때만 추출.
        //   `enumerate()` 를 flat_map 바깥에 두어 여러 MasterPage 의 paragraph 가
        //   고유한 flat 인덱스를 받게 한다 (MasterPage 내부 별 0 부터 재시작 회피).
        for (mp_flat_idx, mp_para) in section
            .section_def
            .master_pages
            .iter()
            .flat_map(|mp| mp.paragraphs.iter())
            .enumerate()
        {
            collect_headers_footers_from_paragraph(
                section_idx,
                mp_flat_idx,
                mp_para,
                doc,
                &mut headers,
                &mut footers,
            );
        }
    }
    RawDocument {
        source_uri: source_uri.map(String::from),
        section_count: doc.sections.len(),
        paragraphs,
        headers,
        footers,
    }
}

fn build_raw_paragraph(
    section_idx: usize,
    para_idx: usize,
    para: &Paragraph,
    doc: &Document,
) -> RawParagraph {
    let char_runs = build_char_runs(para, &doc.doc_info);
    // ^ 문단의 controls 중 Table / Picture 만 추출 — 내부 paragraph 들은 외부 (section, para)
    //   를 공유한다 (Provenance 계약: 표·그림은 부모 문단 위치를 가리킨다)
    let mut tables = Vec::new();
    let mut pictures = Vec::new();
    for ctrl in &para.controls {
        match ctrl {
            Control::Table(t) => {
                tables.push(build_raw_table(t, section_idx, para_idx, doc));
            }
            Control::Picture(p) => {
                pictures.push(build_raw_picture(p, section_idx, para_idx, doc));
            }
            _ => {}
        }
    }
    RawParagraph {
        section_idx,
        para_idx,
        text: para.text.clone(),
        char_runs,
        tables,
        pictures,
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
    doc: &Document,
) -> RawTable {
    let cells = table
        .cells
        .iter()
        .map(|c| build_raw_cell(c, outer_section, outer_para, doc))
        .collect();
    let caption = table.caption.as_ref().and_then(extract_caption_text);
    RawTable {
        rows: table.row_count as usize,
        cols: table.col_count as usize,
        cells,
        caption,
    }
}

fn build_raw_cell(cell: &Cell, outer_section: usize, outer_para: usize, doc: &Document) -> RawCell {
    let paragraphs = cell
        .paragraphs
        .iter()
        .map(|p| build_raw_paragraph(outer_section, outer_para, p, doc))
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

/// Picture 컨트롤 → raw 평탄 구조.
///
/// `bin_data_id` 는 상류 Picture 가 가리키는 BinData 인덱스 (1-based). extension /
/// has_content 는 doc.doc_info.bin_data_list 와 doc.bin_data_content 를 lookup 해서
/// 채운다. 0 (미할당) 또는 lookup 실패 시 image=None 으로 broken reference 표현.
fn build_raw_picture(
    pic: &Picture,
    section_idx: usize,
    para_idx: usize,
    doc: &Document,
) -> RawPicture {
    let bin_data_id = pic.image_attr.bin_data_id;
    let image = if bin_data_id == 0 {
        None
    } else {
        let bd_meta = doc
            .doc_info
            .bin_data_list
            .get((bin_data_id as usize).saturating_sub(1));
        let extension = bd_meta.and_then(|bd| bd.extension.clone());
        // ^ bin_data_content 는 Embedding 만 채워지므로 Link/Storage 는 false.
        //   상류 utils.rs::find_bin_data 와 동일한 인덱싱 (bin_data_id - 1).
        let has_content = doc
            .bin_data_content
            .get((bin_data_id as usize).saturating_sub(1))
            .is_some();
        Some(RawImageRef {
            bin_data_id,
            extension,
            has_content,
        })
    };
    let description = pic.caption.as_ref().and_then(extract_caption_text);
    RawPicture {
        section_idx,
        para_idx,
        image,
        description,
    }
}

/// 본문 paragraph 안의 Header/Footer 컨트롤을 furniture 리스트에 누적한다.
///
/// Header / Footer 가 가지는 자체 paragraphs 들을 외부 (section_idx, para_idx) 와
/// 공유한 RawParagraph 로 변환한다. 본 paragraphs 는 furniture 자체가 어디서
/// "선언" 됐는지 (Provenance) 만 보존하면 충분 — 페이지별 반복 출현은 렌더 단계.
fn collect_headers_footers_from_paragraph(
    section_idx: usize,
    para_idx: usize,
    para: &Paragraph,
    doc: &Document,
    headers: &mut Vec<RawParagraph>,
    footers: &mut Vec<RawParagraph>,
) {
    for ctrl in &para.controls {
        match ctrl {
            Control::Header(h) => {
                for hp in &h.paragraphs {
                    headers.push(build_raw_paragraph(section_idx, para_idx, hp, doc));
                }
            }
            Control::Footer(f) => {
                for fp in &f.paragraphs {
                    footers.push(build_raw_paragraph(section_idx, para_idx, fp, doc));
                }
            }
            _ => {}
        }
    }
}

/// Caption 에서 텍스트만 추출한다 (복합 캡션 구조는 미지원 — S3 CaptionBlock 에서 도입).
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

/// `bin_data_id` (1-based) 에 해당하는 raw bytes 를 반환.
///
/// 상류 `renderer/layout/utils.rs::find_bin_data` 와 동일한 lookup —
/// `bin_data_content` 는 Embedding 타입만 채워져 있고 인덱스는 1-based.
/// Embedding 이 아니거나 (`Link` / `Storage`) 누락 시 None.
///
/// **인덱스 정합성 가정**: `bin_data_content` 와 `bin_data_list` 는 같은 순서로
/// 같은 길이여야 한다 — 즉 모든 BinData entry 가 Embedding 타입이어야 정확.
/// 혼합 (Link + Embedding) 문서에서는 상류 `bin_data_content` 가 Embedding 만
/// 추려 더 짧으므로 잘못된 entry 를 반환할 수 있다 — 상류 renderer 도 같은
/// 가정을 공유하므로 SVG/PDF 렌더링도 같은 잘못된 lookup 을 한다 (상류 패리티).
pub(crate) fn lookup_bin_data_bytes(doc: &Document, bin_data_id: u16) -> Option<&[u8]> {
    if bin_data_id == 0 {
        return None;
    }
    doc.bin_data_content
        .get((bin_data_id as usize) - 1)
        .map(|bdc| bdc.data.as_slice())
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

    #[test]
    fn lookup_bin_data_zero_id_returns_none() {
        let doc = Document::default();
        assert!(lookup_bin_data_bytes(&doc, 0).is_none());
    }
}
