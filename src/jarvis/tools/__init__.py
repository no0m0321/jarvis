"""도구 통합. import 시 모든 모듈이 REGISTRY에 자동 등록.

플랫폼 분기 (graceful 정책):
- 모든 모듈은 모든 OS에서 import 됨 → 도구 명단(REGISTRY)이 OS와 무관하게 일관
- macOS 전용 핸들러는 `@mac_only` 로 감싸져 Windows/Linux 호출 시 한국어 ERROR string 반환
- cross-platform 핸들러는 그대로 동작
- 신규 cross-platform 모듈 system_xp 포함 → 모든 OS에서 317개 도구 등록
"""
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
    system_xp,     # 신규 cross-platform: open_path/show_in_folder + windows_*
    util_extra,
    utility,
    utils,
    vision,        # cross-platform: vision_screen/camera_describe (mss + opencv)
    web,
)

# ── macOS-heavy 모듈 (모든 OS에서 import — 핸들러는 @mac_only로 graceful 분기) ─
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
