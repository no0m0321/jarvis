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


# ──────────────── system_screenshot_to_file (cross-platform via mss) ────────────────
def _system_screenshot_to_file(path: str = "", display: int = 0) -> str:
    """전체 화면을 PNG 파일로 캡처. mss 라이브러리 사용 (mac/win/linux 모두).

    path 미지정 시 ~/.jarvis/screenshots/jarvis-YYYYMMDD-HHMMSS.png 자동 생성.
    display=0은 모든 모니터, 1+는 특정 모니터.
    """
    try:
        import mss  # type: ignore
        import mss.tools  # type: ignore
    except ImportError:
        return "ERROR: mss 미설치"

    if not path:
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_dir = Path.home() / ".jarvis" / "screenshots"
        out_dir.mkdir(parents=True, exist_ok=True)
        target_path = out_dir / f"jarvis-{ts}.png"
    else:
        target_path = Path(path).expanduser()
        target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with mss.mss() as sct:
            mons = sct.monitors  # [0]은 가상 전체, [1]+는 개별 모니터
            if display < 0 or display >= len(mons):
                return f"ERROR: display={display} 범위 밖 ({len(mons)-1} 개 모니터)"
            sshot = sct.grab(mons[display])
            mss.tools.to_png(sshot.rgb, sshot.size, output=str(target_path))
        return f"OK: {target_path} ({sshot.size[0]}x{sshot.size[1]})"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


REGISTRY.register(Tool(
    name="system_screenshot_to_file",
    description=(
        "화면을 PNG 파일로 저장 (cross-platform via mss). "
        "path 미지정 시 ~/.jarvis/screenshots/timestamp.png. display=0은 전체, 1+는 특정 모니터."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "저장 경로 (옵션)"},
            "display": {"type": "integer", "description": "0=전체, 1+=특정 모니터"},
        },
        "required": [],
    },
    handler=_system_screenshot_to_file,
))


# ──────────────── system_record_audio (cross-platform via sounddevice) ────────────────
def _system_record_audio(seconds: int = 5, path: str = "", samplerate: int = 16000) -> str:
    """마이크로 N초 녹음 → WAV 파일. sounddevice + soundfile 또는 wave 모듈."""
    if seconds < 1 or seconds > 600:
        return "ERROR: seconds는 1~600 범위"
    try:
        import wave

        import numpy as np  # type: ignore
        import sounddevice as sd  # type: ignore
    except ImportError as e:
        return f"ERROR: {e}"

    if not path:
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_dir = Path.home() / ".jarvis" / "recordings"
        out_dir.mkdir(parents=True, exist_ok=True)
        target_path = out_dir / f"jarvis-{ts}.wav"
    else:
        target_path = Path(path).expanduser()
        target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        recording = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1, dtype="int16")
        sd.wait()
        with wave.open(str(target_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(samplerate)
            wf.writeframes(recording.tobytes())
        return f"OK: {target_path} ({seconds}s @ {samplerate}Hz)"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


REGISTRY.register(Tool(
    name="system_record_audio",
    description=(
        "마이크로 N초 녹음 → WAV 파일 (cross-platform via sounddevice). "
        "path 미지정 시 ~/.jarvis/recordings/timestamp.wav."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "seconds": {"type": "integer", "description": "녹음 시간 (1~600), 기본 5"},
            "path": {"type": "string", "description": "저장 경로 (옵션)"},
            "samplerate": {"type": "integer", "description": "샘플레이트, 기본 16000"},
        },
        "required": [],
    },
    handler=_system_record_audio,
))


# ──────────────── system_env_summary (cross-platform diagnostic) ────────────────
def _system_env_summary() -> str:
    """OS / Python / 메모리 / 디스크 / 자비스 환경 종합 진단 (한 번 호출로)."""
    import platform as _plat
    import sys as _sys

    out: list[str] = []
    out.append(f"OS:        {_plat.platform()}")
    out.append(f"Python:    {_sys.version.split()[0]} ({_plat.python_implementation()})")
    out.append(f"Arch:      {_plat.machine()}")

    # CPU/메모리 — psutil이 없으면 plat fallback
    try:
        import psutil  # type: ignore
        vm = psutil.virtual_memory()
        out.append(f"CPU:       {psutil.cpu_count(logical=True)} logical / {psutil.cpu_count(logical=False)} physical")
        out.append(f"Memory:    {vm.used // 1024**2}MB used / {vm.total // 1024**2}MB total ({vm.percent}%)")
        d = psutil.disk_usage("/")
        out.append(f"Disk(/):   {d.used // 1024**3}GB used / {d.total // 1024**3}GB total ({d.percent}%)")
    except ImportError:
        out.append("CPU/Memory/Disk: psutil 미설치 (pip install psutil 권장)")

    # Jarvis 환경
    out.append("")
    out.append(f"PLATFORM:  IS_MACOS={IS_MACOS}, IS_WINDOWS={IS_WINDOWS}, IS_LINUX={IS_LINUX}")
    jarvis_dir = Path.home() / ".jarvis"
    if jarvis_dir.exists():
        files = list(jarvis_dir.glob("*"))
        out.append(f"~/.jarvis: {len(files)} files/dirs")
        for f in files[:8]:
            sz = f.stat().st_size if f.is_file() else "-"
            out.append(f"  {f.name:<25} {sz}B")
    else:
        out.append("~/.jarvis: 미생성 (jarvis init 권장)")

    # API key / model 환경변수 (값은 마스킹)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    out.append("")
    out.append(f"ANTHROPIC_API_KEY: {'set (' + api_key[:8] + '...)' if api_key else 'MISSING'}")
    out.append(f"JARVIS_VOICE:      {os.environ.get('JARVIS_VOICE', '(default)')}")
    out.append(f"JARVIS_PERSONA:    {os.environ.get('JARVIS_PERSONA', '(default)')}")
    return "\n".join(out)


REGISTRY.register(Tool(
    name="system_env_summary",
    description=(
        "환경 진단 종합 (cross-platform): OS / Python / CPU / Memory / Disk / ~/.jarvis / API key 상태. "
        "jarvis doctor의 도구 버전."
    ),
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_system_env_summary,
))


# ──────────────── system_default_browser_url ────────────────
def _system_default_browser_url(url: str) -> str:
    """기본 브라우저로 URL 열기 (cross-platform). open_url과 동일하지만
    파일 경로가 아닌 URL 전용 — file://, http(s)://, mailto:, magnet: 등 모두."""
    if not url.strip():
        return "ERROR: empty url"
    try:
        webbrowser.open(url)
        return f"OK: opened {url[:80]}"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


REGISTRY.register(Tool(
    name="system_default_browser_url",
    description="기본 브라우저로 URL 열기 (cross-platform via webbrowser). http/https/mailto/file 모두.",
    input_schema={
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
    handler=_system_default_browser_url,
))


# ──────────────── system_open_terminal_at ────────────────
def _system_open_terminal_at(path: str) -> str:
    """지정 폴더에서 새 터미널/콘솔 창 열기 (cross-platform).

    macOS: Terminal.app / iTerm
    Windows: cmd.exe (또는 wt.exe Windows Terminal)
    Linux: gnome-terminal / xterm
    """
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    if not p.is_dir():
        p = p.parent
    target = str(p)
    try:
        if IS_MACOS:
            # Terminal.app은 osascript로 열기 (mac_only가 아닌 cross-platform 선언이라 직접 분기)
            subprocess.run(
                ["osascript", "-e", f'tell application "Terminal" to do script "cd {target}" activate'],
                capture_output=True, timeout=5,
            )
            return f"OK: opened Terminal.app at {target}"
        if IS_WINDOWS:
            # Windows Terminal 우선, 없으면 cmd.exe
            try:
                subprocess.Popen(["wt.exe", "-d", target])
                return f"OK: opened Windows Terminal at {target}"
            except FileNotFoundError:
                subprocess.Popen(["cmd.exe", "/K", f"cd /d {target}"])
                return f"OK: opened cmd.exe at {target}"
        if IS_LINUX:
            # gnome-terminal 우선, 없으면 xterm
            try:
                subprocess.Popen(["gnome-terminal", "--working-directory", target])
                return f"OK: opened gnome-terminal at {target}"
            except FileNotFoundError:
                subprocess.Popen(["xterm", "-e", f"cd {target}; bash"])
                return f"OK: opened xterm at {target}"
        return "ERROR: unsupported OS"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


REGISTRY.register(Tool(
    name="system_open_terminal_at",
    description=(
        "지정 폴더에서 새 터미널/콘솔 창 열기 (cross-platform). "
        "macOS=Terminal.app, Windows=wt.exe/cmd.exe, Linux=gnome-terminal/xterm."
    ),
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "터미널을 열 디렉토리"}},
        "required": ["path"],
    },
    handler=_system_open_terminal_at,
))


# 모듈 import 시 무용 — silence linter
_ = shlex
