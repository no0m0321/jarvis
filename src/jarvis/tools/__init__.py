"""도구 통합. import 시 모든 모듈이 REGISTRY에 자동 등록."""
from jarvis.tools import (  # noqa: F401  (sideeffect imports)
    fs,
    macos,
    macos_extra,
    macos_extras2,
    macos_more,
    shell,
    utils,
    web,
)
from jarvis.tools.registry import REGISTRY, Tool

__all__ = ["REGISTRY", "Tool"]
