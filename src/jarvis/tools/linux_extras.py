"""Linux 등가물 도구 — macOS/Windows 시스템 도구의 Linux 버전.

`linux_only` 데코레이터가 platform.py에 없으므로 모듈 내부에서 직접 분기.
시스템 명령(notify-send, gsettings, amixer, upower, iwgetid, bluetoothctl, ps, ip)은
대부분 GNU/Linux 데스크톱 배포판에 기본 설치되어 있다고 가정.
"""
from __future__ import annotations

import functools
import re
import subprocess
from typing import Any, Callable, TypeVar

from jarvis.platform import IS_LINUX, PLATFORM
from jarvis.tools.registry import REGISTRY, Tool

F = TypeVar("F", bound=Callable[..., str])


def _linux_only(handler: F) -> F:
    """Linux 전용 핸들러 데코레이터. 다른 OS에서 ERROR string 반환."""
    @functools.wraps(handler)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        if IS_LINUX:
            return handler(*args, **kwargs)
        return f"ERROR: Linux 전용 도구 — 현재 OS({PLATFORM})에서 미지원"
    return wrapper  # type: ignore[return-value]


def _run(cmd: list[str], timeout: int = 8) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: 명령 없음"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout (>{timeout}s)"
    except Exception as e:
        return 1, "", f"{type(e).__name__}: {e}"


# ──────────────── notify (notify-send) ────────────────
@_linux_only
def _linux_notify(title: str, message: str) -> str:
    """libnotify의 notify-send로 데스크톱 알림."""
    rc, out, err = _run(["notify-send", title, message])
    if rc == 0:
        return "OK"
    if rc == 127:
        return "ERROR: notify-send 미설치 (sudo apt install libnotify-bin)"
    return f"ERROR: {err or out}"


REGISTRY.register(Tool(
    name="linux_notify",
    description="Linux 데스크톱 알림 (libnotify notify-send).",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "message": {"type": "string"},
        },
        "required": ["title", "message"],
    },
    handler=_linux_notify,
))


# ──────────────── Dark mode (gsettings, GNOME) ────────────────
_GS = ["gsettings"]
_DM_SCHEMA = "org.gnome.desktop.interface"
_DM_KEY = "color-scheme"  # 'default' | 'prefer-dark' | 'prefer-light'


@_linux_only
def _linux_dark_mode_status() -> str:
    rc, out, _ = _run([*_GS, "get", _DM_SCHEMA, _DM_KEY])
    if rc != 0:
        return "ERROR: gsettings 미설치 또는 GNOME 환경 아님"
    val = out.strip().strip("'")
    return "true" if "dark" in val else "false"


@_linux_only
def _linux_dark_mode_set(on: bool = True) -> str:
    val = "prefer-dark" if on else "prefer-light"
    rc, out, err = _run([*_GS, "set", _DM_SCHEMA, _DM_KEY, val])
    if rc == 0:
        return f"OK: dark={on}"
    return f"ERROR: {err or out}"


@_linux_only
def _linux_dark_mode_toggle() -> str:
    cur = _linux_dark_mode_status()
    if cur.startswith("ERROR"):
        return cur
    return _linux_dark_mode_set(cur == "false")


REGISTRY.register(Tool(
    name="linux_dark_mode_status",
    description="GNOME 다크모드 상태 (gsettings color-scheme).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_linux_dark_mode_status,
))
REGISTRY.register(Tool(
    name="linux_dark_mode_set",
    description="GNOME 다크모드 명시적 on/off.",
    input_schema={
        "type": "object",
        "properties": {"on": {"type": "boolean"}},
        "required": [],
    },
    handler=_linux_dark_mode_set,
))
REGISTRY.register(Tool(
    name="linux_dark_mode_toggle",
    description="GNOME 다크모드 토글.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_linux_dark_mode_toggle,
))


# ──────────────── Top processes (ps aux | sort) ────────────────
@_linux_only
def _linux_top_processes(n: int = 10) -> str:
    """CPU 사용률 상위 N (ps aux --sort=-%cpu)."""
    n = max(1, min(50, int(n)))
    rc, out, err = _run(["ps", "-eo", "pid,pcpu,pmem,comm", "--sort=-pcpu"])
    if rc != 0:
        return f"ERROR: {err or out}"
    lines = out.splitlines()[:n + 1]
    return "\n".join(lines)


REGISTRY.register(Tool(
    name="linux_top_processes",
    description="Linux에서 CPU 상위 N개 프로세스 (ps -eo pid,pcpu,pmem,comm).",
    input_schema={
        "type": "object",
        "properties": {"n": {"type": "integer", "description": "기본 10"}},
        "required": [],
    },
    handler=_linux_top_processes,
))


# ──────────────── Volume (amixer or pactl) ────────────────
@_linux_only
def _linux_volume_set(level: int) -> str:
    """볼륨 % 설정. amixer 우선, 없으면 pactl."""
    level = max(0, min(100, int(level)))
    # amixer
    rc, _, _ = _run(["amixer", "-q", "sset", "Master", f"{level}%"])
    if rc == 0:
        return f"OK: volume = {level}%"
    # pactl
    rc, _, err = _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"])
    if rc == 0:
        return f"OK: volume = {level}% (pactl)"
    return "ERROR: amixer/pactl 둘 다 실패"


@_linux_only
def _linux_volume_get() -> str:
    rc, out, _ = _run(["amixer", "get", "Master"])
    if rc == 0:
        m = re.search(r"\[(\d+)%\]", out)
        if m:
            return f"{m.group(1)}%"
    rc, out, _ = _run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
    if rc == 0:
        m = re.search(r"(\d+)%", out)
        if m:
            return f"{m.group(1)}%"
    return "ERROR: 볼륨 조회 실패"


REGISTRY.register(Tool(
    name="linux_volume_set",
    description="Linux 시스템 볼륨 설정 (amixer Master 우선, pactl fallback).",
    input_schema={
        "type": "object",
        "properties": {"level": {"type": "integer", "description": "0~100"}},
        "required": ["level"],
    },
    handler=_linux_volume_set,
))
REGISTRY.register(Tool(
    name="linux_volume_get",
    description="Linux 현재 볼륨 조회.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_linux_volume_get,
))


# ──────────────── Battery info (upower) ────────────────
@_linux_only
def _linux_battery_info() -> str:
    """배터리 잔량 + 충전 상태 (upower -i $(upower -e | grep BAT))."""
    rc, devices, _ = _run(["upower", "-e"])
    if rc != 0:
        return "ERROR: upower 미설치 (sudo apt install upower)"
    bat_devs = [d for d in devices.splitlines() if "BAT" in d.upper()]
    if not bat_devs:
        return "no battery (desktop?)"
    rc, info, _ = _run(["upower", "-i", bat_devs[0]])
    if rc != 0:
        return f"ERROR: upower -i 실패 — {info}"
    keep = ("state:", "percentage:", "time to empty:", "time to full:", "energy-rate:")
    out = []
    for line in info.splitlines():
        s = line.strip()
        if any(s.startswith(k) for k in keep):
            out.append(s)
    return "\n".join(out) or info[:300]


REGISTRY.register(Tool(
    name="linux_battery_info",
    description="Linux 배터리 잔량 + 충전 상태 (upower).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_linux_battery_info,
))


# ──────────────── Wifi info ────────────────
@_linux_only
def _linux_wifi_info() -> str:
    """현재 Wifi SSID. nmcli 우선, iwgetid fallback."""
    rc, out, _ = _run(["nmcli", "-t", "-f", "active,ssid,signal", "dev", "wifi"])
    if rc == 0:
        active_lines = [l for l in out.splitlines() if l.startswith("yes:")]
        if active_lines:
            parts = active_lines[0].split(":")
            return f"SSID={parts[1]}, signal={parts[2]}%"
    rc, ssid, _ = _run(["iwgetid", "-r"])
    if rc == 0 and ssid:
        return f"SSID={ssid}"
    return "ERROR: wifi 정보 조회 실패 (nmcli/iwgetid 미동작)"


REGISTRY.register(Tool(
    name="linux_wifi_info",
    description="Linux Wifi SSID + 시그널 (nmcli 우선, iwgetid fallback).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_linux_wifi_info,
))


# ──────────────── Bluetooth status (bluetoothctl) ────────────────
@_linux_only
def _linux_bluetooth_status() -> str:
    """블루투스 어댑터 상태 (bluetoothctl show)."""
    rc, out, err = _run(["bluetoothctl", "show"])
    if rc != 0:
        return f"ERROR: {err or 'bluetoothctl 실패'}"
    # 'Powered: yes/no' 추출
    m = re.search(r"Powered:\s+(\w+)", out)
    return f"bluetooth: {'ON' if m and m.group(1) == 'yes' else 'OFF'}"


REGISTRY.register(Tool(
    name="linux_bluetooth_status",
    description="Linux 블루투스 어댑터 powered 상태 (bluetoothctl show).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_linux_bluetooth_status,
))


# ──────────────── Caffeinate (systemd-inhibit / xset) ────────────────
@_linux_only
def _linux_caffeinate_start(minutes: int = 60) -> str:
    """sleep 방지. systemd-inhibit 우선 (백그라운드 sleep 명령).

    minutes=0이면 매우 큰 값 (1년). 종료는 caffeinate_stop으로.
    """
    secs = (minutes if minutes > 0 else 365 * 24 * 60) * 60
    # systemd-inhibit이 있으면 그것 사용, 없으면 xset
    rc, _, _ = _run(["which", "systemd-inhibit"])
    if rc == 0:
        # 백그라운드로 실행 (subprocess.Popen으로 별도 추적)
        try:
            subprocess.Popen(
                ["systemd-inhibit", "--what=idle:sleep", "--mode=block",
                 "--why=jarvis caffeinate", "sleep", str(secs)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return f"OK: sleep prevented for {minutes}m (systemd-inhibit)"
        except Exception as e:
            return f"ERROR: {e}"
    # xset s off + xset -dpms (X11 기본)
    rc1, _, _ = _run(["xset", "s", "off"])
    rc2, _, _ = _run(["xset", "-dpms"])
    if rc1 == 0 and rc2 == 0:
        return "OK: screen saver disabled (xset). 수동 해제: xset s on; xset +dpms"
    return "ERROR: systemd-inhibit / xset 둘 다 실패"


@_linux_only
def _linux_caffeinate_stop() -> str:
    """xset 복구 시도 (systemd-inhibit은 sleep 명령 종료까지 자동 유지)."""
    _run(["xset", "s", "on"])
    _run(["xset", "+dpms"])
    return "OK: xset s on; xset +dpms (systemd-inhibit은 timer 만료까지 유지)"


REGISTRY.register(Tool(
    name="linux_caffeinate_start",
    description="Linux sleep 방지 (systemd-inhibit 우선, xset fallback).",
    input_schema={
        "type": "object",
        "properties": {"minutes": {"type": "integer", "description": "기본 60"}},
        "required": [],
    },
    handler=_linux_caffeinate_start,
))
REGISTRY.register(Tool(
    name="linux_caffeinate_stop",
    description="Linux sleep 방지 해제 (xset 복구).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_linux_caffeinate_stop,
))


# ──────────────── Window list (wmctrl) ────────────────
@_linux_only
def _linux_window_list() -> str:
    """모든 창 list (wmctrl -l). X11 환경에서만."""
    rc, out, err = _run(["wmctrl", "-l"])
    if rc == 0:
        return out or "(no windows)"
    if rc == 127:
        return "ERROR: wmctrl 미설치 (sudo apt install wmctrl). Wayland 환경에서는 동작 안 할 수 있음"
    return f"ERROR: {err}"


REGISTRY.register(Tool(
    name="linux_window_list",
    description="Linux 모든 창 list (wmctrl -l, X11 only).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_linux_window_list,
))
