"""플랫폼 감지 + 분기 헬퍼.

자비스는 macOS 우선이지만 Windows에서도 코어(LLM/voice/clipboard/screen/cam)는 동작.
macOS 전용 도구(Calendar/Mail/Music/Spotlight 등)는 Windows에서 명확한 ERROR string 반환.

Usage:
    from jarvis.platform import IS_MACOS, IS_WINDOWS, mac_only

    @mac_only
    def my_macos_handler(arg: str) -> str:
        return subprocess.run(["osascript", ...]).stdout

    # 호출 시:
    # macOS:   handler 실행
    # Windows: "ERROR: macOS 전용 — Windows 미지원" string 반환 (raise 안 함)
"""
from __future__ import annotations

import functools
import sys
from typing import Any, Callable, TypeVar

PLATFORM = sys.platform  # 'darwin' | 'win32' | 'linux'
IS_MACOS = sys.platform == "darwin"
IS_WINDOWS = sys.platform in ("win32", "cygwin")
IS_LINUX = sys.platform.startswith("linux")

# 도구 핸들러는 모두 str을 반환하므로 일관된 fallback string
_NOT_SUPPORTED = "ERROR: macOS 전용 도구 — 현재 OS({plat})에서 미지원"
_WIN_NOT_SUPPORTED = "ERROR: Windows 전용 도구 — 현재 OS({plat})에서 미지원"

F = TypeVar("F", bound=Callable[..., str])


def mac_only(handler: F) -> F:
    """macOS 전용 핸들러 데코레이터. 다른 OS에서 ERROR string 반환."""

    @functools.wraps(handler)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        if IS_MACOS:
            return handler(*args, **kwargs)
        return _NOT_SUPPORTED.format(plat=PLATFORM)

    return wrapper  # type: ignore[return-value]


def windows_only(handler: F) -> F:
    """Windows 전용 핸들러 데코레이터."""

    @functools.wraps(handler)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        if IS_WINDOWS:
            return handler(*args, **kwargs)
        return _WIN_NOT_SUPPORTED.format(plat=PLATFORM)

    return wrapper  # type: ignore[return-value]


def cross_platform(*, mac: Callable[..., str], win: Callable[..., str], linux: Callable[..., str] | None = None) -> Callable[..., str]:
    """OS별 핸들러 분기 헬퍼.

    Linux 핸들러 안 주면 mac 핸들러를 fallback으로 사용 (대부분 unix-like 명령은 mac/linux 공통).
    """

    def dispatcher(*args: Any, **kwargs: Any) -> str:
        if IS_MACOS:
            return mac(*args, **kwargs)
        if IS_WINDOWS:
            return win(*args, **kwargs)
        return (linux or mac)(*args, **kwargs)

    return dispatcher


def os_label() -> str:
    """사람이 읽기 좋은 OS 라벨."""
    if IS_MACOS:
        return "macOS"
    if IS_WINDOWS:
        return "Windows"
    if IS_LINUX:
        return "Linux"
    return PLATFORM
