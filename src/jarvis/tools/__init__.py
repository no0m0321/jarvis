"""도구 통합. import 시 모든 모듈이 REGISTRY에 자동 등록."""
from jarvis.tools import fs, macos, macos_extra, shell, web  # noqa: F401  (sideeffect)
from jarvis.tools.registry import REGISTRY, Tool

__all__ = ["REGISTRY", "Tool"]
