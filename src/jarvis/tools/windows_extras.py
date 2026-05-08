"""Windows 등가물 도구 — macOS 전용 도구의 Windows 버전.

PowerShell + Win32 API + Registry 기반. 모두 `@windows_only` 데코레이터로 graceful 분기.
macOS/Linux에서 호출 시 한국어 ERROR string 반환.

대응 macOS 도구:
- dark_mode_*       → windows_dark_mode_*
- top_processes     → windows_top_processes
- frontmost_app     → windows_frontmost_app
- running_apps      → windows_running_apps
- audio_device_*    → windows_audio_device_list
- mic_mute          → windows_mic_mute
- battery_info      → windows_battery_info
- wifi_info         → windows_wifi_info
- bluetooth_status  → windows_bluetooth_status
- caffeinate_*      → windows_caffeinate_*
- listening_ports   → windows_listening_ports
- defaults_read     → windows_registry_read
"""
from __future__ import annotations

import os
import subprocess
from typing import List

from jarvis.platform import windows_only
from jarvis.tools.registry import REGISTRY, Tool

_PS_BASE = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command"]


def _ps(script: str, timeout: int = 15) -> str:
    """PowerShell 명령 실행 헬퍼 (Windows-only assumed)."""
    try:
        result = subprocess.run(
            [*_PS_BASE, script],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            return f"ERROR: {(result.stderr or result.stdout).strip()[:300]}"
        return result.stdout.strip() or "(empty)"
    except subprocess.TimeoutExpired:
        return f"TIMEOUT (>{timeout}s)"
    except FileNotFoundError:
        return "ERROR: powershell.exe 없음 (Windows가 아닌 환경)"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


# ──────────────── Dark mode (registry HKCU) ────────────────
_DM_KEY = r"HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"


@windows_only
def _windows_dark_mode_status() -> str:
    """Windows 다크모드 상태 (registry AppsUseLightTheme)."""
    out = _ps(
        f"(Get-ItemProperty -Path '{_DM_KEY}' -Name AppsUseLightTheme -ErrorAction SilentlyContinue).AppsUseLightTheme"
    )
    if out.startswith("ERROR") or out == "(empty)":
        return out
    # 0 = dark, 1 = light
    if out.strip() == "0":
        return "true"
    if out.strip() == "1":
        return "false"
    return out


@windows_only
def _windows_dark_mode_set(on: bool = True) -> str:
    """다크모드 명시적 on/off. 0=dark, 1=light."""
    val = "0" if on else "1"
    out = _ps(
        f"Set-ItemProperty -Path '{_DM_KEY}' -Name AppsUseLightTheme -Value {val}; "
        f"Set-ItemProperty -Path '{_DM_KEY}' -Name SystemUsesLightTheme -Value {val}; "
        f"echo OK"
    )
    return f"OK: dark={on}" if "OK" in out else out


@windows_only
def _windows_dark_mode_toggle() -> str:
    cur = _windows_dark_mode_status()
    if cur == "true":
        return _windows_dark_mode_set(False)
    return _windows_dark_mode_set(True)


REGISTRY.register(Tool(
    name="windows_dark_mode_status",
    description="Windows 다크모드 상태 (registry AppsUseLightTheme).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_windows_dark_mode_status,
))
REGISTRY.register(Tool(
    name="windows_dark_mode_set",
    description="Windows 다크모드 on/off (registry).",
    input_schema={
        "type": "object",
        "properties": {"on": {"type": "boolean", "description": "true=dark, false=light"}},
        "required": [],
    },
    handler=_windows_dark_mode_set,
))
REGISTRY.register(Tool(
    name="windows_dark_mode_toggle",
    description="Windows 다크모드 토글.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_windows_dark_mode_toggle,
))


# ──────────────── Top processes ────────────────
@windows_only
def _windows_top_processes(n: int = 10) -> str:
    """CPU 사용률 상위 N개 프로세스 (Get-Process)."""
    n = max(1, min(50, int(n)))
    script = (
        f"Get-Process | Sort-Object -Property CPU -Descending | "
        f"Select-Object -First {n} | "
        f"Format-Table -AutoSize Name, Id, @{{Name='CPU(s)';Expression={{[math]::Round($_.CPU,2)}}}}, "
        f"@{{Name='WS(MB)';Expression={{[math]::Round($_.WorkingSet64/1MB,1)}}}} | Out-String"
    )
    return _ps(script)


REGISTRY.register(Tool(
    name="windows_top_processes",
    description="Windows에서 CPU 사용률 상위 N개 프로세스 (top_processes의 Windows 등가물).",
    input_schema={
        "type": "object",
        "properties": {"n": {"type": "integer", "description": "기본 10"}},
        "required": [],
    },
    handler=_windows_top_processes,
))


# ──────────────── Frontmost / running apps ────────────────
@windows_only
def _windows_frontmost_app() -> str:
    """현재 frontmost 창의 앱 이름 (GetForegroundWindow + GetWindowThreadProcessId)."""
    script = """
    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    public class W {
        [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
    }
"@
    $h = [W]::GetForegroundWindow()
    $pid_ = 0
    [W]::GetWindowThreadProcessId($h, [ref]$pid_) | Out-Null
    (Get-Process -Id $pid_).ProcessName
    """
    return _ps(script)


@windows_only
def _windows_running_apps() -> str:
    """현재 visible window가 있는 프로세스 list (frontmost가 아닌 모든 visible)."""
    script = (
        "Get-Process | Where-Object {$_.MainWindowTitle} | "
        "Sort-Object ProcessName | "
        "Select-Object -ExpandProperty ProcessName -Unique"
    )
    return _ps(script)


REGISTRY.register(Tool(
    name="windows_frontmost_app",
    description="Windows에서 현재 frontmost 창의 프로세스 이름 (frontmost_app의 Windows 등가물).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_windows_frontmost_app,
))
REGISTRY.register(Tool(
    name="windows_running_apps",
    description="visible window가 있는 모든 실행 중 프로세스 (running_apps의 Windows 등가물).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_windows_running_apps,
))


# ──────────────── Audio device list (PowerShell native) ────────────────
@windows_only
def _windows_audio_device_list() -> str:
    """오디오 출력 장치 list (Get-CimInstance Win32_SoundDevice)."""
    script = (
        "Get-CimInstance -ClassName Win32_SoundDevice | "
        "Where-Object {$_.Status -eq 'OK'} | "
        "Format-Table -AutoSize Name, Manufacturer, StatusInfo | Out-String"
    )
    return _ps(script)


REGISTRY.register(Tool(
    name="windows_audio_device_list",
    description="Windows 오디오 장치 list (audio_device_list의 Windows 등가물 — readonly).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_windows_audio_device_list,
))


# ──────────────── Mic mute (PowerShell + AudioMute helper) ────────────────
@windows_only
def _windows_mic_mute(state: str = "toggle") -> str:
    """마이크 mute/unmute. PowerShell의 AudioDeviceCmdlets 우선, 미설치 시 안내.

    state: on (mute) / off (unmute) / toggle.
    """
    # AudioDeviceCmdlets 모듈 체크
    check = _ps("Get-Module -ListAvailable -Name AudioDeviceCmdlets | Select-Object -ExpandProperty Version", timeout=5)
    if check.startswith("ERROR") or check == "(empty)":
        return (
            "WARN: AudioDeviceCmdlets 미설치. PowerShell 관리자 모드에서:\n"
            "  Install-Module -Name AudioDeviceCmdlets -Scope CurrentUser -Force\n"
            "(또는 NirCmd: nircmd mutesysvolume 1 default_record)"
        )
    if state == "toggle":
        target = "$cur = (Get-AudioDevice -RecordingMute); Set-AudioDevice -RecordingMute (-not $cur)"
    elif state == "on":
        target = "Set-AudioDevice -RecordingMute $true"
    else:
        target = "Set-AudioDevice -RecordingMute $false"
    out = _ps(f"Import-Module AudioDeviceCmdlets; {target}; echo OK")
    return f"OK: mic {state}" if "OK" in out else out


REGISTRY.register(Tool(
    name="windows_mic_mute",
    description="Windows 마이크 mute/unmute/toggle (AudioDeviceCmdlets 모듈 필요).",
    input_schema={
        "type": "object",
        "properties": {"state": {"type": "string", "description": "on|off|toggle"}},
        "required": [],
    },
    handler=_windows_mic_mute,
))


# ──────────────── Battery info ────────────────
@windows_only
def _windows_battery_info() -> str:
    """배터리 잔량 + 충전 상태 (Get-CimInstance Win32_Battery)."""
    script = """
    $b = Get-CimInstance -ClassName Win32_Battery
    if (-not $b) { 'no battery (desktop?)'; exit }
    $pct = $b.EstimatedChargeRemaining
    $stat = switch ($b.BatteryStatus) {
        1 {'Discharging'} 2 {'AC'} 3 {'Fully Charged'} 4 {'Low'} 5 {'Critical'}
        6 {'Charging'} 7 {'Charging+High'} 8 {'Charging+Low'} 9 {'Charging+Critical'}
        10 {'Undefined'} 11 {'Partially Charged'} default {'Unknown'}
    }
    $rem = if ($b.EstimatedRunTime -lt 71582788) {"$([int]($b.EstimatedRunTime/60))h $($b.EstimatedRunTime%60)m"} else {'AC'}
    "battery: $pct% ($stat, $rem)"
    """
    return _ps(script)


REGISTRY.register(Tool(
    name="windows_battery_info",
    description="Windows 배터리 잔량 + 충전 상태 + 남은 시간 (battery_info의 Windows 등가물).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_windows_battery_info,
))


# ──────────────── Wifi info ────────────────
@windows_only
def _windows_wifi_info() -> str:
    """현재 Wifi SSID + 시그널 (netsh wlan show interfaces)."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=8, encoding="cp949", errors="replace",
        )
        # 영문 / 한국어 모두 대응
        keys_en = ("SSID", "Signal", "Channel", "State")
        keys_ko = ("SSID", "신호", "채널", "상태")
        out: List[str] = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped or ":" not in stripped:
                continue
            head = stripped.split(":", 1)[0].strip()
            if any(head.startswith(k) for k in keys_en + keys_ko):
                out.append(stripped)
        return "\n".join(out[:10]) or "(no wifi info)"
    except FileNotFoundError:
        return "ERROR: netsh 없음 (Windows가 아닌 환경)"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="windows_wifi_info",
    description="Windows Wifi SSID/시그널/채널 (wifi_info의 Windows 등가물).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_windows_wifi_info,
))


# ──────────────── Bluetooth status ────────────────
@windows_only
def _windows_bluetooth_status() -> str:
    """블루투스 어댑터 상태 (Get-PnpDevice -Class Bluetooth)."""
    script = (
        "Get-PnpDevice -Class Bluetooth -PresentOnly | "
        "Where-Object {$_.FriendlyName -match 'Adapter|Radio'} | "
        "Select-Object FriendlyName, Status | "
        "Format-Table -AutoSize | Out-String"
    )
    out = _ps(script)
    if out.startswith("ERROR") or "(empty)" in out:
        return out
    return out or "no bluetooth adapter"


REGISTRY.register(Tool(
    name="windows_bluetooth_status",
    description="Windows 블루투스 어댑터 상태 (bluetooth_status의 Windows 등가물).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_windows_bluetooth_status,
))


# ──────────────── Caffeinate (sleep prevention via SetThreadExecutionState) ──
_CAFFEINATE_THREAD = {"active": False, "minutes": 0}


@windows_only
def _windows_caffeinate_start(minutes: int = 60) -> str:
    """N분간 sleep 방지 (SetThreadExecutionState ES_CONTINUOUS | ES_SYSTEM_REQUIRED).

    minutes=0이면 무한 (jarvis 프로세스 종료 시 자동 해제).
    Python 프로세스가 살아있는 동안만 유효 — daemon에서 호출되는 게 이상적.
    """
    if _CAFFEINATE_THREAD["active"]:
        return "WARN: 이미 caffeinate 실행 중 (먼저 windows_caffeinate_stop)"
    try:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(flags)
        _CAFFEINATE_THREAD["active"] = True
        _CAFFEINATE_THREAD["minutes"] = minutes

        if minutes > 0:
            # 백그라운드 timer로 자동 해제
            import threading
            def _auto_release():
                import time as _time
                _time.sleep(minutes * 60)
                _windows_caffeinate_stop()
            threading.Thread(target=_auto_release, daemon=True).start()
        return f"OK: sleep prevented{' for ' + str(minutes) + 'm' if minutes else ' (until process exit)'}"
    except Exception as e:
        return f"ERROR: {e}"


@windows_only
def _windows_caffeinate_stop() -> str:
    if not _CAFFEINATE_THREAD["active"]:
        return "(not running)"
    try:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        _CAFFEINATE_THREAD["active"] = False
        return "OK: caffeinate stopped"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="windows_caffeinate_start",
    description="Windows sleep 방지 (caffeinate_start의 Windows 등가물 — SetThreadExecutionState).",
    input_schema={
        "type": "object",
        "properties": {"minutes": {"type": "integer", "description": "기본 60, 0=프로세스 종료까지"}},
        "required": [],
    },
    handler=_windows_caffeinate_start,
))
REGISTRY.register(Tool(
    name="windows_caffeinate_stop",
    description="Windows sleep 방지 해제.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_windows_caffeinate_stop,
))


# ──────────────── Listening ports ────────────────
@windows_only
def _windows_listening_ports() -> str:
    """현재 LISTEN 중인 TCP 포트 (netstat -ano)."""
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True, text=True, timeout=8,
        )
        listen_lines = [
            line.strip() for line in result.stdout.splitlines()
            if "LISTENING" in line
        ]
        return "\n".join(listen_lines[:60]) or "(no LISTEN ports)"
    except FileNotFoundError:
        return "ERROR: netstat 없음 (Windows가 아닌 환경)"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="windows_listening_ports",
    description="Windows LISTEN TCP 포트 (listening_ports의 Windows 등가물 — netstat).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_windows_listening_ports,
))


# ──────────────── Registry read (defaults_read 등가물) ────────────────
@windows_only
def _windows_registry_read(path: str, name: str = "") -> str:
    """Windows registry 값 조회 (defaults_read의 Windows 등가물).

    path: 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize'
    name: 키 이름 (없으면 전체 properties)
    """
    if not path.startswith(("HKCU:", "HKLM:", "HKCR:", "HKCU\\", "HKLM\\")):
        return "ERROR: path는 HKCU:/HKLM:/HKCR:로 시작 (예: HKCU:\\Software\\...)"
    if name:
        script = f"(Get-ItemProperty -Path '{path}' -Name '{name}' -ErrorAction SilentlyContinue).'{name}'"
    else:
        script = f"Get-ItemProperty -Path '{path}' -ErrorAction SilentlyContinue | Format-List | Out-String"
    return _ps(script)


REGISTRY.register(Tool(
    name="windows_registry_read",
    description="Windows registry 값 조회 (defaults_read의 Windows 등가물). path 예: HKCU:\\Software\\...",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "registry 경로"},
            "name": {"type": "string", "description": "키 이름 (옵션)"},
        },
        "required": ["path"],
    },
    handler=_windows_registry_read,
))


# 미사용 import silence
_ = os
