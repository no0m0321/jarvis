"""파일 처리 — PDF/docx 읽기, Excel/CSV, 이미지 변환, markdown."""
from __future__ import annotations

import csv
import json
import os
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from jarvis.tools.registry import REGISTRY, Tool


def _pdf_read(path: str, max_pages: int = 50) -> str:
    """PDF 텍스트 추출 — pypdf 우선, 없으면 macOS textutil."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"파일 없음: {p}"
    # 1) pypdf
    try:
        from pypdf import PdfReader  # type: ignore
        r = PdfReader(str(p))
        pages = []
        for i, page in enumerate(r.pages[:max_pages]):
            try:
                pages.append(f"\n--- p.{i+1} ---\n{page.extract_text() or ''}")
            except Exception:
                pages.append(f"\n--- p.{i+1} ---\n(추출 실패)")
        return "".join(pages)[:30000]
    except ImportError:
        pass
    # 2) macOS pdftotext (poppler) 시도
    for cmd in (["pdftotext", str(p), "-"], ["mdls", "-name", "kMDItemTextContent", str(p)]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout[:30000]
        except FileNotFoundError:
            continue
    return "PDF 추출 도구 없음 — pip install pypdf 또는 brew install poppler"


def _docx_read(path: str) -> str:
    """docx 텍스트 추출 (zip + xml 직접 파싱, 의존성 0)."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"파일 없음: {p}"
    try:
        with zipfile.ZipFile(p) as z:
            with z.open("word/document.xml") as f:
                tree = ET.parse(f)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for para in tree.iter(f"{{{ns['w']}}}p"):
            texts = [t.text or "" for t in para.iter(f"{{{ns['w']}}}t")]
            paragraphs.append("".join(texts))
        return "\n".join(paragraphs)[:30000]
    except Exception as e:
        return f"docx 실패: {e}"


def _xlsx_read(path: str, sheet: int = 0, max_rows: int = 100) -> str:
    """xlsx 읽기 — openpyxl 있으면 사용, 없으면 zip 파싱."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"파일 없음: {p}"
    try:
        from openpyxl import load_workbook  # type: ignore
        wb = load_workbook(str(p), read_only=True, data_only=True)
        ws = wb.worksheets[sheet] if isinstance(sheet, int) else wb[sheet]
        rows = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= max_rows:
                break
            rows.append([str(c) if c is not None else "" for c in row])
        return json.dumps({"sheet": ws.title, "rows": rows}, ensure_ascii=False)
    except ImportError:
        return "openpyxl 미설치 — pip install openpyxl"
    except Exception as e:
        return f"xlsx 실패: {e}"


def _csv_read(path: str, max_rows: int = 100, delimiter: str = ",") -> str:
    """CSV 읽기 + JSON 반환."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"파일 없음: {p}"
    try:
        with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f, delimiter=delimiter)
            rows = []
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                rows.append(row)
        return json.dumps(rows, ensure_ascii=False)
    except Exception as e:
        return f"CSV 실패: {e}"


def _csv_write(path: str, rows_json: str, delimiter: str = ",") -> str:
    """CSV 쓰기. rows_json: '[[a,b],[c,d]]' 형식."""
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        rows = json.loads(rows_json)
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=delimiter)
            w.writerows(rows)
        return f"OK: {p} ({len(rows)} rows)"
    except Exception as e:
        return f"실패: {e}"


def _image_resize(path: str, width: int = 0, height: int = 0, output: str = "") -> str:
    """이미지 리사이즈 — macOS sips 사용 (no Python deps)."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"파일 없음: {p}"
    out = Path(output).expanduser() if output else p.parent / f"{p.stem}_resized{p.suffix}"
    args = ["sips"]
    if width and not height:
        args += ["--resampleWidth", str(width)]
    elif height and not width:
        args += ["--resampleHeight", str(height)]
    elif width and height:
        args += ["-z", str(height), str(width)]
    else:
        return "width 또는 height 지정 필요"
    args += [str(p), "--out", str(out)]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return f"OK: {out}"
        return f"실패: {r.stderr.strip()[:200]}"
    except Exception as e:
        return f"오류: {e}"


def _image_convert(path: str, fmt: str = "png", output: str = "") -> str:
    """이미지 포맷 변환 (sips). fmt: png/jpeg/heic/tiff."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"파일 없음: {p}"
    out = Path(output).expanduser() if output else p.with_suffix(f".{fmt}")
    fmt_map = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg", "heic": "heic", "tiff": "tiff"}
    target = fmt_map.get(fmt.lower(), "png")
    try:
        r = subprocess.run(
            ["sips", "-s", "format", target, str(p), "--out", str(out)],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0:
            return f"OK: {out}"
        return f"실패: {r.stderr.strip()[:200]}"
    except Exception as e:
        return f"오류: {e}"


def _markdown_to_html(markdown_text: str) -> str:
    """Markdown → HTML — Python markdown 모듈 또는 fallback."""
    try:
        import markdown  # type: ignore
        return markdown.markdown(markdown_text, extensions=["fenced_code", "tables", "nl2br"])
    except ImportError:
        # fallback — 매우 단순
        import re
        html = markdown_text
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.M)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.M)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.M)
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)
        html = html.replace("\n", "<br>")
        return f"<html><body>{html}</body></html>"


def _zip_extract(zip_path: str, dest: str = "") -> str:
    """zip 파일 압축 해제."""
    p = Path(zip_path).expanduser()
    if not p.exists():
        return f"파일 없음: {p}"
    out = Path(dest).expanduser() if dest else p.parent / p.stem
    out.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(p) as z:
            z.extractall(out)
        return f"OK: {out} ({len(z.namelist())} 파일)"
    except Exception as e:
        return f"실패: {e}"


def _zip_create(source_paths_json: str, output_zip: str) -> str:
    """파일/디렉토리 list를 zip으로 묶음. source_paths_json: '[\"a\",\"b/dir\"]'."""
    try:
        sources = json.loads(source_paths_json)
        out = Path(output_zip).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for src in sources:
                p = Path(src).expanduser()
                if p.is_file():
                    z.write(p, p.name)
                elif p.is_dir():
                    for f in p.rglob("*"):
                        if f.is_file():
                            z.write(f, str(f.relative_to(p.parent)))
        return f"OK: {out} ({out.stat().st_size}B)"
    except Exception as e:
        return f"실패: {e}"


REGISTRY.register(Tool(
    name="pdf_read",
    description="PDF 텍스트 추출. pypdf → poppler → mdls 순 fallback.",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}, "max_pages": {"type": "integer", "default": 50}},
        "required": ["path"],
    },
    handler=_pdf_read,
))
REGISTRY.register(Tool(
    name="docx_read",
    description="Word docx 텍스트 추출 (의존성 0).",
    input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    handler=_docx_read,
))
REGISTRY.register(Tool(
    name="xlsx_read",
    description="Excel xlsx 읽기 (openpyxl 필요). sheet: 인덱스(int) 또는 이름.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "sheet": {"type": "integer", "default": 0},
            "max_rows": {"type": "integer", "default": 100},
        },
        "required": ["path"],
    },
    handler=_xlsx_read,
))
REGISTRY.register(Tool(
    name="csv_read",
    description="CSV 파일 → JSON 배열.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "max_rows": {"type": "integer", "default": 100},
            "delimiter": {"type": "string", "default": ","},
        },
        "required": ["path"],
    },
    handler=_csv_read,
))
REGISTRY.register(Tool(
    name="csv_write",
    description="CSV 파일 쓰기. rows_json: JSON 2D 배열 문자열.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "rows_json": {"type": "string"},
            "delimiter": {"type": "string", "default": ","},
        },
        "required": ["path", "rows_json"],
    },
    handler=_csv_write,
))
REGISTRY.register(Tool(
    name="image_resize",
    description="이미지 크기 변경 (macOS sips). width 또는 height 단독, 또는 둘 다.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "width": {"type": "integer", "default": 0},
            "height": {"type": "integer", "default": 0},
            "output": {"type": "string", "default": ""},
        },
        "required": ["path"],
    },
    handler=_image_resize,
))
REGISTRY.register(Tool(
    name="image_convert",
    description="이미지 포맷 변환. fmt: png/jpeg/heic/tiff.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "fmt": {"type": "string", "default": "png"},
            "output": {"type": "string", "default": ""},
        },
        "required": ["path"],
    },
    handler=_image_convert,
))
REGISTRY.register(Tool(
    name="markdown_to_html",
    description="Markdown 텍스트를 HTML로 변환.",
    input_schema={
        "type": "object",
        "properties": {"markdown_text": {"type": "string"}},
        "required": ["markdown_text"],
    },
    handler=_markdown_to_html,
))
REGISTRY.register(Tool(
    name="zip_extract",
    description="zip 압축 해제.",
    input_schema={
        "type": "object",
        "properties": {"zip_path": {"type": "string"}, "dest": {"type": "string", "default": ""}},
        "required": ["zip_path"],
    },
    handler=_zip_extract,
))
REGISTRY.register(Tool(
    name="zip_create",
    description="파일/디렉토리 묶어서 zip 생성. source_paths_json: '[\"a\",\"b/dir\"]'.",
    input_schema={
        "type": "object",
        "properties": {
            "source_paths_json": {"type": "string"},
            "output_zip": {"type": "string"},
        },
        "required": ["source_paths_json", "output_zip"],
    },
    handler=_zip_create,
))
