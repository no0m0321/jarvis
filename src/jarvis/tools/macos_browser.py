"""Safari / Chrome 브라우저 제어."""
from __future__ import annotations

import subprocess

from jarvis.tools.registry import REGISTRY, Tool


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _osa(script: str, timeout: int = 8) -> str:
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout, check=True,
        )
        return r.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"ERROR: {(e.stderr or '').strip()}"
    except Exception as e:
        return f"ERROR: {e}"


# ── Safari ───────────────────────────────────────────────────────────────
def _safari_new_tab(url: str) -> str:
    s = f'tell application "Safari" to make new document with properties {{URL:"{_esc(url)}"}}'
    out = _osa(s)
    return out if out.startswith("ERROR") else f"OK: opened {url} in Safari"


def _safari_current_url() -> str:
    s = 'tell application "Safari" to return URL of front document'
    return _osa(s) or "(no front document)"


def _safari_list_tabs() -> str:
    s = '''
tell application "Safari"
    set out to ""
    repeat with w in windows
        repeat with t in tabs of w
            set out to out & (URL of t) & " | " & (name of t) & linefeed
        end repeat
    end repeat
    return out
end tell
'''
    return _osa(s) or "(no tabs)"


def _safari_close_current() -> str:
    return _osa('tell application "Safari" to close current tab of front window') or "OK"


def _safari_reload() -> str:
    return _osa('tell application "Safari" to do JavaScript "location.reload()" in front document') or "OK"


REGISTRY.register(Tool(
    name="safari_new_tab",
    description="Safari에 새 탭으로 URL 열기.",
    input_schema={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    handler=_safari_new_tab,
))
REGISTRY.register(Tool(
    name="safari_current_url",
    description="Safari 현재(front) 탭의 URL 반환.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_safari_current_url,
))
REGISTRY.register(Tool(
    name="safari_list_tabs",
    description="Safari 모든 창의 탭 list — URL | 제목.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_safari_list_tabs,
))
REGISTRY.register(Tool(
    name="safari_close_current",
    description="Safari 현재 탭 닫기.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_safari_close_current,
))
REGISTRY.register(Tool(
    name="safari_reload",
    description="Safari 현재 탭 새로고침 (Develop > Allow JavaScript from Apple Events 필요).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_safari_reload,
))


# ── Chrome ───────────────────────────────────────────────────────────────
def _chrome_new_tab(url: str) -> str:
    s = f'''
tell application "Google Chrome"
    if (count windows) = 0 then make new window
    tell front window to make new tab with properties {{URL:"{_esc(url)}"}}
    activate
end tell
return "OK"
'''
    out = _osa(s)
    return out if out.startswith("ERROR") else f"OK: opened {url} in Chrome"


def _chrome_current_url() -> str:
    return _osa('tell application "Google Chrome" to return URL of active tab of front window') or "(no front window)"


def _chrome_list_tabs() -> str:
    s = '''
tell application "Google Chrome"
    set out to ""
    repeat with w in windows
        repeat with t in tabs of w
            set out to out & (URL of t) & " | " & (title of t) & linefeed
        end repeat
    end repeat
    return out
end tell
'''
    return _osa(s) or "(no tabs)"


REGISTRY.register(Tool(
    name="chrome_new_tab",
    description="Google Chrome에 새 탭으로 URL 열기.",
    input_schema={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    handler=_chrome_new_tab,
))
REGISTRY.register(Tool(
    name="chrome_current_url",
    description="Chrome 현재(active) 탭의 URL 반환.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_chrome_current_url,
))
REGISTRY.register(Tool(
    name="chrome_list_tabs",
    description="Chrome 모든 창의 탭 list — URL | 제목.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_chrome_list_tabs,
))
