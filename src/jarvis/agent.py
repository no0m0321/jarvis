from __future__ import annotations

from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from rich.console import Console

from jarvis import history, hud
from jarvis.assistant import SYSTEM_PROMPT
from jarvis.config import settings
from jarvis.tools import REGISTRY


def _block_to_dict(block: Any) -> Dict[str, Any]:
    if hasattr(block, "model_dump"):
        return block.model_dump(exclude_unset=False)
    if isinstance(block, dict):
        return block
    return {"type": "text", "text": str(block)}


def _final_text(content: Any) -> str:
    parts: "List[str]" = []
    for block in content:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", "") or "")
    return "".join(parts)


def run_agent(
    user_input: str,
    max_turns: int = 12,
    max_tokens_per_turn: int = 4096,
    verbose: bool = True,
    console: Optional[Console] = None,
) -> str:
    """Tool use agentic loop.

    Prompt caching: tools 배열 마지막 + system block에 ephemeral 캐시.
    Render 순서가 tools → system → messages이므로 system block 캐시는
    tools+system 전체를 커버하고, tools 자체 캐시는 tier 분리로 안전.
    HUD: 진입 시 'analyzing' 상태 set, 종료 시 'idle' 복귀.
    """
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY가 설정되지 않음. .env에 키를 채우거나 환경변수로 지정하시오."
        )

    client = Anthropic(api_key=settings.anthropic_api_key)
    out = console or Console()

    tool_specs: "List[Dict[str, Any]]" = REGISTRY.specs()
    if tool_specs:
        tool_specs = [{**spec} for spec in tool_specs]
        tool_specs[-1]["cache_control"] = {"type": "ephemeral"}

    # Anthropic server-side web search tool (Claude가 직접 실행)
    tool_specs.append({
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": 3,
    })

    system_blocks = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    messages: "List[Dict[str, Any]]" = [{"role": "user", "content": user_input}]
    history.append("user", user_input)
    hud.set_state("analyzing", "agent loop")

    try:
        for _ in range(max_turns):
            response = client.messages.create(
                model=settings.model,
                max_tokens=max_tokens_per_turn,
                system=system_blocks,
                tools=tool_specs,
                messages=messages,
            )

            messages.append({
                "role": "assistant",
                "content": [_block_to_dict(b) for b in response.content],
            })

            tool_uses = []
            for block in response.content:
                btype = getattr(block, "type", None)
                if btype == "text":
                    text = getattr(block, "text", "") or ""
                    if text and verbose:
                        out.print(text)
                elif btype == "tool_use":
                    tool_uses.append(block)

            if response.stop_reason == "end_turn":
                final = _final_text(response.content)
                history.append("assistant", final, {"stop_reason": "end_turn"})
                return final

            if response.stop_reason == "pause_turn":
                # server-side tool (web_search) 진행 중 — 그대로 다시 보내 resume
                continue

            if response.stop_reason != "tool_use" or not tool_uses:
                final = _final_text(response.content) or f"[stop_reason={response.stop_reason}]"
                history.append("assistant", final, {"stop_reason": response.stop_reason})
                return final

            tool_results = []
            for tool_use in tool_uses:
                name = getattr(tool_use, "name", "")
                tool_input = getattr(tool_use, "input", {}) or {}
                tool_id = getattr(tool_use, "id", "")
                if verbose:
                    out.print(f"[dim cyan]→ {name}({tool_input})[/dim cyan]")
                hud.set_state("analyzing", f"tool: {name}")
                result = REGISTRY.dispatch(name, tool_input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})

        return "[자비스: 최대 턴 수 초과]"
    finally:
        hud.set_state("idle")
