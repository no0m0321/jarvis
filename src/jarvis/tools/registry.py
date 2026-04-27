from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Tool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., str]

    def to_spec(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class ToolRegistry:
    """Tool 등록 + Anthropic tool spec 생성 + 디스패치."""

    def __init__(self) -> None:
        self._tools: "Dict[str, Tool]" = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def names(self) -> "List[str]":
        return list(self._tools.keys())

    def specs(self) -> "List[Dict[str, Any]]":
        return [t.to_spec() for t in self._tools.values()]

    def dispatch(self, name: str, args: "Dict[str, Any]") -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"[unknown tool: {name}]"
        try:
            result = tool.handler(**(args or {}))
        except TypeError as e:
            return f"ERROR: invalid arguments for {name}: {e}"
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"
        return result if isinstance(result, str) else str(result)


REGISTRY = ToolRegistry()
