"""Cross-platform 시스템 도구 + Windows 전용 도구.

신규 4개 도구:
- system_open_path        cross-platform: 파일/폴더 열기 (macOS=open, Windows=startfile, Linux=xdg-open)
- system_show_in_folder   cross-platform: 파일 위치 reveal (macOS=open -R, Windows=explorer /select, Linux=xdg-open parent)
- windows_run_powershell  Windows 전용: PowerShell 명령 실행 (apple_script의 Windows 등가물)
- windows_outlook_compose Windows 전용: Outlook COM으로 메일 초안 (mail_compose의 Windows 등가물)

graceful 분기:
- Windows-only 핸들러는 @windows_only로 macOS/Linux에서 한국어 ERROR 반환
- cross-platform 핸들러는 OS별 로직을 직접 분기
"""
from __future__ import annotations

import os
import shlex
import subprocess
import webbrowser
from pathlib import Path

from jarvis.platform import IS_LINUX, IS_MACOS, IS_WINDOWS, windows_only
from jarvis.tools.registry import REGISTRY, Tool


# ──────────────── system_open_path (cross-platform) ────────────────
def _system_open_path(path: str) -> str:
    """로컬 파일/폴더를 OS 기본 앱(또는 파일 탐색기)으로 열기.

    URL은 받지 않음 — URL 열기는 기존 `open_url` 도구 사용.
    """
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    target = str(p)
    try:
        if IS_MACOS:
            subprocess.run(["open", target], timeout=5, check=True)
            return f"OK: opened {target}"
        if IS_WINDOWS:
            os.startfile(target)  # type: ignore[attr-defined]
            return f"OK: opened {target}"
        # Linux
        if IS_LINUX:
            subprocess.run(["xdg-open", target], timeout=5, check=True)
            return f"OK: opened {target}"
        # 마지막 fallback
        webbrowser.open(target)
        return f"OK: opened {target} (webbrowser fallback)"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e}"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


REGISTRY.register(Tool(
    name="system_open_path",
    description=(
        "로컬 파일/폴더를 OS 기본 앱으로 열기 (cross-platform). "
        "macOS: open, Windows: startfile, Linux: xdg-open. URL은 open_url 사용."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "파일 또는 디렉토리 절대/상대 경로 (예: ~/Downloads)"},
        },
        "required": ["path"],
    },
    handler=_system_open_path,
))


# ──────────────── system_show_in_folder (cross-platform) ────────────────
def _system_show_in_folder(path: str) -> str:
    """파일을 파일 탐색기에서 select 상태로 표시 (포함된 폴더 열고 해당 파일 강조).

    macOS: open -R (Finder reveal)
    Windows: explorer /select,<path>
    Linux: 부모 폴더만 xdg-open (대부분 file manager는 select 옵션 미지원)
    """
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    target = str(p)
    try:
        if IS_MACOS:
            subprocess.run(["open", "-R", target], timeout=5, check=True)
            return f"OK: revealed {target} in Finder"
        if IS_WINDOWS:
            # explorer /select 는 일반적으로 returncode 1이지만 정상 동작 → check=False
            subprocess.run(["explorer", f"/select,{target}"], timeout=5, check=False)
            return f"OK: revealed {target} in Explorer"
        if IS_LINUX:
            parent = str(p.parent if p.is_file() else p)
            subprocess.run(["xdg-open", parent], timeout=5, check=True)
            return f"OK: opened parent folder {parent} (Linux file manager는 select 미지원)"
        return "ERROR: unsupported OS"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e}"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


REGISTRY.register(Tool(
    name="system_show_in_folder",
    description=(
        "파일을 파일 탐색기에서 select/reveal (cross-platform). "
        "macOS: Finder reveal (open -R), Windows: Explorer /select, Linux: 부모 폴더 열기."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "파일 절대/상대 경로"},
        },
        "required": ["path"],
    },
    handler=_system_show_in_folder,
))


# ──────────────── windows_run_powershell (Windows 전용) ────────────────
@windows_only
def _windows_run_powershell(script: str, timeout: int = 30) -> str:
    """임의 PowerShell 명령 실행 (apple_script의 Windows 등가물).

    NoProfile + ExecutionPolicy Bypass 로 빠르게 실행. stdout 반환.
    """
    if not script.strip():
        return "ERROR: empty script"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            return f"ERROR: {(result.stderr or result.stdout).strip()[:500]}"
        return result.stdout.strip() or "(empty)"
    except subprocess.TimeoutExpired:
        return f"TIMEOUT (>{timeout}s)"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


REGISTRY.register(Tool(
    name="windows_run_powershell",
    description=(
        "임의 PowerShell 명령 실행 (Windows 전용 — apple_script의 Windows 등가물). "
        "NoProfile + ExecutionPolicy Bypass로 실행. stdout 반환."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "script": {"type": "string", "description": "PowerShell 스크립트 내용"},
            "timeout": {"type": "integer", "description": "초, 기본 30"},
        },
        "required": ["script"],
    },
    handler=_windows_run_powershell,
))


# ──────────────── windows_outlook_compose (Windows 전용) ────────────────
@windows_only
def _windows_outlook_compose(to: str, subject: str = "", body: str = "") -> str:
    """Outlook 새 메일 초안 창을 띄움 (mail_compose의 Windows 등가물).

    pywin32 + Outlook COM 사용. 발송은 사용자가 직접 (안전).
    """
    try:
        import win32com.client  # type: ignore
    except ImportError:
        return "ERROR: pywin32 미설치 — `pip install pywin32`"
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)  # 0 = olMailItem
        mail.To = to
        mail.Subject = subject
        mail.Body = body
        mail.Display()
        return f"OK: drafted to {to} in Outlook (창 열림, 발송은 직접 ⌘+Enter 또는 Send 버튼)"
    except Exception as e:
        # COM 호출 실패 fallback: mailto 스킴 (제한된 본문 길이)
        try:
            from urllib.parse import quote
            url = f"mailto:{to}?subject={quote(subject)}&body={quote(body)}"
            os.startfile(url)  # type: ignore[attr-defined]
            return f"OK: opened mailto fallback (Outlook COM 실패: {e})"
        except Exception as e2:
            return f"ERROR: Outlook COM 실패: {e}, mailto fallback 실패: {e2}"


REGISTRY.register(Tool(
    name="windows_outlook_compose",
    description=(
        "Outlook 새 메일 초안 창 (Windows 전용 — mail_compose의 Windows 등가물). "
        "발송은 사용자 직접. pywin32 필요. 실패 시 mailto fallback."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "받는 사람 이메일"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["to"],
    },
    handler=_windows_outlook_compose,
))


# 모듈 import 시 무용 — silence linter
_ = shlex
