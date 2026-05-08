"""핵심 OS 통합 — Cross-platform.

`notify` / `say` / `open_url`은 macOS 우선이지만 Windows 동등 구현 포함.
모든 도구는 실패 시 "ERROR: ..." string 반환 (raise 안 함, agent loop 안전).
"""
from __future__ import annotations

import os as _os
import subprocess
import webbrowser

from jarvis.platform import IS_MACOS, IS_WINDOWS
from jarvis.tools.registry import REGISTRY, Tool


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


# ──────────────── notify ────────────────
def _notify_macos(title: str, message: str, subtitle: str = "") -> str:
    script = f'display notification "{_escape(message)}" with title "{_escape(title)}"'
    if subtitle:
        script += f' subtitle "{_escape(subtitle)}"'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, timeout=5, check=True,
        )
        return "OK"
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode(errors="replace") if e.stderr else str(e)
        return f"ERROR: {err.strip()}"


def _notify_windows(title: str, message: str, subtitle: str = "") -> str:
    """Windows 토스트 알림. win10toast 우선, 실패 시 PowerShell BurntToast 시도."""
    body = f"{subtitle}\n{message}" if subtitle else message
    # 1차: win10toast (가장 가벼움, balloon 알림)
    try:
        from win10toast import ToastNotifier  # type: ignore
        ToastNotifier().show_toast(title, body, duration=5, threaded=True)
        return "OK"
    except Exception:
        pass
    # 2차: PowerShell native toast (Windows 10+)
    try:
        ps = (
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
            "ContentType = WindowsRuntime] | Out-Null;"
            "$tpl = [Windows.UI.Notifications.ToastTemplateType]::ToastText02;"
            "$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($tpl);"
            f"$xml.GetElementsByTagName('text')[0].AppendChild($xml.CreateTextNode('{_escape(title)}')) | Out-Null;"
            f"$xml.GetElementsByTagName('text')[1].AppendChild($xml.CreateTextNode('{_escape(body)}')) | Out-Null;"
            "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml);"
            "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Jarvis').Show($toast);"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, timeout=8, check=False,
        )
        return "OK"
    except Exception as e:
        return f"ERROR: {e}"


def _notify(title: str, message: str, subtitle: str = "") -> str:
    if IS_MACOS:
        return _notify_macos(title, message, subtitle)
    if IS_WINDOWS:
        return _notify_windows(title, message, subtitle)
    # Linux: 기본 notify-send 시도, 실패 시 경고
    try:
        subprocess.run(
            ["notify-send", title, message],
            capture_output=True, timeout=5, check=True,
        )
        return "OK"
    except Exception as e:
        return f"ERROR: notify not supported on this OS ({e})"


# ──────────────── say (TTS) ────────────────
def _say_macos(text: str, voice: str = "", rate: int = 180) -> str:
    """macOS `say` 명령. JARVIS_LANG 기반 voice 자동 선택, JARVIS_VOICE env로 override."""
    if not voice:
        voice = _os.environ.get("JARVIS_VOICE", "")
    if not voice:
        # 언어별 권장 voice
        try:
            from jarvis import i18n
            voice = i18n.tts_voice(platform="macos")
        except Exception:
            voice = "Yuna"
    try:
        subprocess.run(
            ["say", "-v", voice, "-r", str(rate), text],
            timeout=180, check=True,
        )
        return "OK"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e}"


def _say_pyttsx3(text: str, voice: str = "", rate: int = 180) -> str:
    """Cross-platform fallback. Windows SAPI / Linux espeak."""
    try:
        import pyttsx3  # type: ignore
        engine = pyttsx3.init()
        engine.setProperty("rate", rate)
        # 한국어 voice 자동 선택 (Windows에서 Microsoft Heami가 한국어 default)
        if voice:
            voices = engine.getProperty("voices")
            for v in voices:
                if voice.lower() in (v.id or "").lower() or voice.lower() in (v.name or "").lower():
                    engine.setProperty("voice", v.id)
                    break
        else:
            # 한국어 voice 자동 탐색
            voices = engine.getProperty("voices")
            for v in voices:
                ident = (v.id or "") + " " + (v.name or "")
                if "ko" in ident.lower() or "korea" in ident.lower() or "heami" in ident.lower():
                    engine.setProperty("voice", v.id)
                    break
        engine.say(text)
        engine.runAndWait()
        return "OK"
    except Exception as e:
        return f"ERROR: pyttsx3 failed: {e}"


def _say(text: str, voice: str = "", rate: int = 180) -> str:
    """크로스플랫폼 TTS.

    macOS: `say` 네이티브 (한국어 Yuna 자동)
    Windows/Linux: pyttsx3 (Windows SAPI / espeak)
    """
    if IS_MACOS:
        return _say_macos(text, voice, rate)
    return _say_pyttsx3(text, voice, rate)


# ──────────────── open_url ────────────────
def _open_url(url: str) -> str:
    """URL 또는 경로 열기. webbrowser는 양쪽 OS에서 작동."""
    if IS_MACOS:
        try:
            subprocess.run(["open", url], timeout=5, check=True)
            return f"OK: opened {url}"
        except subprocess.CalledProcessError as e:
            return f"ERROR: {e}"
    if IS_WINDOWS:
        # 파일 경로면 explorer, URL이면 브라우저
        if url.startswith(("http://", "https://", "file://")):
            try:
                webbrowser.open(url)
                return f"OK: opened {url}"
            except Exception as e:
                return f"ERROR: {e}"
        # 파일 경로는 start
        try:
            _os.startfile(url)  # type: ignore[attr-defined]
            return f"OK: opened {url}"
        except Exception as e:
            return f"ERROR: {e}"
    # Linux fallback
    try:
        subprocess.run(["xdg-open", url], timeout=5, check=True)
        return f"OK: opened {url}"
    except Exception:
        try:
            webbrowser.open(url)
            return f"OK: opened {url}"
        except Exception as e:
            return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="notify",
    description="시스템 알림 표시 (macOS 알림 센터 / Windows 토스트 / Linux notify-send).",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "message": {"type": "string"},
            "subtitle": {"type": "string"},
        },
        "required": ["title", "message"],
    },
    handler=_notify,
))

REGISTRY.register(Tool(
    name="say",
    description=(
        "TTS로 텍스트 음성 출력. macOS는 native say(Yuna/Reed 등 한국어), "
        "Windows는 pyttsx3+SAPI (Heami 등 한국어 자동)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "voice": {"type": "string", "description": "voice 이름 (옵션)"},
            "rate": {"type": "integer", "description": "WPM, 기본 180"},
        },
        "required": ["text"],
    },
    handler=_say,
))

REGISTRY.register(Tool(
    name="open_url",
    description="기본 브라우저/앱으로 URL 또는 파일 경로 열기. macOS/Windows/Linux 모두.",
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL 또는 경로"},
        },
        "required": ["url"],
    },
    handler=_open_url,
))
