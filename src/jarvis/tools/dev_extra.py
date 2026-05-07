"""개발 도구 확장 — git advanced, npm, pip, brew, docker, vscode, line count."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool


def _run(cmd: list, cwd: str = "", timeout: int = 15) -> str:
    try:
        r = subprocess.run(
            cmd,
            cwd=cwd or None,
            capture_output=True, text=True, timeout=timeout,
        )
        return (r.stdout or r.stderr).strip()
    except Exception as e:
        return f"ERROR: {e}"


# ── Git advanced ──────────────────────────────────────────────────────────
def _git_branch_list(cwd: str = ".") -> str:
    return _run(["git", "branch", "-a", "--sort=-committerdate"], cwd) or "(no branches)"


def _git_stash_list(cwd: str = ".") -> str:
    return _run(["git", "stash", "list"], cwd) or "(no stashes)"


def _git_remote_info(cwd: str = ".") -> str:
    return _run(["git", "remote", "-v"], cwd) or "(no remotes)"


def _git_recent_commits(cwd: str = ".", limit: int = 10) -> str:
    return _run(
        ["git", "log", f"-{limit}", "--pretty=format:%h  %an  %ar  %s"],
        cwd,
    ) or "(no commits)"


def _git_blame_line(path: str, line: int) -> str:
    return _run(["git", "blame", "-L", f"{line},{line}", path]) or "(no blame)"


def _git_changed_files(cwd: str = ".") -> str:
    out = _run(["git", "status", "--short"], cwd)
    return out or "(clean)"


REGISTRY.register(Tool(
    name="git_branch_list",
    description="git 브랜치 list (최근 commit 순).",
    input_schema={"type": "object", "properties": {"cwd": {"type": "string"}}, "required": []},
    handler=_git_branch_list,
))
REGISTRY.register(Tool(
    name="git_stash_list",
    description="git stash list.",
    input_schema={"type": "object", "properties": {"cwd": {"type": "string"}}, "required": []},
    handler=_git_stash_list,
))
REGISTRY.register(Tool(
    name="git_remote_info",
    description="git 원격 저장소 정보 (remote -v).",
    input_schema={"type": "object", "properties": {"cwd": {"type": "string"}}, "required": []},
    handler=_git_remote_info,
))
REGISTRY.register(Tool(
    name="git_recent_commits",
    description="최근 N개 commit 한 줄 요약.",
    input_schema={
        "type": "object",
        "properties": {
            "cwd": {"type": "string"},
            "limit": {"type": "integer", "description": "기본 10"},
        },
        "required": [],
    },
    handler=_git_recent_commits,
))
REGISTRY.register(Tool(
    name="git_blame_line",
    description="특정 파일의 line N에 대한 git blame.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "line": {"type": "integer"},
        },
        "required": ["path", "line"],
    },
    handler=_git_blame_line,
))
REGISTRY.register(Tool(
    name="git_changed_files",
    description="git status --short (변경된 파일 list).",
    input_schema={"type": "object", "properties": {"cwd": {"type": "string"}}, "required": []},
    handler=_git_changed_files,
))


# ── npm / pip / brew ─────────────────────────────────────────────────────
def _npm_outdated(cwd: str = ".") -> str:
    return _run(["npm", "outdated"], cwd, timeout=30) or "(none outdated)"


def _pip_outdated() -> str:
    return _run(["pip", "list", "--outdated"], timeout=30) or "(none outdated)"


def _brew_outdated() -> str:
    return _run(["brew", "outdated", "--verbose"], timeout=30) or "(none outdated)"


def _brew_list() -> str:
    return _run(["brew", "list", "--formula"], timeout=30)


def _brew_info(formula: str) -> str:
    return _run(["brew", "info", formula], timeout=15)


REGISTRY.register(Tool(
    name="npm_outdated",
    description="npm 패키지 outdated list (현재 디렉토리).",
    input_schema={"type": "object", "properties": {"cwd": {"type": "string"}}, "required": []},
    handler=_npm_outdated,
))
REGISTRY.register(Tool(
    name="pip_outdated",
    description="pip outdated 패키지 list.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_pip_outdated,
))
REGISTRY.register(Tool(
    name="brew_outdated",
    description="Homebrew outdated formula list.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_brew_outdated,
))
REGISTRY.register(Tool(
    name="brew_list",
    description="설치된 brew formula list.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_brew_list,
))
REGISTRY.register(Tool(
    name="brew_info",
    description="brew formula 상세 정보.",
    input_schema={
        "type": "object",
        "properties": {"formula": {"type": "string"}},
        "required": ["formula"],
    },
    handler=_brew_info,
))


# ── Docker ────────────────────────────────────────────────────────────────
def _docker_ps() -> str:
    return _run(["docker", "ps", "-a", "--format",
                 "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"], timeout=10)


def _docker_logs(name: str, lines: int = 50) -> str:
    return _run(["docker", "logs", "--tail", str(lines), name], timeout=15)


def _docker_images() -> str:
    return _run(["docker", "images", "--format",
                 "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}"], timeout=10)


REGISTRY.register(Tool(
    name="docker_ps",
    description="Docker 컨테이너 list (모든 상태).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_docker_ps,
))
REGISTRY.register(Tool(
    name="docker_logs",
    description="Docker 컨테이너 로그 tail.",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "lines": {"type": "integer", "description": "기본 50"},
        },
        "required": ["name"],
    },
    handler=_docker_logs,
))
REGISTRY.register(Tool(
    name="docker_images",
    description="Docker 이미지 list.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_docker_images,
))


# ── Editor open ──────────────────────────────────────────────────────────
def _editor_open(path: str, editor: str = "code") -> str:
    """vscode/cursor 등 외부 CLI로 열기."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    if subprocess.run(["which", editor], capture_output=True).returncode != 0:
        return f"ERROR: '{editor}' CLI not found in PATH"
    try:
        subprocess.Popen([editor, str(p)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"OK: opened {p} in {editor}"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="editor_open",
    description="외부 에디터 CLI로 파일/폴더 열기 (code/cursor/subl 등).",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "editor": {"type": "string", "description": "기본 'code'"},
        },
        "required": ["path"],
    },
    handler=_editor_open,
))


# ── Line count by language ──────────────────────────────────────────────
def _loc_count(path: str = ".") -> str:
    """간단 LoC 통계 — 확장자별 파일/라인."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__",
                 ".next", "dist", "build", ".cache", ".tox"}
    counts: dict = {}
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            ext = Path(f).suffix.lower() or "(no ext)"
            try:
                with open(Path(root) / f, "r", encoding="utf-8", errors="ignore") as fp:
                    lines = sum(1 for _ in fp)
            except Exception:
                continue
            cur = counts.setdefault(ext, [0, 0])
            cur[0] += 1
            cur[1] += lines
    if not counts:
        return "(no source files)"
    rows = sorted(counts.items(), key=lambda x: -x[1][1])[:20]
    out = [f"{'ext':<10s} {'files':>7s} {'lines':>10s}"]
    for ext, (nf, nl) in rows:
        out.append(f"{ext:<10s} {nf:>7d} {nl:>10d}")
    out.append(f"{'TOTAL':<10s} {sum(c[0] for c in counts.values()):>7d} {sum(c[1] for c in counts.values()):>10d}")
    return "\n".join(out)


REGISTRY.register(Tool(
    name="loc_count",
    description="디렉토리 LoC 통계 (확장자별 파일수+라인수, 빌드폴더 제외).",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "기본 현재 dir"}},
        "required": [],
    },
    handler=_loc_count,
))


# ── Project size ────────────────────────────────────────────────────────
def _project_size(path: str = ".", depth: int = 1) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    try:
        r = subprocess.run(
            ["du", "-h", "-d", str(depth), str(p)],
            capture_output=True, text=True, timeout=20,
        )
        lines = r.stdout.strip().splitlines()
        # Sort by size descending — humans-readable size sort hack
        lines.sort(key=lambda x: x.split()[0])
        return "\n".join(lines[:30])
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="project_size",
    description="디렉토리 크기 (du -h, depth 기본 1).",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "depth": {"type": "integer", "description": "기본 1"},
        },
        "required": [],
    },
    handler=_project_size,
))
