"""도구 통합. import 시 모든 모듈이 REGISTRY에 자동 등록."""
from jarvis.tools import (  # noqa: F401  (sideeffect imports)
    applescript,
    dev,
    fileops,
    fs,
    generators,
    macos,
    macos_extra,
    macos_extras2,
    macos_more,
    shell,
    utils,
    web,
)
from jarvis.tools.registry import REGISTRY, Tool

# Plugin loader — ~/.jarvis/plugins/*.py 자동 import
try:
    from jarvis import plugins as _plugins

    _plugins.load_all()
except Exception:
    pass

__all__ = ["REGISTRY", "Tool"]
