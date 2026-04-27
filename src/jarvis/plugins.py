"""Plugin loader — ~/.jarvis/plugins/*.py 자동 import.

각 plugin 파일은 `register()` 함수를 export하면 자비스 시작 시 호출됨.
또는 module-level에서 `from jarvis.tools.registry import REGISTRY, Tool` 후 직접 등록.

plugin 예시:
    # ~/.jarvis/plugins/weather.py
    from jarvis.tools.registry import REGISTRY, Tool

    def _check_weather(city: str = "Seoul") -> str:
        return f"weather check for {city}"  # 실제 구현은 사용자

    REGISTRY.register(Tool(
        name="weather",
        description="...",
        input_schema={...},
        handler=_check_weather,
    ))
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PLUGIN_DIR = Path.home() / ".jarvis" / "plugins"


def discover() -> list[Path]:
    """로드 가능한 plugin 파일 list."""
    if not _PLUGIN_DIR.exists():
        return []
    return sorted(_PLUGIN_DIR.glob("*.py"))


def load_all() -> list[str]:
    """모든 plugin import. 에러는 silently 캐치 — 한 plugin 실패가 전체를 막지 않음."""
    loaded: list[str] = []
    for plugin_path in discover():
        if plugin_path.name.startswith("_"):
            continue
        mod_name = f"jarvis.plugins.{plugin_path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(mod_name, plugin_path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = module
            spec.loader.exec_module(module)
            # optional register() callback
            if hasattr(module, "register") and callable(module.register):
                module.register()
            loaded.append(plugin_path.stem)
        except Exception as e:
            print(f"[plugin] {plugin_path.name} load failed: {e}", file=sys.stderr)
    return loaded
