"""LLM provider 추상화 — Anthropic / OpenAI / Ollama 통합 인터페이스.

provider 선택은 JARVIS_PROVIDER 환경변수 (기본 'anthropic'):
  - 'anthropic': Anthropic SDK (기본, 모든 도구 use 지원)
  - 'openai':    OpenAI Chat API (도구 use 지원, 메시지 변환)
  - 'ollama':    로컬 Ollama (일반 텍스트만, 도구 use 미지원 — chat/ask 한정)

사용 예:
    export JARVIS_PROVIDER=openai
    export OPENAI_API_KEY=sk-...
    export JARVIS_MODEL=gpt-4o-mini
    jarvis ask "안녕"

    export JARVIS_PROVIDER=ollama
    export OLLAMA_HOST=http://localhost:11434
    export JARVIS_MODEL=llama3.2
    jarvis ask "안녕"

도구 use가 필요한 'jarvis do'와 wake daemon은 anthropic 권장.
"""
from __future__ import annotations

import os
from typing import Any, Iterable, Iterator, Optional, Protocol


class LLMProvider(Protocol):
    """모든 provider가 구현해야 할 인터페이스."""

    name: str
    supports_tools: bool

    def reply(self, messages: list[dict], system: str, model: str, max_tokens: int) -> str:
        ...

    def stream(self, messages: list[dict], system: str, model: str, max_tokens: int) -> Iterator[str]:
        ...


class AnthropicProvider:
    name = "anthropic"
    supports_tools = True

    def __init__(self) -> None:
        from anthropic import Anthropic
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY 미설정")
        self.client = Anthropic(api_key=key)

    def reply(self, messages: list[dict], system: str, model: str, max_tokens: int) -> str:
        msg = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
        )
        return "".join(b.text for b in msg.content if b.type == "text")

    def stream(self, messages: list[dict], system: str, model: str, max_tokens: int) -> Iterator[str]:
        with self.client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
        ) as s:
            yield from s.text_stream


class OpenAIProvider:
    name = "openai"
    supports_tools = True  # OpenAI Chat API도 tool use 지원

    def __init__(self) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai 패키지 미설치 — pip install 'jarvis[openai]'")
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("OPENAI_API_KEY 미설정")
        self.client = OpenAI(api_key=key)

    @staticmethod
    def _to_openai_messages(messages: list[dict], system: str) -> list[dict]:
        out: list[dict] = [{"role": "system", "content": system}]
        for m in messages:
            content = m.get("content", "")
            if isinstance(content, list):
                # Anthropic-style content blocks → text 추출만
                content = "".join(b.get("text", "") for b in content if b.get("type") == "text")
            out.append({"role": m["role"], "content": content})
        return out

    def reply(self, messages: list[dict], system: str, model: str, max_tokens: int) -> str:
        r = self.client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=self._to_openai_messages(messages, system),
        )
        return r.choices[0].message.content or ""

    def stream(self, messages: list[dict], system: str, model: str, max_tokens: int) -> Iterator[str]:
        s = self.client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=self._to_openai_messages(messages, system),
            stream=True,
        )
        for chunk in s:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta


class OllamaProvider:
    """로컬 Ollama 서버 사용. tool use 미지원 — 일반 chat만."""
    name = "ollama"
    supports_tools = False

    def __init__(self) -> None:
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        # ping
        try:
            import urllib.request
            urllib.request.urlopen(f"{self.host}/api/tags", timeout=2).read()
        except Exception as e:
            raise RuntimeError(f"Ollama 서버 도달 불가 ({self.host}) — {e}")

    @staticmethod
    def _to_ollama_messages(messages: list[dict], system: str) -> list[dict]:
        out = [{"role": "system", "content": system}]
        for m in messages:
            content = m.get("content", "")
            if isinstance(content, list):
                content = "".join(b.get("text", "") for b in content if b.get("type") == "text")
            out.append({"role": m["role"], "content": content})
        return out

    def reply(self, messages: list[dict], system: str, model: str, max_tokens: int) -> str:
        import json
        import urllib.request
        body = json.dumps({
            "model": model,
            "messages": self._to_ollama_messages(messages, system),
            "stream": False,
            "options": {"num_predict": max_tokens},
        }).encode()
        req = urllib.request.Request(
            f"{self.host}/api/chat", data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
        return data.get("message", {}).get("content", "")

    def stream(self, messages: list[dict], system: str, model: str, max_tokens: int) -> Iterator[str]:
        import json
        import urllib.request
        body = json.dumps({
            "model": model,
            "messages": self._to_ollama_messages(messages, system),
            "stream": True,
            "options": {"num_predict": max_tokens},
        }).encode()
        req = urllib.request.Request(
            f"{self.host}/api/chat", data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            for line in r:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    msg = obj.get("message", {}).get("content", "")
                    if msg:
                        yield msg
                    if obj.get("done"):
                        break
                except json.JSONDecodeError:
                    pass


def get_provider() -> LLMProvider:
    """JARVIS_PROVIDER 환경변수 기반 provider instance 반환."""
    name = (os.environ.get("JARVIS_PROVIDER") or "anthropic").strip().lower()
    if name == "openai":
        return OpenAIProvider()
    if name == "ollama":
        return OllamaProvider()
    return AnthropicProvider()
