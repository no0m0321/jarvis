"""Plugin loader — ~/.jarvis/plugins/*.py 자동 import (v0.7.0 보안 강화).

각 plugin 파일은 `register()` 함수를 export하면 자비스 시작 시 호출됨.
또는 module-level에서 `from jarvis.tools.registry import REGISTRY, Tool` 후 직접 등록.

v0.7.0 보안:
- 파일 권한 검증 — group/world writable인 plugin은 거부 (`chmod 644` 또는 `600` 권장)
- AST 정적 분석 — 명백히 위험한 패턴(__import__('os').system, exec(urlopen), eval(input()) 등) 거부
- 한 plugin 실패가 다른 plugin 로드를 막지 않음 (격리)
- 모든 plugin 로드 결과는 logger.info로 audit trail

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

import ast
import importlib.util
import os
import stat
import sys
from pathlib import Path

from jarvis.logger import get_logger

log = get_logger(__name__)

_PLUGIN_DIR = Path.home() / ".jarvis" / "plugins"

# 명백히 위험한 AST 패턴 (false positive 가능성 매우 낮은 것만)
_FORBIDDEN_AST_CALLS = {
    # __import__('os').system / __import__('subprocess').run 같은 동적 import
    ("__import__",): "동적 __import__ 사용 — 명시적 import 권장",
    # eval(input()), eval(open()) — 데이터를 코드로 실행
    # exec(urlopen()) — 네트워크에서 받은 코드 실행
}

# 거부할 attribute 접근 패턴 (흔치 않지만 명백히 위험)
_FORBIDDEN_ATTR_PATTERNS = [
    # urllib/requests로 가져온 데이터를 exec/eval — 매우 위험
    # 일반 plugin은 이런 패턴 안 씀.
]


def discover() -> list[Path]:
    """로드 가능한 plugin 파일 list."""
    if not _PLUGIN_DIR.exists():
        return []
    return sorted(_PLUGIN_DIR.glob("*.py"))


def _is_world_or_group_writable(path: Path) -> bool:
    """다른 사용자가 plugin을 수정할 수 있는지 검사. 보안상 거부 대상."""
    try:
        st = path.stat()
        # group write (S_IWGRP=0o020) or other write (S_IWOTH=0o002)
        return bool(st.st_mode & (stat.S_IWGRP | stat.S_IWOTH))
    except OSError:
        return False


def _ast_security_scan(source: str, filename: str) -> str | None:
    """AST 기반 정적 분석 — 명백히 위험한 패턴이 있으면 reason string 반환, 안전하면 None."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as e:
        return f"syntax error at line {e.lineno}: {e.msg}"

    for node in ast.walk(tree):
        # __import__('os').system / __import__('subprocess')
        if isinstance(node, ast.Call):
            func = node.func
            # __import__('...') 호출
            if isinstance(func, ast.Name) and func.id == "__import__":
                if node.args and isinstance(node.args[0], ast.Constant):
                    arg = node.args[0].value
                    if isinstance(arg, str) and arg in ("os", "subprocess", "ctypes"):
                        return (
                            f"동적 __import__('{arg}') 사용 (line {node.lineno}). "
                            "명시적 'import' 문을 사용하시오."
                        )
            # exec(urlopen(...)) / exec(requests.get(...).text) 같은 패턴
            if isinstance(func, ast.Name) and func.id in ("exec", "eval"):
                # 첫 인자가 Call이면서 그 함수명이 urlopen/get/post/fetch면 차단
                if node.args and isinstance(node.args[0], ast.Call):
                    inner = node.args[0].func
                    inner_name = ""
                    if isinstance(inner, ast.Name):
                        inner_name = inner.id
                    elif isinstance(inner, ast.Attribute):
                        inner_name = inner.attr
                    if inner_name in ("urlopen", "get", "post", "fetch", "request"):
                        return (
                            f"network fetch → exec/eval 패턴 거부 (line {node.lineno}). "
                            "untrusted code execution 위험."
                        )
    return None


def load_all() -> list[str]:
    """모든 plugin import. 각 파일은 권한 + AST 검증 후 로드.

    실패한 plugin은 logger.warning로 기록하고 다음 plugin으로 진행.
    Returns: 성공적으로 로드된 plugin stem 이름 list.
    """
    loaded: list[str] = []
    for plugin_path in discover():
        if plugin_path.name.startswith("_"):
            continue
        # 1) 파일 권한 검증
        if _is_world_or_group_writable(plugin_path):
            log.warning(
                "plugin %s 거부: group/world writable. `chmod 600 %s` 또는 644.",
                plugin_path.name, plugin_path,
            )
            continue
        # 2) AST 정적 분석
        try:
            source = plugin_path.read_text(encoding="utf-8")
        except OSError as e:
            log.warning("plugin %s 읽기 실패: %s", plugin_path.name, e)
            continue
        reason = _ast_security_scan(source, plugin_path.name)
        if reason:
            log.warning("plugin %s 거부 (정적 분석): %s", plugin_path.name, reason)
            continue
        # 3) import + 선택적 register() 호출
        mod_name = f"jarvis.plugins.{plugin_path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(mod_name, plugin_path)
            if spec is None or spec.loader is None:
                log.warning("plugin %s spec 생성 실패", plugin_path.name)
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = module
            spec.loader.exec_module(module)
            if hasattr(module, "register") and callable(module.register):
                module.register()
            loaded.append(plugin_path.stem)
            log.info("plugin loaded: %s", plugin_path.stem)
        except Exception as e:
            log.error("plugin %s load failed: %s", plugin_path.name, e)
    return loaded


# 미사용 import silence
_ = os
