"""파일 작업 — tree, grep, diff, wc, archive, find."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool

_SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
         ".mypy_cache", ".ruff_cache", ".next", "dist", "build"}


def _tree(path: str = ".", max_depth: int = 3) -> str:
    """디렉토리 tree 출력 (max_depth 레벨)."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"NOT_FOUND: {path}"
    out: list[str] = []
    base_depth = len(p.parts)

    def walk(d: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(d.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        except PermissionError:
            return
        for e in entries:
            if e.name in _SKIP or e.name.startswith("."):
                continue
            indent = "  " * (depth - 1)
            mark = "📁" if e.is_dir() else "  "
            out.append(f"{indent}{mark} {e.name}")
            if e.is_dir() and depth < max_depth:
                walk(e, depth + 1)

    out.append(str(p))
    walk(p, 1)
    return "\n".join(out[:200]) + ("\n(truncated)" if len(out) > 200 else "")


REGISTRY.register(Tool(
    name="tree",
    description="디렉토리 tree (skip .git/.venv/node_modules 등). max_depth 기본 3.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "max_depth": {"type": "integer"},
        },
        "required": [],
    },
    handler=_tree,
))


def _grep(pattern: str, path: str = ".", file_glob: str = "*",
          max_results: int = 50, ignore_case: bool = True) -> str:
    """파일 내용 정규식 검색 (rg if available, else grep)."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"NOT_FOUND: {path}"
    if subprocess.run(["which", "rg"], capture_output=True).returncode == 0:
        cmd = ["rg", "--no-heading", "-n"]
        if ignore_case:
            cmd.append("-i")
        cmd += ["--max-count", str(max_results), pattern, str(p)]
    else:
        # fallback grep
        cmd = ["grep", "-rn"]
        if ignore_case:
            cmd.append("-i")
        cmd += [pattern, str(p)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        out = result.stdout.strip().splitlines()[:max_results]
        return "\n".join(out) if out else f"(no matches for '{pattern}')"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="grep",
    description="파일 내용 검색 (ripgrep > grep). 정규식 지원.",
    input_schema={
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string"},
            "file_glob": {"type": "string"},
            "max_results": {"type": "integer"},
            "ignore_case": {"type": "boolean"},
        },
        "required": ["pattern"],
    },
    handler=_grep,
))


def _diff_files(path1: str, path2: str) -> str:
    """두 파일 unified diff."""
    p1, p2 = Path(path1).expanduser(), Path(path2).expanduser()
    if not p1.exists() or not p2.exists():
        return f"NOT_FOUND: {p1 if not p1.exists() else p2}"
    try:
        result = subprocess.run(
            ["diff", "-u", str(p1), str(p2)],
            capture_output=True, text=True, timeout=10,
        )
        out = result.stdout[:5000]
        if not out:
            return "(identical)"
        return out + ("\n(truncated)" if len(result.stdout) > 5000 else "")
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="diff_files",
    description="두 파일 unified diff (max 5KB 출력).",
    input_schema={
        "type": "object",
        "properties": {
            "path1": {"type": "string"},
            "path2": {"type": "string"},
        },
        "required": ["path1", "path2"],
    },
    handler=_diff_files,
))


def _wc(path: str) -> str:
    """파일 라인/단어/문자 수."""
    p = Path(path).expanduser()
    if not p.exists() or not p.is_file():
        return f"NOT_FILE: {path}"
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.count("\n")
        words = len(text.split())
        chars = len(text)
        return f"lines: {lines}\nwords: {words}\nchars: {chars}"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="wc",
    description="파일 lines/words/chars 카운트.",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
    handler=_wc,
))


def _zip_create(source: str, dest: str = "") -> str:
    """디렉토리/파일을 zip으로. dest 비우면 source.zip."""
    src = Path(source).expanduser()
    if not src.exists():
        return f"NOT_FOUND: {source}"
    if not dest:
        dest = str(src) + ".zip"
    try:
        subprocess.run(
            ["zip", "-rq", dest, str(src.name)],
            cwd=str(src.parent),
            capture_output=True, timeout=120, check=True,
        )
        size = Path(dest).stat().st_size
        return f"OK: {dest} ({size:,} bytes)"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="zip_create",
    description="디렉토리/파일을 zip 압축. dest 비우면 source.zip.",
    input_schema={
        "type": "object",
        "properties": {
            "source": {"type": "string"},
            "dest": {"type": "string"},
        },
        "required": ["source"],
    },
    handler=_zip_create,
))


def _delete_path(path: str, force: bool = False) -> str:
    """파일/빈 디렉토리 삭제. force=true면 디렉토리 재귀 삭제."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"NOT_FOUND: {path}"
    try:
        if p.is_file() or p.is_symlink():
            p.unlink()
            return f"OK: deleted file {p}"
        if p.is_dir():
            if force:
                import shutil
                shutil.rmtree(p)
                return f"OK: deleted directory (recursive) {p}"
            try:
                p.rmdir()
                return f"OK: deleted empty directory {p}"
            except OSError:
                return f"ERROR: directory not empty (use force=true for recursive)"
    except Exception as e:
        return f"ERROR: {e}"
    return "ERROR: unknown path type"


REGISTRY.register(Tool(
    name="delete_path",
    description="파일/디렉토리 삭제. force=true 시 디렉토리 재귀. ⚠ 위험.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "force": {"type": "boolean", "description": "true면 rm -rf"},
        },
        "required": ["path"],
    },
    handler=_delete_path,
))


def _move_path(src: str, dest: str) -> str:
    """파일/디렉토리 이동/이름변경."""
    s = Path(src).expanduser()
    d = Path(dest).expanduser()
    if not s.exists():
        return f"NOT_FOUND: {src}"
    try:
        s.rename(d)
        return f"OK: {s} → {d}"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="move_path",
    description="파일/디렉토리 이동 또는 이름 변경.",
    input_schema={
        "type": "object",
        "properties": {
            "src": {"type": "string"},
            "dest": {"type": "string"},
        },
        "required": ["src", "dest"],
    },
    handler=_move_path,
))
