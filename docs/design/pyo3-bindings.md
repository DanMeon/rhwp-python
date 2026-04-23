# PyO3 Python 바인딩 구현 가이드 (Phase 1)

> **문서 목적**: rhwp를 PyPI 배포 가능한 Python 패키지로 만드는 작업의 기술 참조. 다른 Claude Code 세션이 이 문서를 기반으로 구현한다.
>
> **배경**: GitHub Issue [#227](https://github.com/edwardkim/rhwp/issues/227) 에서 시작. **사용자 Fork(`DanMeon/rhwp`)에서 독립 진행**하는 개인 패키지화 작업이다. 상류 리포(`edwardkim/rhwp`)에 PR 제출 여부는 별도 판단.
>
> **전제**: 이 문서 작성 전에 `pyo3-sandbox/`에서 기술 검증 완료 ([검증 문서 5종](../../pyo3-sandbox/docs/) 참조). 본 가이드는 그 결과를 현업 패턴과 대조해 정식 구현 청사진으로 정제한 것.

---

## 0. 불변 원칙 (CRITICAL CONSTRAINTS)

다음은 구현 전 과정에서 **절대 위반하면 안 되는** 제약이다. 위반 시 작업 중단 후 작업지시자 확인 필수.

### 0.1 rhwp 코어 무수정

| 경로 | 수정 가능? |
|------|----------|
| `/src/**/*.rs` (rhwp 본체) | ❌ **절대 수정 금지** |
| `/Cargo.toml` (루트) | ❌ **수정 금지** |
| `/pyproject.toml` (존재 시) | ❌ **수정 금지** |
| 새 디렉토리 (예: `/rhwp-python/` 또는 `/pyo3-bindings/`) | ✓ 자유 생성 |
| `/pyo3-sandbox/` | ✓ 참조만 (직접 복사 금지) |

**이유**: rhwp는 WASM 단일 스레드 타겟을 위한 설계 철학(예: `RefCell` 기반 interior mutability)을 가진다. 이를 변경하면 WASM 빌드·기존 소비자(Studio·Chrome·Safari 확장)가 회귀할 수 있음. 메인테이너 승인 없이 코어 설계 변경 금지.

**대응**: 새 크레이트를 만들어 rhwp를 **경로 의존성**(`rhwp = { path = ".." }`)으로 참조. PyO3 래퍼 레이어만 새 크레이트에 작성.

### 0.2 하이퍼-워터폴 프로세스 준수

프로젝트 `CLAUDE.md`의 워크플로우 준수:

1. 수행 계획서 (`mydocs/plans/task_m{마일스톤}_{이슈}.md`) 작성 → 승인
2. 구현 계획서 (`task_m{마일스톤}_{이슈}_impl.md`, 3~6단계) 작성 → 승인
3. 단계별 구현 → 단계별 완료 보고서 → 승인
4. 최종 보고서 → 승인

각 단계 완료 시 승인 없이 다음 단계 진행 금지.

### 0.3 기타 원칙

- 한글 문서 작성 (코드·LLM-facing 텍스트는 영어)
- Pydantic V2, Python 3.10+ 타입 유니언, `uv` 패키지 관리자
- PostToolUse 린트 훅(`ruff format`, `ruff check --fix`, `pyright`)이 자동 실행되므로 결과 확인만

---

## 1. 현업 패턴 조사 결과 (근거)

### 1.1 조사 대상

| 프로젝트 | 구조 | 참고 가치 |
|---------|-----|----------|
| [pydantic-core](https://github.com/pydantic/pydantic-core) | subdirectory + `python-source` | **최고 참조** (rhwp와 유사한 단일 리포 + 네이티브 코어) |
| [polars (py-polars)](https://github.com/pola-rs/polars/tree/main/py-polars) | subdirectory in workspace | 대규모 프로젝트 매뉴얼 빌드 관리 |
| [ruff](https://github.com/astral-sh/ruff) | workspace + crates/ | CLI·LSP 특수 형태, 부분 참고 |
| [tiktoken](https://github.com/openai/tiktoken) | flat + `tiktoken/` | 간단한 케이스 참조 |

### 1.2 공통 패턴

모든 성숙 프로젝트가 수렴하는 현업 관행:

1. **`python-source = "python"` + 명시적 Python 디렉토리** — 루트 네임스페이스 충돌 방지
2. **`module-name = "pkg._pkg"` (내부 submodule 감춤)** — 사용자는 `pkg.foo()`만 보고, Rust 네이티브 모듈은 `_pkg`로 숨김
3. **`crate-type = ["cdylib", "rlib"]`** — cdylib(Python 연결) + rlib(stub 생성 바이너리용)
4. **`abi3-py39` 또는 `abi3-py310`** — 단일 휠이 여러 Python 버전 커버
5. **`[profile.release] lto = "fat" + codegen-units = 1 + strip = true`** — 릴리즈 바이너리 최소화·최대 최적화
6. **`maturin-action`으로 멀티플랫폼 CI** — Linux(manylinux+musllinux)·macOS(x86·ARM)·Windows 매트릭스
7. **PyPI Trusted Publishing (OIDC)** — API 토큰 관리 탈피
8. **`py.typed` 마커 + `.pyi` 스텁 번들링** — PEP 561 준수
9. **`[dependency-groups]` (PEP 735)** — dev/test/lint 분리
10. **PGO(Profile-Guided Optimization)** — 성숙 단계에서 추가 (Phase 1 범위 외)

### 1.3 타입 스텁 생성 도구 (선택지)

| 도구 | 방식 | 권장도 |
|------|------|-------|
| 수동 작성 `.pyi` | 현재 sandbox 방식 | **Phase 1 권장** (API 작아서) |
| [pyo3-stub-gen](https://github.com/Jij-Inc/pyo3-stub-gen) | Rust 매크로 기반 자동 생성 | Phase 2+ (API 커지면) |
| [pyo3-stubgen](https://pypi.org/project/pyo3-stubgen/) | 런타임 introspection | 비권장 (정확도 낮음) |
| mypy `stubgen` | 범용 | 비권장 (PyO3 특화 아님) |

**결정**: Phase 1은 수동 `.pyi`. 이유 — API 표면 작음(10개 미만), 사용자 문서에 들어갈 docstring을 세밀하게 제어 필요, 의존성 최소화.

---

## 2. 프로젝트 구조 결정

### 2.1 선택지 비교

| 옵션 | 설명 | rhwp 적용 |
|------|-----|----------|
| A. Subdirectory crate | 리포 하위 `/rhwp-python/` 신설, 경로 의존 | **권장** |
| B. Cargo workspace + Python crate | 루트 `[workspace]` 선언, 멤버 등록 | 불가 (루트 Cargo.toml 수정 필요) |
| C. 별도 리포 | `edwardkim/rhwp-python` 신설 | 불가 (배포·버전 동기화 부담) |

### 2.2 결정: 옵션 A

**이유**:
- 원칙 0.1(코어 무수정)과 양립 가능
- pydantic-core의 검증된 패턴 (subdirectory에 Python 크레이트)
- 단일 리포 유지 → 버전·이슈·PR 관리 간결
- 배포 시점에 `cd rhwp-python && maturin build`만 하면 됨

### 2.3 최종 디렉토리 구조

```
rhwp/                                    # 루트 (기존, 무수정)
├── src/                                 # rhwp 코어 (무수정)
├── Cargo.toml                           # rhwp 코어 (무수정)
├── pyo3-sandbox/                        # 기존 실증 코드 (참고용)
└── rhwp-python/                         # 🆕 신설 — Phase 1 구현 위치
    ├── Cargo.toml                       # 바인딩 크레이트 manifest
    ├── pyproject.toml                   # Python 패키지 manifest
    ├── build.rs                         # (선택) 빌드 스크립트
    ├── README.md                        # 사용자용 문서
    ├── LICENSE                          # MIT (rhwp와 동일)
    ├── src/
    │   ├── lib.rs                       # PyO3 모듈 엔트리
    │   ├── document.rs                  # Document 클래스 바인딩
    │   ├── errors.rs                    # 예외 매핑
    │   └── version.rs                   # 버전 함수
    ├── python/
    │   └── rhwp/
    │       ├── __init__.py              # 재노출 + 고수준 Python API
    │       ├── __init__.pyi             # 타입 스텁
    │       └── py.typed                 # PEP 561 마커 (빈 파일)
    ├── tests/
    │   ├── test_parse.py
    │   ├── test_render.py
    │   ├── test_errors.py
    │   └── conftest.py
    ├── benches/                         # (선택) pytest-benchmark
    └── .github/workflows/
        └── release.yml                  # PyPI 배포 워크플로우
```

### 2.4 네이밍 규약

| 항목 | 값 | 근거 |
|------|----|------|
| PyPI 패키지명 | `rhwp` | 가장 기억하기 쉬움, 네임 선점 |
| import 이름 | `rhwp` | `import rhwp` |
| 내부 Rust 모듈 | `rhwp._rhwp` | pydantic-core 패턴 (`pydantic_core._pydantic_core`) |
| Cargo 크레이트 이름 | `rhwp-python` | PyPI와 구분 |
| cdylib 출력 이름 | `_rhwp` | `#[pymodule]` 함수명과 일치 |

**사용자 경험**:
```python
import rhwp                    # 공개 API
doc = rhwp.parse("a.hwp")      # 최상위 함수
# rhwp._rhwp는 접근 가능하지만 사용자 대상 아님 (밑줄 규약)
```

---

## 3. Cargo.toml 템플릿

**파일**: `rhwp-python/Cargo.toml`

```toml
[package]
name = "rhwp-python"
version = "0.1.0"                       # rhwp 코어와 별도 버전 (3.3 참조)
edition = "2021"
# * rust-version 미명시 — 루트 rhwp 정책 (stable Rust, MSRV unclaimed) 준수.
#   PyO3 0.28 이 Rust 1.83+ 요구하지만 이는 README 문서로 안내
license = "MIT"
description = "Python bindings for rhwp — HWP/HWPX parser and renderer"
repository = "https://github.com/edwardkim/rhwp"
readme = "README.md"
publish = false                          # crates.io 배포 대상 아님

# * sdist 포함 파일 제어 (pydantic-core 패턴)
include = [
    "/pyproject.toml",
    "/README.md",
    "/LICENSE",
    "/build.rs",
    "/src",
    "/python/rhwp",
    "/tests",
    "!__pycache__",
    "!*.so",
    "!*.pyd",
]

[lib]
name = "_rhwp"
crate-type = ["cdylib", "rlib"]          # cdylib: Python ext / rlib: 향후 stub_gen 바이너리용

[dependencies]
pyo3 = { version = "0.28", features = ["extension-module", "abi3-py39"] }
# ^ abi3-py39: Python 3.9+ 단일 휠로 전부 커버
rhwp = { path = ".." }                    # 코어 경로 의존성 (무수정 원칙)

[profile.release]
lto = "fat"                               # Link-Time Optimization 최대치
codegen-units = 1                         # 단일 코드 생성 유닛 → 더 공격적인 인라이닝
strip = true                              # 디버그 심볼 제거 (바이너리 크기 ↓)

[profile.bench]
# 릴리즈와 동일 최적화 수준 권장
```

**주의**:
- `[workspace]` 섹션 추가 금지 (루트 Cargo.toml과 충돌)
- `publish = false` — 실수로 `cargo publish` 방지 (PyPI 배포는 maturin 담당)
- `rhwp = { path = ".." }` 경로는 rhwp-python 디렉토리 기준 상대 경로

---

## 4. pyproject.toml 템플릿

**파일**: `rhwp-python/pyproject.toml`

pydantic-core 스타일을 rhwp에 맞춰 이식.

```toml
[build-system]
requires = ["maturin>=1.13,<2"]
build-backend = "maturin"

[project]
name = "rhwp"
description = "Parser and renderer for HWP/HWPX documents (Korean word processor format)"
requires-python = ">=3.9"
license = "MIT"
license-files = ["LICENSE"]
authors = [
    { name = "edwardkim", email = "..." },
    # Phase 1 기여자 추가 가능
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Rust",
    "Operating System :: POSIX :: Linux",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: MacOS",
    "Typing :: Typed",
    "Natural Language :: Korean",
    "Topic :: Office/Business :: Office Suites",
    "Topic :: Text Processing",
]
keywords = ["hwp", "hwpx", "hancom", "korean", "document", "parser"]
dynamic = ["version"]                    # Cargo.toml에서 가져옴

[project.urls]
Homepage = "https://github.com/edwardkim/rhwp"
Repository = "https://github.com/edwardkim/rhwp"
Issues = "https://github.com/edwardkim/rhwp/issues"

# * 옵셔널 익스트라 (선택적 통합, 필요 시 Phase 1.5)
[project.optional-dependencies]
langchain = ["langchain-core>=0.2"]

[dependency-groups]                      # PEP 735 (maturin 1.7+ 지원, PyO3 0.28은 maturin 1.13+ 필요)
dev = ["maturin>=1.13"]
testing = [
    {include-group = "dev"},
    "pytest>=8",
    "pytest-cov",
]
linting = [
    {include-group = "dev"},
    "ruff",
    "pyright",
]
all = [
    {include-group = "dev"},
    {include-group = "testing"},
    {include-group = "linting"},
]

[tool.maturin]
python-source = "python"
module-name = "rhwp._rhwp"
bindings = "pyo3"
features = ["pyo3/extension-module"]
include = [
    { path = "python/rhwp/py.typed", format = "wheel" },
    { path = "python/rhwp/*.pyi", format = "wheel" },
]

[tool.pytest.ini_options]
testpaths = ["tests"]
minversion = "8.0"
addopts = ["-ra", "--strict-markers"]
markers = [
    "slow: 느린 테스트 (PDF 렌더링 등)",
]

[tool.pyright]
venvPath = "."
venv = ".venv"
include = ["python", "tests"]
reportMissingImports = true
reportMissingTypeStubs = false

[tool.ruff]
line-length = 100
target-version = "py39"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B"]
```

**핵심 포인트**:
- `dynamic = ["version"]` + `Cargo.toml`의 version이 자동으로 반영됨 (maturin 기능)
- `module-name = "rhwp._rhwp"` — 내부 네이티브 모듈 숨김
- `python-source = "python"` — Python 소스 위치 명시
- `include`에 `py.typed`와 `*.pyi` 반드시 포함 → 휠에 타입 정보 번들

---

## 5. Rust 바인딩 코드 패턴

### 5.1 모듈 엔트리 (`src/lib.rs`)

```rust
use pyo3::prelude::*;

mod document;
mod errors;
mod version;

use document::PyDocument;

// ^ gil_used = true: free-threaded Python 비활성 (DocumentCore 내부 RefCell 캐시가 !Sync)
#[pymodule(gil_used = true)]
fn _rhwp(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // * 버전 함수
    m.add_function(wrap_pyfunction!(version::version, m)?)?;
    m.add_function(wrap_pyfunction!(version::rhwp_core_version, m)?)?;

    // * 최상위 함수
    m.add_function(wrap_pyfunction!(document::parse, m)?)?;

    // * 클래스
    m.add_class::<PyDocument>()?;

    Ok(())
}
```

**패턴**: 모듈 엔트리는 **등록만** 담당. 로직은 개별 모듈에 분산.

### 5.2 Document 클래스 (`src/document.rs`)

pyo3-sandbox의 `PyDocument`에서 이식. GIL 해제 적용분 포함.

```rust
use pyo3::exceptions::{PyIOError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

use crate::errors::{parse_error_to_py, ParseError};

// ^ unsendable: DocumentCore 내부 RefCell 필드로 !Sync — 다른 스레드 접근 시 런타임 패닉 방어
#[pyclass(name = "Document", module = "rhwp", unsendable)]
pub struct PyDocument {
    inner: rhwp::document_core::DocumentCore,
}

fn load_document(path: String) -> Result<rhwp::document_core::DocumentCore, ParseError> {
    let bytes = std::fs::read(&path).map_err(ParseError::Io)?;
    rhwp::document_core::DocumentCore::from_bytes(&bytes)
        .map_err(|e| ParseError::Parse(format!("{e:?}")))
}

#[pymethods]
impl PyDocument {
    #[new]
    fn new(py: Python<'_>, path: &str) -> PyResult<Self> {
        let path = path.to_owned();
        let doc = py
            .detach(move || load_document(path))
            .map_err(parse_error_to_py)?;
        Ok(PyDocument { inner: doc })
    }

    #[getter]
    fn section_count(&self) -> usize {
        self.inner.document().sections.len()
    }

    #[getter]
    fn paragraph_count(&self) -> usize {
        self.inner
            .document()
            .sections
            .iter()
            .map(|s| s.paragraphs.len())
            .sum()
    }

    #[getter]
    fn page_count(&self) -> u32 {
        self.inner.page_count()
    }

    fn extract_text(&self) -> String {
        self.inner
            .document()
            .sections
            .iter()
            .flat_map(|s| s.paragraphs.iter())
            .map(|p| p.text.as_str())
            .filter(|t| !t.is_empty())
            .collect::<Vec<_>>()
            .join("\n")
    }

    fn paragraphs(&self) -> Vec<String> {
        self.inner
            .document()
            .sections
            .iter()
            .flat_map(|s| s.paragraphs.iter())
            .map(|p| p.text.clone())
            .collect()
    }

    fn render_svg(&self, page: u32) -> PyResult<String> {
        self.inner
            .render_page_svg_native(page)
            .map_err(|e| PyValueError::new_err(format!("render page {page} failed: {e:?}")))
    }

    fn render_all_svg(&self) -> PyResult<Vec<String>> {
        self.render_all_svg_internal()
    }

    #[pyo3(signature = (output_dir, prefix=None))]
    fn export_svg(&self, output_dir: &str, prefix: Option<&str>) -> PyResult<Vec<String>> {
        let out_dir = std::path::Path::new(output_dir);
        std::fs::create_dir_all(out_dir).map_err(|e| PyIOError::new_err(e.to_string()))?;

        let page_count = self.inner.page_count();
        let stem = prefix.unwrap_or("page");
        let mut written = Vec::with_capacity(page_count as usize);
        for page in 0..page_count {
            let svg = self.inner.render_page_svg_native(page).map_err(|e| {
                PyValueError::new_err(format!("render page {page} failed: {e:?}"))
            })?;
            let filename = if page_count == 1 {
                format!("{stem}.svg")
            } else {
                format!("{stem}_{:03}.svg", page + 1)
            };
            let path = out_dir.join(&filename);
            std::fs::write(&path, &svg).map_err(|e| PyIOError::new_err(e.to_string()))?;
            written.push(path.to_string_lossy().into_owned());
        }
        Ok(written)
    }

    fn render_pdf<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        let svgs = self.render_all_svg_internal()?;
        let bytes = py
            .detach(move || rhwp::renderer::pdf::svgs_to_pdf(&svgs))
            .map_err(|e| PyValueError::new_err(format!("PDF conversion failed: {e}")))?;
        Ok(PyBytes::new(py, &bytes))
    }

    fn export_pdf(&self, py: Python<'_>, output_path: &str) -> PyResult<usize> {
        let svgs = self.render_all_svg_internal()?;
        let output_path = output_path.to_owned();
        py.detach(move || -> PyResult<usize> {
            let bytes = rhwp::renderer::pdf::svgs_to_pdf(&svgs)
                .map_err(|e| PyValueError::new_err(format!("PDF conversion failed: {e}")))?;
            std::fs::write(&output_path, &bytes)
                .map_err(|e| PyIOError::new_err(e.to_string()))?;
            Ok(bytes.len())
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "Document(sections={}, paragraphs={}, pages={})",
            self.section_count(),
            self.paragraph_count(),
            self.page_count()
        )
    }
}

// * 내부 헬퍼 (not exposed to Python)
impl PyDocument {
    fn render_all_svg_internal(&self) -> PyResult<Vec<String>> {
        let page_count = self.inner.page_count();
        (0..page_count)
            .map(|p| {
                self.inner
                    .render_page_svg_native(p)
                    .map_err(|e| PyValueError::new_err(format!("render page {p} failed: {e:?}")))
            })
            .collect()
    }
}

#[pyfunction]
pub fn parse(py: Python<'_>, path: &str) -> PyResult<PyDocument> {
    PyDocument::new(py, path)
}
```

### 5.3 에러 매핑 (`src/errors.rs`)

```rust
use pyo3::exceptions::{PyIOError, PyValueError};
use pyo3::PyErr;

pub enum ParseError {
    Io(std::io::Error),
    Parse(String),
}

pub fn parse_error_to_py(e: ParseError) -> PyErr {
    match e {
        ParseError::Io(err) => PyIOError::new_err(err.to_string()),
        ParseError::Parse(msg) => PyValueError::new_err(format!("parse failed: {msg}")),
    }
}
```

### 5.4 버전 함수 (`src/version.rs`)

```rust
use pyo3::prelude::*;

#[pyfunction]
pub fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[pyfunction]
pub fn rhwp_core_version() -> String {
    rhwp::version()
}
```

---

## 6. Python 모듈 레이아웃

### 6.1 `python/rhwp/__init__.py`

pydantic-core 패턴 + 고수준 래퍼 추가.

```python
"""rhwp — HWP/HWPX parser and renderer."""
from __future__ import annotations

from ._rhwp import (
    Document,
    parse,
    rhwp_core_version,
    version,
)

__all__ = [
    "Document",
    "parse",
    "version",
    "rhwp_core_version",
]
```

### 6.2 `python/rhwp/__init__.pyi`

pyo3-sandbox의 스텁 이식 + docstring 강화.

```python
"""rhwp — HWP/HWPX parser and renderer (Korean word processor format)."""

__all__ = [
    "Document",
    "parse",
    "version",
    "rhwp_core_version",
]


def version() -> str:
    """rhwp Python 패키지 버전 (예: "0.1.0")."""
    ...


def rhwp_core_version() -> str:
    """rhwp Rust 코어 버전 (예: "0.7.3")."""
    ...


def parse(path: str) -> Document:
    """HWP5 또는 HWPX 파일을 파싱하여 Document 반환.

    Args:
        path: HWP 또는 HWPX 파일 경로.

    Returns:
        파싱된 Document.

    Raises:
        OSError: 파일을 열 수 없을 때.
        ValueError: 파일 포맷이 유효하지 않을 때.
    """
    ...


class Document:
    """파싱된 HWP/HWPX 문서.

    직접 생성자를 호출하거나 :func:`parse` 를 사용할 수 있다.
    """

    section_count: int
    """섹션 수."""

    paragraph_count: int
    """전체 섹션에 걸친 총 문단 수."""

    page_count: int
    """페이지네이션 후 총 페이지 수."""

    def __init__(self, path: str) -> None:
        """HWP/HWPX 파일 경로로부터 파싱.

        Raises:
            OSError: 파일을 열 수 없을 때.
            ValueError: 파일 포맷이 유효하지 않을 때.
        """
        ...

    def extract_text(self) -> str:
        """전체 문서의 텍스트를 `\\n`으로 연결해 반환 (빈 문단 제외)."""
        ...

    def paragraphs(self) -> list[str]:
        """모든 문단의 텍스트 리스트 (빈 문단 포함, len == paragraph_count)."""
        ...

    def render_svg(self, page: int) -> str:
        """특정 페이지를 SVG 문자열로 렌더링.

        Args:
            page: 0-based 페이지 인덱스.

        Raises:
            ValueError: 페이지 인덱스가 범위를 벗어났거나 렌더링 실패 시.
        """
        ...

    def render_all_svg(self) -> list[str]:
        """모든 페이지를 SVG 문자열 리스트로 렌더링."""
        ...

    def export_svg(self, output_dir: str, prefix: str | None = None) -> list[str]:
        """모든 페이지를 SVG 파일로 저장.

        Args:
            output_dir: 출력 디렉토리 (자동 생성).
            prefix: 파일명 접두사 (기본 "page"). 다중 페이지 시 `{prefix}_{NNN}.svg`.

        Returns:
            생성된 파일 경로 리스트.
        """
        ...

    def render_pdf(self) -> bytes:
        """전체 문서를 PDF 바이트로 렌더링."""
        ...

    def export_pdf(self, output_path: str) -> int:
        """문서를 PDF 파일로 저장.

        Returns:
            저장된 바이트 수.
        """
        ...

    def __repr__(self) -> str: ...
```

### 6.3 `python/rhwp/py.typed`

빈 파일. PEP 561 마커.

```bash
touch python/rhwp/py.typed
```

---

## 7. 테스트 전략

### 7.1 pytest 구조

```
tests/
├── conftest.py              # 공용 fixture
├── test_parse.py            # 파싱 기본
├── test_text_extraction.py  # 텍스트 API
├── test_svg_rendering.py    # SVG API
├── test_pdf_rendering.py    # PDF API (@pytest.mark.slow)
├── test_errors.py           # 에러 전파
├── test_types.py            # pyright 스텁 검증
└── samples/                 # 테스트용 HWP 파일 (소용량만)
    ├── simple.hwp
    └── simple.hwpx
```

**중요**: 기존 `/samples/`의 대용량 파일은 테스트에 사용하지 말 것. 작은 fixture 파일만 `tests/samples/`에 새로 만들거나 선택 (CI 시간 최소화).

### 7.2 주요 테스트 케이스

pyo3-sandbox의 테스트를 이식하되:
- `import rhwp_sandbox` → `import rhwp`
- `rhwp_sandbox.parse` → `rhwp.parse`
- 모듈 네임 변경만으로 대부분 그대로 작동

### 7.3 pyright 검증

`tests/test_types.py`에 의도된 타입 오류 케이스 포함. `pyright --outputjson | jq '.summary.errorCount'` 로 검증.

---

## 8. CI/CD 전략

### 8.1 워크플로우 구성 (`.github/workflows/release.yml`)

pydantic-core의 구조를 간략화한 버전:

```yaml
name: Release

on:
  push:
    tags: ["python-v*"]                   # 태그 트리거 (rhwp 코어와 구분)
  pull_request:
    paths:
      - "rhwp-python/**"
      - ".github/workflows/release.yml"

permissions:
  contents: read

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python: ["3.9", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - uses: dtolnay/rust-toolchain@stable
      - uses: PyO3/maturin-action@v1
        with:
          command: develop
          args: --release
          working-directory: rhwp-python
      - run: pip install pytest pyright
      - run: cd rhwp-python && pytest
      - run: cd rhwp-python && pyright tests/

  build-linux:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        target: [x86_64, aarch64]
    steps:
      - uses: actions/checkout@v4
      - uses: PyO3/maturin-action@v1
        with:
          target: ${{ matrix.target }}
          manylinux: auto
          args: --release --out dist
          working-directory: rhwp-python
      - uses: actions/upload-artifact@v4
        with:
          name: wheels-linux-${{ matrix.target }}
          path: rhwp-python/dist/*.whl

  build-macos:
    runs-on: macos-latest
    strategy:
      matrix:
        target: [x86_64, aarch64]
    steps:
      - uses: actions/checkout@v4
      - uses: PyO3/maturin-action@v1
        with:
          target: ${{ matrix.target }}
          args: --release --out dist
          working-directory: rhwp-python
      - uses: actions/upload-artifact@v4
        with:
          name: wheels-macos-${{ matrix.target }}
          path: rhwp-python/dist/*.whl

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: PyO3/maturin-action@v1
        with:
          args: --release --out dist
          working-directory: rhwp-python
      - uses: actions/upload-artifact@v4
        with:
          name: wheels-windows
          path: rhwp-python/dist/*.whl

  sdist:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: PyO3/maturin-action@v1
        with:
          command: sdist
          args: --out dist
          working-directory: rhwp-python
      - uses: actions/upload-artifact@v4
        with:
          name: sdist
          path: rhwp-python/dist/*.tar.gz

  # NOTE: 외부 저장소 publish job 은 Phase 1 범위 외.
  #   빌드 산출물은 Actions artifact 로만 업로드하여 로컬 검증에 활용.
  #   외부 배포(PyPI 등)는 상류 메인테이너 합의 후 별도 단계로 진행.

  verify-wheel:
    # ^ 각 빌드된 wheel 을 클린 venv 에서 설치해 end-to-end 검증
    needs: [build-linux, build-macos, build-windows]
    if: startsWith(github.ref, 'refs/tags/') || github.event_name == 'workflow_dispatch'
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            artifact: wheels-linux-x86_64
          - os: macos-latest
            artifact: wheels-macos-aarch64
          - os: windows-latest
            artifact: wheels-windows
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - uses: actions/download-artifact@v4
        with:
          name: ${{ matrix.artifact }}
          path: dist
      - run: pip install dist/*.whl
      - run: python -c "import rhwp; print(rhwp.version())"
```

### 8.2 외부 저장소 publish 범위 외

Phase 1 은 빌드 산출물을 **Actions artifact 로만** 업로드한다. PyPI·TestPyPI 포함 어떠한 외부 저장소에도 자동 publish 하지 않음. 이유:

- 이름 선점 / 브랜드 혼동 방지 — 상류 메인테이너 합의 전 외부 업로드 금지
- OIDC Trusted Publisher 설정도 Phase 1 에서는 하지 않음 (publish job 자체가 없으므로 불필요)
- 배포가 필요한 시점 (Phase 2+) 에 별도 workflow 파일로 분리하여 관리

---

## 9. 버전 관리

### 9.1 버전 정책

| 항목 | 값 |
|------|-----|
| 초기 버전 | `0.1.0` (rhwp 0.7.x와 **독립**) |
| Semver 준수 | ✓ |
| Phase 1 목표 버전 | `0.1.x` (alpha) |
| Stable 목표 | `1.0.0` (Phase 3 이후) |

**독립 버전을 선택한 이유**: rhwp Python 바인딩은 독자적 제품 수명 주기를 가짐. 코어가 0.8.0 → 0.9.0으로 가도 바인딩 API가 그대로면 0.1.5 → 0.2.0 으로 독립 증가 가능.

### 9.2 태그 규약

- Python 패키지: `python-v0.1.0`
- rhwp 코어 릴리즈: 기존 `v0.7.3` 유지
- 워크플로우가 `python-v*`만 트리거

### 9.3 CHANGELOG

`rhwp-python/CHANGELOG.md` 별도 유지. Keep a Changelog 포맷.

---

## 10. 단계별 구현 계획 (Phase 1)

아래 단계를 **순차** 진행. 각 단계 완료 시 작업지시자(사용자) 승인 후 다음 단계로. 좁은 범위부터 시작해서 한 단계씩 확장한다.

### Stage 0: 최소 증명 (半日)

**목적**: 프로젝트 구조가 현업 패턴에 부합하는지 빠르게 검증. 전체 API를 만들기 전에 **뼈대만** 세워서 빌드/임포트 경로가 올바른지 확인.

**범위**: **`rhwp.version()`만 동작**. 그 외 API 전부 제외.

**산출물**:
- `rhwp-python/Cargo.toml` (최소)
- `rhwp-python/pyproject.toml` (최소)
- `rhwp-python/src/lib.rs` — `version()` 하나만 노출
- `rhwp-python/python/rhwp/__init__.py` — 재노출
- `rhwp-python/python/rhwp/__init__.pyi` — 타입 스텁 (version만)
- `rhwp-python/python/rhwp/py.typed`
- `rhwp-python/README.md` (짧게)
- `mydocs/working/task_m{M}_{이슈}_stage0.md`

**완료 기준**:
```bash
cd rhwp-python && maturin develop
python -c "import rhwp; print(rhwp.version())"
# → 0.1.0
```

### Stage 1: 프로젝트 구조 + 최소 빌드 성공 (1~2일)

**목표**: `maturin develop` 성공 + `import rhwp; rhwp.version()` 작동

**산출물**:
- `rhwp-python/` 디렉토리 신설
- `Cargo.toml`, `pyproject.toml`, `README.md`, `LICENSE`
- `src/lib.rs`, `src/version.rs` (최소)
- `python/rhwp/__init__.py`, `__init__.pyi`, `py.typed`
- `tests/test_smoke.py` (`rhwp.version()` 검증만)
- `mydocs/working/task_m{M}_{이슈}_stage1.md`

**완료 기준**:
```bash
cd rhwp-python && maturin develop && python -c "import rhwp; print(rhwp.version())"
# → 0.1.0
```

### Stage 2: 파싱 + 텍스트 API (1~2일)

**목표**: `parse(path) → Document`, `extract_text`, `paragraphs`, getters 동작

**산출물**:
- `src/document.rs`, `src/errors.rs`
- `python/rhwp/__init__.pyi` 업데이트
- `tests/test_parse.py`, `test_text_extraction.py`, `test_errors.py`
- `mydocs/working/task_m{M}_{이슈}_stage2.md`

**완료 기준**: pytest 전부 통과, pyright 0 errors

### Stage 3: SVG/PDF 렌더링 API (1~2일)

**목표**: `render_svg`, `render_all_svg`, `export_svg`, `render_pdf`, `export_pdf`

**산출물**:
- `src/document.rs` 렌더링 메서드 추가
- `tests/test_svg_rendering.py`, `test_pdf_rendering.py`
- `mydocs/working/task_m{M}_{이슈}_stage3.md`

### Stage 4: GIL 해제 + 성능 벤치 (1일)

**목표**: `parse`/`render_pdf`에 `py.detach` 적용, 벤치로 검증

**산출물**:
- `src/document.rs`, `src/errors.rs` GIL 해제 리팩터
- `benches/` 또는 `scripts/bench.py` (ThreadPoolExecutor 비교)
- `mydocs/working/task_m{M}_{이슈}_stage4.md`

**완료 기준**: 단일 vs 4스레드 parse 실측 1.5배 이상

### Stage 5: CI/CD 파이프라인 (2~3일)

**목표**: GitHub Actions 워크플로우 구성, wheel 빌드 + clean venv install 검증

**산출물**:
- `.github/workflows/rhwp-python-release.yml` (test + build + verify-wheel, 외부 publish job 없음)
- `rhwp-python/README.md` 사용자용 완성 (source install 안내)
- CI 에서 빌드된 wheel 을 clean venv 에 install + import 검증
- `mydocs/working/task_m{M}_{이슈}_stage5.md`

**완료 기준**:
```bash
# CI 에서 (verify-wheel job)
pip install dist/*.whl
python -c "import rhwp; print(rhwp.version())"
# → 정상 동작. 외부 저장소 publish 는 Phase 1 범위 외
```

### Stage 6: 문서 + 최종 보고서 (1일)

**목표**: 사용자 문서 정비, 최종 보고서 작성

**산출물**:
- `rhwp-python/README.md` 완성
- `rhwp-python/docs/quickstart.md` (선택)
- `mydocs/report/task_m{M}_{이슈}_report.md`

### 총 예상 기간

**6~11일** (단독 작업 기준, 각 승인 대기 시간 별도).

---

## 11. 검증 체크리스트 (Phase 1 완료 기준)

```
[ ] rhwp 코어(`/src/`, 루트 `Cargo.toml`) 수정 이력 없음 (git log 확인)
[ ] `cd rhwp-python && maturin develop --release` 성공
[ ] `python -c "import rhwp"` 성공
[ ] pytest 전체 통과 (core + langchain extras 없이)
[ ] pyright 0 errors on 정상 케이스
[ ] pyright 의도된 오류 케이스 전부 검출
[ ] `maturin build --release` 성공, wheel 생성
[ ] 새 venv에서 `pip install <wheel>` + import + parse 성공
[ ] CI: Linux/macOS/Windows 3개 플랫폼 녹색 (test + wheel build + verify-wheel)
[ ] `verify-wheel` job — 각 OS clean venv 에서 wheel install + import 성공
[ ] 외부 저장소 publish 이력 0건 (workflow grep 확인)
[ ] README.md 사용자 기준 실행 가능한 예제 포함
[ ] samples/aift.hwp 파싱 → 텍스트 추출 → SVG 렌더 → PDF 내보내기 전체 동작
[ ] 각 Stage 완료 보고서 (`mydocs/working/`) 존재
[ ] 최종 보고서 (`mydocs/report/`) 작성 완료
```

---

## 12. 흔한 함정 및 해결

### 12.1 wasm-bindgen 공존

**현상**: rhwp 코어가 `wasm_bindgen::prelude::*`를 top-level에서 사용. 네이티브 빌드에서 혼란 가능.

**해결**: 이미 sandbox에서 검증됨 — 네이티브 타겟(`cfg(not(target_arch = "wasm32"))`)은 wasm-bindgen 영향 없음. **그대로 두고 추가 작업 불필요**.

### 12.2 `Vec<u8>` vs `bytes`

**현상**: PyO3 기본 변환에서 `Vec<u8>`이 Python `list[int]`로 노출됨. `bytes`로 하려면 명시 필요.

**해결**: `PyBytes::new(py, &vec)` 사용 (5.2절 render_pdf 참고).

### 12.3 `RefCell` 기반 !Sync + `#[pyclass(unsendable)]`

**현상 1 — 컴파일 에러 (`#[pyclass]` Sync 요구)**:
PyO3 0.23+ 에서 `#[pyclass]` 기본값은 `T: Sync` 요구. `DocumentCore` 는 `RefCell<Vec<Option<PageRenderTree>>>` 등 `!Sync` 필드를 가지므로 컴파일 실패.

**해결 1**: `#[pyclass(..., unsendable)]` 지정. 타 스레드 접근 시 **런타임 패닉**으로 보호 (컴파일은 통과).

```rust
#[pyclass(name = "Document", module = "rhwp", unsendable)]
pub struct PyDocument { ... }
```

**현상 2 — `py.detach` 클로저 캡처 에러**: `&DocumentCore`를 `py.detach` 클로저에 넘기면 `!Send` 로 컴파일 에러.

**해결 2**: 코어 무수정 원칙하에서:
- `parse()` — 새 `DocumentCore`를 클로저 내부에서 생성만 → OK
- `render_pdf()` PDF 변환 단계 — 소유권 있는 `Vec<String>` 전달 → OK
- 기타 메서드 — GIL 유지 (sandbox 결과와 동일)

**현상 3 — free-threaded Python 기본 허용 (PyO3 0.27+)**: `#[pymodule]` 기본값이 free-threaded 허용. `RefCell` 기반 단일 스레드 설계와 충돌 가능.

**해결 3**: `#[pymodule(gil_used = true)]` 로 명시 GIL 요구.

상세: [gil_release.md](../../pyo3-sandbox/docs/gil_release.md).

### 12.4 GIL 반환값 타입 실수

**현상**: `render_pdf`가 `list[int]` 반환 (bytes 아님). 사용자 실망.

**해결**: 반환 타입을 `Bound<'py, PyBytes>`로 명시. 테스트에서 `isinstance(result, bytes)` 확인.

### 12.5 Python/Rust 버전 불일치

**현상**: `rhwp.version()`과 `rhwp.rhwp_core_version()` 헷갈림.

**해결**: 함수명 명확화 + docstring 명시. `.pyi` 파일에 각 함수 예시 포함.

### 12.6 maturin develop 시 venv 미감지

**현상**: CI에서 `maturin develop` 실행 시 venv 미감지로 시스템 Python에 설치 시도.

**해결**: `VIRTUAL_ENV` 환경변수 명시 또는 `--python` 플래그 사용.

### 12.7 abi3 휠 태그 오류

**현상**: `cp39-abi3-*` 휠이 특정 Python 버전에서 거부됨.

**해결**: `abi3-py39` feature가 정확히 `Python 3.9 이상`만 지원함을 보장. CI 매트릭스에 3.9 포함.

---

## 13. 참고 자료

### 13.1 이 리포 내 참고

- [pyo3-sandbox/](../../pyo3-sandbox/) — 이미 검증된 실증 코드
- [pyo3-sandbox/docs/benchmark.md](../../pyo3-sandbox/docs/benchmark.md) — 성능 기준선
- [pyo3-sandbox/docs/gil_release.md](../../pyo3-sandbox/docs/gil_release.md) — GIL 해제 상세
- [pyo3-sandbox/docs/pyhwp_comparison.md](../../pyo3-sandbox/docs/pyhwp_comparison.md) — 경쟁 분석
- GitHub Issue [#227](https://github.com/edwardkim/rhwp/issues/227)

### 13.2 외부 참고

| 주제 | URL |
|------|-----|
| PyO3 공식 가이드 | https://pyo3.rs/ |
| maturin 사용자 가이드 | https://www.maturin.rs/ |
| maturin-action | https://github.com/PyO3/maturin-action |
| pydantic-core (최고 참조) | https://github.com/pydantic/pydantic-core |
| py-polars | https://github.com/pola-rs/polars/tree/main/py-polars |
| pyo3-stub-gen (Phase 2+ 고려) | https://github.com/Jij-Inc/pyo3-stub-gen |
| PEP 561 (py.typed) | https://peps.python.org/pep-0561/ |
| PEP 735 (dependency-groups) | https://peps.python.org/pep-0735/ |
| PyPI Trusted Publishing | https://docs.pypi.org/trusted-publishers/ |

---

## 14. 문서 변경 이력

| 날짜 | 변경 | 작성 |
|------|------|------|
| 2026-04-21 | 초안 작성 (현업 패턴 조사 + Phase 1 청사진) | Claude (sandbox 세션) |

---

## 다음 Claude 세션에 전하는 메모

이 문서 기반으로 작업 시작 시 다음 순서 권장:

### 1. **작업 시작 전 선결**

- 본 문서 전체 정독
- [pyo3-sandbox/docs/](../../pyo3-sandbox/docs/) 의 5개 문서 훑어보기
- `pyo3-sandbox/src/lib.rs`, `pyo3-sandbox/pyproject.toml`, `pyo3-sandbox/Cargo.toml` 읽고 현재 검증된 바인딩 파악
- 현재 Fork 상태 (`git remote -v`, `git log`)로 브랜치·원격 확인

### 2. **수행 계획서 작성**

- `mydocs/plans/task_m{마일스톤}_{이슈번호}.md`
- 본 문서의 10절(단계별 구현 계획)을 기반으로 일정·담당·산출물 구체화
- 작업지시자 승인 요청

### 3. **구현 계획서 작성**

- `mydocs/plans/task_m{마일스톤}_{이슈번호}_impl.md`
- 최소 3단계, 최대 6단계 (본 문서 10절의 Stage 0~6을 기반으로 실제 프로젝트 상황에 맞춰 재구성)
- 각 단계의 파일 변경 목록·검증 방법 상세화

### 4. **구현은 Stage 0부터 순차 진행**

- Stage 0 (최소 증명)이 **가장 중요** — 이게 구조 검증의 첫 지점
- 각 Stage 완료마다 보고서 작성·작업지시자 승인
- `pyo3-sandbox/` 소스를 **복사하지 말 것**. 본 문서의 5~6절 템플릿을 기반으로 직접 작성
- 모든 변경은 `rhwp-python/` 내부에서만 (원칙 0.1)

### 5. **좁게, 천천히**

- 본 문서의 검증 체크리스트(11절)는 Phase 1 **최종** 목표. 중간 단계에서는 훨씬 작은 단위로 쪼개서 진행
- 의심스러울 때는 "한 스테이지 더 잘게 쪼개기" 쪽으로 결정
- 하이퍼-워터폴 방법론 → 속도보다 **작업지시자와의 합의·검증 우선**

### 6. **막힐 경우**

- 먼저 [pyo3-sandbox/](../../pyo3-sandbox/)에서 유사 사례 찾기
- 그 다음 pydantic-core 실제 코드 참조
- 그래도 안 풀리면 작업지시자에게 질문

### 7. **다음 세션은 이 문서를 읽고 쓸 수 있다**

본 문서는 버전 관리되는 가이드. 구현 중 발견한 이슈·결정사항은 **본 문서의 14절 변경 이력에 추가**하고, 해당 섹션 본문도 업데이트해 다음 사람에게 전달.
