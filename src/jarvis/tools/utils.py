"""범용 유틸 도구 — 시간, 사용자, 네트워크, 파일 정보."""
from __future__ import annotations

import os
import platform
import socket
import subprocess
from datetime import datetime
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool


def _now(format: str = "iso") -> str:
    """현재 시각. format: iso|kr|unix|hour."""
    now = datetime.now()
    if format == "iso":
        return now.strftime("%Y-%m-%d %H:%M:%S")
    if format == "kr":
        return now.strftime("%Y년 %m월 %d일 %A %H시 %M분")
    if format == "unix":
        return str(int(now.timestamp()))
    if format == "hour":
        return now.strftime("%H:%M")
    return now.isoformat()


def _whoami() -> str:
    """현재 사용자/호스트/플랫폼 정보."""
    info = {
        "user": os.environ.get("USER", "unknown"),
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cwd": str(Path.cwd()),
    }
    return "\n".join(f"{k}: {v}" for k, v in info.items())


def _network_test(host: str = "8.8.8.8", count: int = 3) -> str:
    """ping으로 네트워크 연결 테스트."""
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", "2000", host],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            # 마지막 두 줄에 통계
            lines = result.stdout.strip().split("\n")
            return "\n".join(lines[-2:]) if len(lines) >= 2 else result.stdout.strip()
        return f"FAILED: {result.stdout[-200:]}"
    except Exception as e:
        return f"ERROR: {e}"


def _file_info(path: str) -> str:
    """파일/디렉토리 메타데이터."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"NOT_FOUND: {path}"
    st = p.stat()
    info = {
        "type": "directory" if p.is_dir() else "file",
        "size": f"{st.st_size:,} bytes",
        "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "created": datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
        "mode": oct(st.st_mode)[-3:],
        "owner_uid": st.st_uid,
    }
    if p.is_file():
        info["extension"] = p.suffix or "(none)"
    return "\n".join(f"{k}: {v}" for k, v in info.items())


def _jarvis_status() -> str:
    """자비스 자체 상태 dump — daemon, hud, tool count, history size."""
    from jarvis.tools import REGISTRY as _R

    status = {}
    # daemon process
    try:
        result = subprocess.run(
            ["pgrep", "-f", "jarvis wake"],
            capture_output=True, text=True, timeout=3,
        )
        status["daemon_pids"] = result.stdout.strip() or "(not running)"
    except Exception:
        status["daemon_pids"] = "(check failed)"
    # hud state
    try:
        import json
        hud_p = Path.home() / "Library" / "Caches" / "jarvis-hud.json"
        if hud_p.exists():
            status["hud_state"] = json.loads(hud_p.read_text()).get("state", "?")
    except Exception:
        status["hud_state"] = "(unavailable)"
    # history size
    hist_p = Path.home() / ".jarvis" / "history.jsonl"
    if hist_p.exists():
        status["history_lines"] = sum(1 for _ in hist_p.open(encoding="utf-8"))
    else:
        status["history_lines"] = 0
    # tools
    status["tools_count"] = len(_R.names())
    return "\n".join(f"{k}: {v}" for k, v in status.items())


def _ip_info() -> str:
    """로컬 + 공인 IP."""
    out = []
    # local
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        out.append(f"local: {s.getsockname()[0]}")
        s.close()
    except Exception:
        out.append("local: (unavailable)")
    # public — ifconfig.me
    try:
        result = subprocess.run(
            ["curl", "-s", "-m", "5", "https://ifconfig.me"],
            capture_output=True, text=True, timeout=8,
        )
        out.append(f"public: {result.stdout.strip() or '(failed)'}")
    except Exception:
        out.append("public: (curl failed)")
    return "\n".join(out)


def _hash_file(path: str, algo: str = "sha256") -> str:
    """파일 해시 (md5|sha1|sha256|sha512)."""
    import hashlib

    p = Path(path).expanduser()
    if not p.exists() or not p.is_file():
        return f"NOT_FILE: {path}"
    try:
        h = hashlib.new(algo)
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return f"{algo}: {h.hexdigest()}"
    except Exception as e:
        return f"ERROR: {e}"


def _env_get(name: str = "") -> str:
    """환경변수 조회. name 비우면 JARVIS_* 전체."""
    if name:
        return f"{name}={os.environ.get(name, '(unset)')}"
    return "\n".join(f"{k}={v}" for k, v in sorted(os.environ.items()) if k.startswith("JARVIS_"))


REGISTRY.register(Tool(
    name="now",
    description="현재 시각. format: iso|kr|unix|hour.",
    input_schema={
        "type": "object",
        "properties": {"format": {"type": "string", "description": "iso|kr|unix|hour, 기본 iso"}},
        "required": [],
    },
    handler=_now,
))

REGISTRY.register(Tool(
    name="whoami",
    description="현재 사용자/호스트/플랫폼 정보.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_whoami,
))

REGISTRY.register(Tool(
    name="network_test",
    description="ping으로 네트워크 연결 테스트 (기본 8.8.8.8).",
    input_schema={
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "기본 8.8.8.8"},
            "count": {"type": "integer", "description": "ping 횟수, 기본 3"},
        },
        "required": [],
    },
    handler=_network_test,
))

REGISTRY.register(Tool(
    name="file_info",
    description="파일/디렉토리 메타데이터 (size/modified/permissions).",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
    handler=_file_info,
))

REGISTRY.register(Tool(
    name="jarvis_status",
    description="자비스 자체 상태 dump (daemon PID, HUD 상태, history 크기, 도구 수).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_jarvis_status,
))

REGISTRY.register(Tool(
    name="ip_info",
    description="로컬 + 공인 IP 주소.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_ip_info,
))

REGISTRY.register(Tool(
    name="hash_file",
    description="파일 해시 계산 (md5|sha1|sha256|sha512).",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "algo": {"type": "string", "description": "기본 sha256"},
        },
        "required": ["path"],
    },
    handler=_hash_file,
))

REGISTRY.register(Tool(
    name="env_get",
    description="환경변수 조회. name 비우면 JARVIS_* 전체 dump.",
    input_schema={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": [],
    },
    handler=_env_get,
))
