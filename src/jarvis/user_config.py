"""사용자 설정 파일 — ~/.jarvis/config.toml.

자비스 시작 시 자동 로드. 환경변수보다 우선순위 낮음 (env가 override).

예시:
    # ~/.jarvis/config.toml
    voice = "Yuna"
    persona = "casual"
    hud_sounds = false
    health_port = 41420

    [hud]
    silence_threshold = 0.012
    main_model = "small"
    detect_model = "base"
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path.home() / ".jarvis" / "config.toml"


def load() -> dict:
    """config 로드. 없거나 실패 시 빈 dict."""
    if not _CONFIG_PATH.exists():
        return {}
    try:
        if sys.version_info >= (3, 11):
            import tomllib

            with _CONFIG_PATH.open("rb") as f:
                return tomllib.load(f)
        else:
            try:
                import tomli  # type: ignore[import-not-found]

                with _CONFIG_PATH.open("rb") as f:
                    return tomli.load(f)
            except ImportError:
                # fallback: 매우 simple key=value 파싱
                data: dict[str, Any] = {}
                for line in _CONFIG_PATH.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("["):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        v = v.strip().strip('"').strip("'")
                        if v.lower() in ("true", "false"):
                            v = v.lower() == "true"
                        elif v.isdigit():
                            v = int(v)
                        data[k.strip()] = v
                return data
    except Exception as e:
        print(f"[config] load failed: {e}", file=sys.stderr)
        return {}


def apply_to_env() -> None:
    """config 값들을 JARVIS_* env vars로 export (env가 우선)."""
    cfg = load()
    mapping = {
        "voice": "JARVIS_VOICE",
        "persona": "JARVIS_PERSONA",
        "language": "JARVIS_LANG",        # i18n v0.6.0: ko/en/ja/zh/es/fr/de/pt
        "hud_sounds": "JARVIS_HUD_SOUNDS",
        "health_port": "JARVIS_HEALTH_PORT",
        "wake_debug": "JARVIS_WAKE_DEBUG",
        "history_path": "JARVIS_HISTORY_PATH",
    }
    for cfg_key, env_key in mapping.items():
        if cfg_key in cfg and not os.environ.get(env_key):
            v = cfg[cfg_key]
            if isinstance(v, bool):
                v = "1" if v else "0"
            os.environ[env_key] = str(v)


def path() -> Path:
    return _CONFIG_PATH


def set_value(key: str, value: Any) -> None:
    """config.toml에 key=value 저장. 기존 키는 update, 없으면 append.

    간단한 line-based 구현 — 기존 [section] 헤더는 보존, root-level 키만 update/append.
    """
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bool):
        line_value = "true" if value else "false"
    elif isinstance(value, (int, float)):
        line_value = str(value)
    else:
        # string은 quote
        line_value = '"' + str(value).replace('"', '\\"') + '"'
    new_line = f"{key} = {line_value}"

    # 기존 파일 읽기
    if _CONFIG_PATH.exists():
        lines = _CONFIG_PATH.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    # root-level (section 헤더 이전)에서 같은 키 찾기
    found = False
    out_lines: list[str] = []
    in_root = True
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_root = False
        if in_root and stripped and not stripped.startswith("#") and "=" in stripped:
            existing_key = stripped.split("=", 1)[0].strip()
            if existing_key == key:
                out_lines.append(new_line)
                found = True
                continue
        out_lines.append(ln)

    if not found:
        # 첫 [section] 앞에 삽입, 없으면 끝에 append
        insert_idx = len(out_lines)
        for i, ln in enumerate(out_lines):
            if ln.strip().startswith("["):
                insert_idx = i
                break
        out_lines.insert(insert_idx, new_line)

    _CONFIG_PATH.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
