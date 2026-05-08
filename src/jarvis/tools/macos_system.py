"""macOS 시스템 제어 — Bluetooth, dark mode, audio device, time machine, listen ports, etc."""
from __future__ import annotations

import subprocess
from pathlib import Path

from jarvis.platform import mac_only
from jarvis.tools.registry import REGISTRY, Tool


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


# ── Bluetooth ─────────────────────────────────────────────────────────────
@mac_only
def _bluetooth_status() -> str:
    """blueutil 또는 system_profiler 기반."""
    if subprocess.run(["which", "blueutil"], capture_output=True).returncode == 0:
        try:
            r = subprocess.run(["blueutil", "-p"], capture_output=True, text=True, timeout=5, check=True)
            return f"bluetooth: {'ON' if r.stdout.strip() == '1' else 'OFF'}"
        except Exception as e:
            return f"ERROR: {e}"
    try:
        r = subprocess.run(
            ["system_profiler", "SPBluetoothDataType"],
            capture_output=True, text=True, timeout=10,
        )
        for line in r.stdout.splitlines():
            if "State:" in line:
                return f"bluetooth: {line.split(':', 1)[1].strip()}"
        return "bluetooth: unknown (install blueutil for detail)"
    except Exception as e:
        return f"ERROR: {e}"


@mac_only
def _bluetooth_toggle(state: str = "toggle") -> str:
    """state: on|off|toggle. blueutil CLI 필요."""
    if subprocess.run(["which", "blueutil"], capture_output=True).returncode != 0:
        return "WARN: blueutil 미설치. `brew install blueutil` 필요."
    if state == "toggle":
        cur = subprocess.run(["blueutil", "-p"], capture_output=True, text=True).stdout.strip()
        state = "off" if cur == "1" else "on"
    val = "1" if state == "on" else "0"
    try:
        subprocess.run(["blueutil", "-p", val], capture_output=True, timeout=5, check=True)
        return f"OK: bluetooth {state}"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="bluetooth_status",
    description="블루투스 on/off 상태 조회.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_bluetooth_status,
))
REGISTRY.register(Tool(
    name="bluetooth_toggle",
    description="macOS 블루투스 on/off/toggle (blueutil CLI 필요 — `brew install blueutil`).",
    input_schema={
        "type": "object",
        "properties": {
            "state": {
                "type": "string",
                "description": "블루투스 어댑터 상태",
                "enum": ["on", "off", "toggle"],
                "default": "toggle",
            },
        },
        "required": [],
    },
    handler=_bluetooth_toggle,
))


# ── Dark mode ─────────────────────────────────────────────────────────────
@mac_only
def _dark_mode_toggle() -> str:
    s = 'tell application "System Events" to tell appearance preferences to set dark mode to not dark mode'
    return _osa(s) or "OK: toggled"


@mac_only
def _dark_mode_set(on: bool = True) -> str:
    val = "true" if on else "false"
    s = f'tell application "System Events" to tell appearance preferences to set dark mode to {val}'
    return _osa(s) or f"OK: dark={on}"


@mac_only
def _dark_mode_status() -> str:
    s = 'tell application "System Events" to tell appearance preferences to return dark mode'
    return _osa(s) or "?"


REGISTRY.register(Tool(
    name="dark_mode_toggle",
    description="시스템 다크모드 on/off 토글.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_dark_mode_toggle,
))
REGISTRY.register(Tool(
    name="dark_mode_set",
    description="시스템 다크모드를 명시적으로 on/off.",
    input_schema={
        "type": "object",
        "properties": {"on": {"type": "boolean", "description": "true=dark, false=light"}},
        "required": [],
    },
    handler=_dark_mode_set,
))
REGISTRY.register(Tool(
    name="dark_mode_status",
    description="현재 다크모드 상태 (true/false).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_dark_mode_status,
))


# ── Audio output device ───────────────────────────────────────────────────
@mac_only
def _audio_device_list() -> str:
    """SwitchAudioSource (brew install switchaudio-osx) 우선, 없으면 안내."""
    if subprocess.run(["which", "SwitchAudioSource"], capture_output=True).returncode != 0:
        return "WARN: SwitchAudioSource 미설치. `brew install switchaudio-osx` 필요."
    try:
        r = subprocess.run(
            ["SwitchAudioSource", "-a", "-t", "output"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        cur = subprocess.run(
            ["SwitchAudioSource", "-c"], capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        return f"current: {cur}\n---\n{r.stdout.strip()}"
    except Exception as e:
        return f"ERROR: {e}"


@mac_only
def _audio_device_set(name: str) -> str:
    if subprocess.run(["which", "SwitchAudioSource"], capture_output=True).returncode != 0:
        return "WARN: SwitchAudioSource 미설치. `brew install switchaudio-osx` 필요."
    try:
        r = subprocess.run(
            ["SwitchAudioSource", "-s", name],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return r.stdout.strip() or f"OK: {name}"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {(e.stderr or '').strip()}"


REGISTRY.register(Tool(
    name="audio_device_list",
    description="오디오 출력 장치 list + 현재 활성 장치.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_audio_device_list,
))
REGISTRY.register(Tool(
    name="audio_device_set",
    description="오디오 출력 장치 전환 (예: 'AirPods Pro', 'MacBook Pro Speakers').",
    input_schema={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
    handler=_audio_device_set,
))


# ── Mic mute (시스템 입력 볼륨) ──────────────────────────────────────────
@mac_only
def _mic_mute(state: str = "toggle") -> str:
    """state: on|off|toggle. on=mute (input volume 0), off=unmute (75)."""
    cur = _osa("input volume of (get volume settings)")
    try:
        cur_int = int(cur)
    except Exception:
        cur_int = 75
    if state == "toggle":
        target = 0 if cur_int > 0 else 75
    else:
        target = 0 if state == "on" else 75
    out = _osa(f"set volume input volume {target}")
    if out.startswith("ERROR"):
        return out
    return f"OK: mic {'muted' if target == 0 else 'unmuted'} (input volume = {target})"


REGISTRY.register(Tool(
    name="mic_mute",
    description="macOS 마이크 입력 볼륨 mute/unmute (on=mute=0, off=unmute=75, toggle=현재 상태 반전).",
    input_schema={
        "type": "object",
        "properties": {
            "state": {
                "type": "string",
                "description": "마이크 상태",
                "enum": ["on", "off", "toggle"],
                "default": "toggle",
            },
        },
        "required": [],
    },
    handler=_mic_mute,
))


# ── Time Machine ──────────────────────────────────────────────────────────
@mac_only
def _tm_status() -> str:
    try:
        r = subprocess.run(
            ["tmutil", "status"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return r.stdout.strip()[:500] or "(no status)"
    except Exception as e:
        return f"ERROR: {e}"


@mac_only
def _tm_latest_backup() -> str:
    try:
        r = subprocess.run(
            ["tmutil", "latestbackup"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() or r.stderr.strip() or "(no backup)"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="time_machine_status",
    description="Time Machine 현재 상태 (backup 진행/완료/idle).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_tm_status,
))
REGISTRY.register(Tool(
    name="time_machine_latest",
    description="Time Machine 최근 백업 위치 + 시각.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_tm_latest_backup,
))


# ── Listening ports ───────────────────────────────────────────────────────
@mac_only
def _listening_ports() -> str:
    try:
        r = subprocess.run(
            ["lsof", "-iTCP", "-sTCP:LISTEN", "-n", "-P"],
            capture_output=True, text=True, timeout=8,
        )
        lines = r.stdout.splitlines()
        return "\n".join(lines[:60]) or "(no LISTEN ports)"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="listening_ports",
    description="현재 LISTEN 중인 TCP 포트 list (lsof).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_listening_ports,
))


# ── Memory pressure ───────────────────────────────────────────────────────
@mac_only
def _memory_pressure() -> str:
    try:
        r = subprocess.run(
            ["memory_pressure"],
            capture_output=True, text=True, timeout=5,
        )
        out = r.stdout.strip()
        # 마지막 5줄만 (전체는 길음)
        return "\n".join(out.splitlines()[-10:]) or "(no output)"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="memory_pressure",
    description="시스템 메모리 압박 상태 (memory_pressure CLI).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_memory_pressure,
))


# ── Diskutil list ─────────────────────────────────────────────────────────
@mac_only
def _diskutil_list() -> str:
    try:
        r = subprocess.run(
            ["diskutil", "list"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return r.stdout.strip()[:2000]
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="diskutil_list",
    description="모든 디스크/파티션 list (diskutil list).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_diskutil_list,
))


# ── Spotlight metadata (mdls) ─────────────────────────────────────────────
@mac_only
def _mdls_metadata(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    try:
        r = subprocess.run(
            ["mdls", str(p)],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return r.stdout.strip()[:3000]
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="mdls_metadata",
    description="파일의 Spotlight 메타데이터 (mdls).",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
    handler=_mdls_metadata,
))


# ── log show (system log) ─────────────────────────────────────────────────
@mac_only
def _log_show(predicate: str = "", last: str = "5m", max_lines: int = 50) -> str:
    """log show — 최근 N분/시간."""
    cmd = ["log", "show", "--last", last, "--style", "compact"]
    if predicate:
        cmd += ["--predicate", predicate]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        lines = r.stdout.splitlines()[:max_lines]
        return "\n".join(lines) or "(no entries)"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="log_show",
    description="시스템 로그 조회 (log show). predicate (e.g., 'process == \"WindowServer\"'), last (5m/1h).",
    input_schema={
        "type": "object",
        "properties": {
            "predicate": {"type": "string"},
            "last": {"type": "string", "description": "기본 5m"},
            "max_lines": {"type": "integer", "description": "기본 50"},
        },
        "required": [],
    },
    handler=_log_show,
))


# ── defaults read/write ──────────────────────────────────────────────────
@mac_only
def _defaults_read(domain: str, key: str = "") -> str:
    cmd = ["defaults", "read", domain]
    if key:
        cmd.append(key)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return (r.stdout or r.stderr).strip()[:2000]
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="defaults_read",
    description="`defaults read <domain> [key]` — macOS preferences 조회.",
    input_schema={
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "예: com.apple.dock"},
            "key": {"type": "string", "description": "옵션"},
        },
        "required": ["domain"],
    },
    handler=_defaults_read,
))


# ── AirDrop (Finder reveal) ──────────────────────────────────────────────
@mac_only
def _airdrop_send(file_path: str) -> str:
    """파일을 AirDrop sheet로 열기 (사용자 수신자 선택)."""
    p = Path(file_path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    try:
        subprocess.run(["open", "-a", "Finder", str(p)], timeout=5)
        # AirDrop sheet open via AppleScript
        s = f'''
tell application "Finder" to activate
tell application "System Events"
    keystroke "r" using {{shift down, command down}}
end tell
'''
        # Note: actually sharing requires extra UI automation — just reveal + remind user
        return f"OK: revealed {p}. AirDrop은 Finder > 공유 메뉴에서 수동 진행."
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="airdrop_reveal",
    description="파일을 Finder에 표시 (사용자가 AirDrop sheet로 보낼 수 있도록).",
    input_schema={
        "type": "object",
        "properties": {"file_path": {"type": "string"}},
        "required": ["file_path"],
    },
    handler=_airdrop_send,
))


# ── Quick Look ────────────────────────────────────────────────────────────
@mac_only
def _quick_look(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    try:
        subprocess.Popen(
            ["qlmanage", "-p", str(p)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return f"OK: Quick Look opened — {p}"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="quick_look",
    description="파일을 Quick Look 미리보기로 열기 (qlmanage -p).",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
    handler=_quick_look,
))


# ── Finder reveal ────────────────────────────────────────────────────────
@mac_only
def _finder_reveal(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    try:
        subprocess.run(["open", "-R", str(p)], timeout=5, check=True)
        return f"OK: revealed {p} in Finder"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="finder_reveal",
    description="파일/폴더를 Finder에 reveal (Cmd+클릭과 동등).",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
    handler=_finder_reveal,
))


# ── Caffeinate (sleep prevention) ────────────────────────────────────────
_CAFFEINATE_PROC = {"p": None}


@mac_only
def _caffeinate_start(minutes: int = 60) -> str:
    """N분간 sleep 방지. 0 = 무한."""
    if _CAFFEINATE_PROC["p"] and _CAFFEINATE_PROC["p"].poll() is None:
        return "WARN: 이미 caffeinate 실행 중 (먼저 caffeinate_stop)"
    cmd = ["caffeinate", "-d", "-i"]
    if minutes > 0:
        cmd += ["-t", str(minutes * 60)]
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _CAFFEINATE_PROC["p"] = p
        return f"OK: caffeinate started{' for ' + str(minutes) + 'm' if minutes else ' (indefinite)'}"
    except Exception as e:
        return f"ERROR: {e}"


@mac_only
def _caffeinate_stop() -> str:
    p = _CAFFEINATE_PROC["p"]
    if p and p.poll() is None:
        p.terminate()
        return "OK: caffeinate stopped"
    return "(not running)"


REGISTRY.register(Tool(
    name="caffeinate_start",
    description="시스템 sleep 방지 (caffeinate). minutes=0이면 무한.",
    input_schema={
        "type": "object",
        "properties": {"minutes": {"type": "integer", "description": "기본 60, 0=무한"}},
        "required": [],
    },
    handler=_caffeinate_start,
))
REGISTRY.register(Tool(
    name="caffeinate_stop",
    description="caffeinate 중지 (sleep 방지 해제).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_caffeinate_stop,
))
