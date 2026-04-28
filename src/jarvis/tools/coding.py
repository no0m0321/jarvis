"""코딩 도구 — Python/Node/Ruby/Bash 실행, 포맷, lint."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool


def _run_python(code: str, timeout: int = 30) -> str:
    """Python 코드 실행. stdout/stderr/exit_code."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        result = subprocess.run(
            ["python3", path],
            capture_output=True, text=True, timeout=timeout,
        )
        out = [f"exit={result.returncode}"]
        if result.stdout:
            out.append(f"--- stdout ---\n{result.stdout.rstrip()}")
        if result.stderr:
            out.append(f"--- stderr ---\n{result.stderr.rstrip()}")
        return "\n".join(out) if len(out) > 1 else out[0]
    finally:
        Path(path).unlink(missing_ok=True)


REGISTRY.register(Tool(
    name="run_python",
    description="Python 3 코드 임시파일 실행. stdout/stderr/exit_code 반환.",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "timeout": {"type": "integer", "description": "기본 30초"},
        },
        "required": ["code"],
    },
    handler=_run_python,
))


def _run_node(code: str, timeout: int = 30) -> str:
    """Node.js 코드 실행."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        result = subprocess.run(
            ["node", path],
            capture_output=True, text=True, timeout=timeout,
        )
        out = [f"exit={result.returncode}"]
        if result.stdout:
            out.append(f"--- stdout ---\n{result.stdout.rstrip()}")
        if result.stderr:
            out.append(f"--- stderr ---\n{result.stderr.rstrip()}")
        return "\n".join(out) if len(out) > 1 else out[0]
    except FileNotFoundError:
        return "ERROR: node 미설치 (`brew install node`)"
    finally:
        Path(path).unlink(missing_ok=True)


REGISTRY.register(Tool(
    name="run_node",
    description="Node.js 코드 실행. stdout/stderr 반환.",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "timeout": {"type": "integer"},
        },
        "required": ["code"],
    },
    handler=_run_node,
))


def _run_ruby(code: str, timeout: int = 30) -> str:
    """Ruby 코드 실행."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        result = subprocess.run(
            ["ruby", path],
            capture_output=True, text=True, timeout=timeout,
        )
        out = [f"exit={result.returncode}"]
        if result.stdout:
            out.append(f"--- stdout ---\n{result.stdout.rstrip()}")
        if result.stderr:
            out.append(f"--- stderr ---\n{result.stderr.rstrip()}")
        return "\n".join(out) if len(out) > 1 else out[0]
    except FileNotFoundError:
        return "ERROR: ruby 미설치"
    finally:
        Path(path).unlink(missing_ok=True)


REGISTRY.register(Tool(
    name="run_ruby",
    description="Ruby 코드 실행.",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "timeout": {"type": "integer"},
        },
        "required": ["code"],
    },
    handler=_run_ruby,
))


def _format_python(code: str) -> str:
    """Python 코드 black/ruff format. 둘 다 없으면 원본 반환."""
    if subprocess.run(["which", "ruff"], capture_output=True).returncode == 0:
        try:
            result = subprocess.run(
                ["ruff", "format", "-"],
                input=code, capture_output=True, text=True, timeout=10, check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"FORMAT_FAILED: {e.stderr}\n--- ORIGINAL ---\n{code}"
    if subprocess.run(["which", "black"], capture_output=True).returncode == 0:
        try:
            result = subprocess.run(
                ["black", "-q", "-"],
                input=code, capture_output=True, text=True, timeout=10, check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"FORMAT_FAILED: {e.stderr}\n--- ORIGINAL ---\n{code}"
    return f"WARN: ruff/black 미설치. 원본 반환:\n{code}"


REGISTRY.register(Tool(
    name="format_python",
    description="Python 코드 포맷 (ruff > black > 원본).",
    input_schema={
        "type": "object",
        "properties": {"code": {"type": "string"}},
        "required": ["code"],
    },
    handler=_format_python,
))


def _lint_python(code: str) -> str:
    """Python 코드 lint (ruff check)."""
    if subprocess.run(["which", "ruff"], capture_output=True).returncode != 0:
        return "WARN: ruff 미설치. `pip install ruff`"
    try:
        result = subprocess.run(
            ["ruff", "check", "-"],
            input=code, capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() or "(no issues)"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="lint_python",
    description="Python 코드 lint (ruff check).",
    input_schema={
        "type": "object",
        "properties": {"code": {"type": "string"}},
        "required": ["code"],
    },
    handler=_lint_python,
))


def _run_typescript(code: str, timeout: int = 60) -> str:
    """TypeScript 코드 ts-node 또는 tsx로 실행. 둘 다 없으면 ts-node 안내."""
    runner = None
    for cmd in ("tsx", "ts-node"):
        if subprocess.run(["which", cmd], capture_output=True).returncode == 0:
            runner = cmd
            break
    if not runner:
        return "ERROR: tsx 또는 ts-node 미설치 (`npm i -g tsx`)"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        result = subprocess.run(
            [runner, path],
            capture_output=True, text=True, timeout=timeout,
        )
        out = [f"exit={result.returncode}"]
        if result.stdout:
            out.append(f"--- stdout ---\n{result.stdout.rstrip()}")
        if result.stderr:
            out.append(f"--- stderr ---\n{result.stderr.rstrip()}")
        return "\n".join(out)
    finally:
        Path(path).unlink(missing_ok=True)


REGISTRY.register(Tool(
    name="run_typescript",
    description="TypeScript 코드 실행 (tsx/ts-node).",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "timeout": {"type": "integer"},
        },
        "required": ["code"],
    },
    handler=_run_typescript,
))


def _run_swift(code: str, timeout: int = 60) -> str:
    """Swift 코드 실행 (swift CLI)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".swift", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        result = subprocess.run(
            ["swift", path],
            capture_output=True, text=True, timeout=timeout,
        )
        out = [f"exit={result.returncode}"]
        if result.stdout:
            out.append(f"--- stdout ---\n{result.stdout.rstrip()}")
        if result.stderr:
            out.append(f"--- stderr ---\n{result.stderr.rstrip()}")
        return "\n".join(out)
    except FileNotFoundError:
        return "ERROR: swift 미설치 (Xcode CLT 필요: `xcode-select --install`)"
    finally:
        Path(path).unlink(missing_ok=True)


REGISTRY.register(Tool(
    name="run_swift",
    description="Swift 코드 실행 (swift CLI).",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "timeout": {"type": "integer"},
        },
        "required": ["code"],
    },
    handler=_run_swift,
))


def _which(cmd: str) -> str:
    """명령 위치 확인 (which). 미설치면 NOT_FOUND."""
    result = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=3)
    return result.stdout.strip() or f"NOT_FOUND: {cmd}"


REGISTRY.register(Tool(
    name="which",
    description="명령 위치 확인 (which command).",
    input_schema={
        "type": "object",
        "properties": {"cmd": {"type": "string"}},
        "required": ["cmd"],
    },
    handler=_which,
))


def _man_page(cmd: str, lines: int = 50) -> str:
    """man page 첫 N라인."""
    try:
        result = subprocess.run(
            ["man", cmd],
            capture_output=True, text=True, timeout=10,
            env={"MANPAGER": "cat", "PAGER": "cat", "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
        )
        if result.returncode != 0:
            return f"ERROR: {result.stderr.strip()[:200]}"
        # ANSI escape 제거
        import re
        text = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
        text = re.sub(r".\x08", "", text)
        return "\n".join(text.splitlines()[:lines])
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="man_page",
    description="man page 첫 N라인 (ANSI 제거).",
    input_schema={
        "type": "object",
        "properties": {
            "cmd": {"type": "string"},
            "lines": {"type": "integer", "description": "기본 50"},
        },
        "required": ["cmd"],
    },
    handler=_man_page,
))


def _markdown_render(text: str, output_path: str = "") -> str:
    """Markdown → HTML (pandoc 필요)."""
    if subprocess.run(["which", "pandoc"], capture_output=True).returncode != 0:
        return "ERROR: pandoc 미설치 (`brew install pandoc`)"
    if not output_path:
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            output_path = f.name
    try:
        subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "html", "-o", output_path],
            input=text, text=True, timeout=10, check=True,
        )
        return f"OK: {output_path}"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="markdown_render",
    description="Markdown 텍스트를 HTML 파일로 변환 (pandoc).",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "output_path": {"type": "string"},
        },
        "required": ["text"],
    },
    handler=_markdown_render,
))
