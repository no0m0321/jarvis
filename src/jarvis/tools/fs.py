from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool

_SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".next", "dist", "build",
}


def _read_file(path: str, max_bytes: int = 100_000) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"NOT_FOUND: {path}"
    if not p.is_file():
        return f"NOT_FILE: {path}"
    data = p.read_bytes()[:max_bytes]
    text = data.decode("utf-8", errors="replace")
    suffix = "\n…[truncated]" if p.stat().st_size > max_bytes else ""
    return text + suffix


def _write_file(path: str, content: str, append: bool = False) -> str:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with p.open(mode, encoding="utf-8") as f:
        n = f.write(content)
    return f"OK: wrote {n} chars to {p}"


def _list_dir(path: str = ".") -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"NOT_FOUND: {path}"
    if not p.is_dir():
        return f"NOT_DIR: {path}"
    items = []
    for entry in sorted(p.iterdir()):
        kind = "d" if entry.is_dir() else "f"
        size = entry.stat().st_size if entry.is_file() else 0
        items.append(f"{kind} {size:>10}  {entry.name}")
    return "\n".join(items) or "(empty)"


def _search_files(pattern: str, root: str = ".", max_results: int = 50) -> str:
    p = Path(root).expanduser()
    if not p.exists():
        return f"NOT_FOUND: {root}"
    matches = []
    for dirpath, dirnames, filenames in os.walk(p):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if fnmatch.fnmatch(fn, pattern):
                matches.append(os.path.join(dirpath, fn))
                if len(matches) >= max_results:
                    return "\n".join(matches) + f"\n(stopped at {max_results})"
    return "\n".join(matches) or "(no matches)"


REGISTRY.register(Tool(
    name="read_file",
    description="파일 내용 읽기 (UTF-8, 기본 최대 100KB).",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "파일 경로 (~ 확장 지원)"},
            "max_bytes": {"type": "integer", "description": "최대 바이트, 기본 100000"},
        },
        "required": ["path"],
    },
    handler=_read_file,
))

REGISTRY.register(Tool(
    name="write_file",
    description="파일 쓰기 또는 append. 부모 디렉토리 자동 생성.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
            "append": {"type": "boolean", "description": "true면 append, 기본 false"},
        },
        "required": ["path", "content"],
    },
    handler=_write_file,
))

REGISTRY.register(Tool(
    name="list_dir",
    description="디렉토리 항목 목록 (이름·크기·종류).",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "디렉토리 경로, 기본 '.'"},
        },
        "required": [],
    },
    handler=_list_dir,
))

REGISTRY.register(Tool(
    name="search_files",
    description="glob 패턴으로 파일명 재귀 검색 (.git/.venv/node_modules 등 제외).",
    input_schema={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "glob 패턴 (예: '*.py')"},
            "root": {"type": "string", "description": "검색 시작 디렉토리, 기본 '.'"},
            "max_results": {"type": "integer", "description": "최대 결과 수, 기본 50"},
        },
        "required": ["pattern"],
    },
    handler=_search_files,
))
