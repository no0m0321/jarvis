"""도구 통합. import 시 모든 모듈이 REGISTRY에 자동 등록.

플랫폼 분기:
- 항상 import: cross-platform 도구 모듈
- macOS only import: AppleScript/osascript 의존 모듈 (Windows에서는 등록 안 됨)
- 결과: Windows에서 약 197개, macOS에서 약 296개 도구 등록 (vision +2 포함)
"""
from jarvis.platform import IS_MACOS

# ── Cross-platform 모듈 (모든 OS) ──────────────────────────
from jarvis.tools import (  # noqa: F401  (sideeffect imports)
    code_exec,
    coding,
    converters,
    data_viz,
    dev,
    dev_extra,
    files,
    files_extra,
    fileops,
    finance,
    fs,
    fun,
    generators,
    health_extra,
    info,
    macos,         # cross-platform: notify/say/open_url
    macos_extra,   # cross-platform: clipboard/screen_capture (calendar는 mac_only)
    memory,
    network,
    network_extra,
    personal,
    shell,
    util_extra,
    utility,
    utils,
    vision,        # cross-platform: vision_screen/camera_describe (mss + opencv)
    web,
)

# ── macOS 전용 모듈 (Windows/Linux에서는 등록 안 됨) ────────
if IS_MACOS:
    from jarvis.tools import (  # noqa: F401
        applescript,
        comm,
        extras,
        macos_browser,
        macos_extras2,
        macos_more,
        macos_system,
        productivity,
        productivity_extra,
        window_mgmt,
    )

from jarvis.tools.registry import REGISTRY, Tool

# Plugin loader — ~/.jarvis/plugins/*.py 자동 import
try:
    from jarvis import plugins as _plugins

    _plugins.load_all()
except Exception:
    pass

__all__ = ["REGISTRY", "Tool"]
