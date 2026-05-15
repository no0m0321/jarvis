"""LLM provider 추상화 — Anthropic / OpenAI / Ollama 통합 인터페이스.

provider 선택은 JARVIS_PROVIDER 환경변수 (기본 'anthropic'):
  - 'anthropic': Anthropic SDK (기본, 모든 도구 use 지원)
  - 'openai':    OpenAI Chat API (도구 use 지원, 메시지 변환)
  - 'ollama':    로컬 Ollama (일반 텍스트만, 도구 use 미지원 — chat/ask 한정)

JARVIS의 상용 배포 기본 경로는 Anthropic Claude이며, 이 모듈은 다음 최적화를 포함한다.
  - auto/balanced/premium/fast/sonnet/opus/haiku 모델 별칭과 입력 길이 기반 라우팅
  - system prompt ephemeral cache 적용
  - SDK 타임아웃 및 재시도 설정
  - 네트워크/일시 오류에 대한 지수 백오프 재시도
  - ~/.jarvis/usage/anthropic-usage.jsonl 사용량·지연 시간 계측
"""
from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path
from typing import Any, Callable, Iterator, Protocol, TypeVar

T = TypeVar("T")


class LLMProvider(Protocol):
    """모든 provider가 구현해야 할 인터페이스."""

    name: str
    supports_tools: bool

    def reply(self, messages: list[dict], system: str, model: str, max_tokens: int) -> str:
        ...

    def stream(self, messages: list[dict], system: str, model: str, max_tokens: int) -> Iterator[str]:
        ...


DEFAULT_ANTHROPIC_MODEL = os.environ.get("JARVIS_DEFAULT_MODEL", "claude-sonnet-4-6")
PREMIUM_ANTHROPIC_MODEL = os.environ.get("JARVIS_PREMIUM_MODEL", "claude-opus-4-7")
FAST_ANTHROPIC_MODEL = os.environ.get("JARVIS_FAST_MODEL", "claude-haiku-4-5-20251001")
ANTHROPIC_MODEL_ALIASES = {
    "auto": "auto",
    "balanced": DEFAULT_ANTHROPIC_MODEL,
    "default": DEFAULT_ANTHROPIC_MODEL,
    "sonnet": DEFAULT_ANTHROPIC_MODEL,
    "sonnet4": DEFAULT_ANTHROPIC_MODEL,
    "sonnet-4": DEFAULT_ANTHROPIC_MODEL,
    "premium": PREMIUM_ANTHROPIC_MODEL,
    "pro": PREMIUM_ANTHROPIC_MODEL,
    "opus": PREMIUM_ANTHROPIC_MODEL,
    "opus4": PREMIUM_ANTHROPIC_MODEL,
    "opus-4": PREMIUM_ANTHROPIC_MODEL,
    "fast": FAST_ANTHROPIC_MODEL,
    "quick": FAST_ANTHROPIC_MODEL,
    "haiku": FAST_ANTHROPIC_MODEL,
    "haiku4": FAST_ANTHROPIC_MODEL,
    "haiku-4": FAST_ANTHROPIC_MODEL,
}


def _estimate_text_size(messages: list[dict], system: str = "") -> int:
    total = len(system or "")
    for message in messages or []:
        content = message.get("content", "")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total += len(str(block.get("text") or block.get("content") or ""))
        else:
            total += len(str(content))
    return total


def _contains_complex_intent(messages: list[dict]) -> bool:
    joined = "\n".join(str(m.get("content", "")) for m in messages or []).lower()
    premium_keywords = (
        "코드", "디버그", "설계", "기획", "분석", "대규모", "최대한", "상용", "배포",
        "refactor", "architecture", "debug", "analyze", "production", "premium", "deploy",
    )
    return any(keyword in joined for keyword in premium_keywords)


def _resolve_anthropic_model(model: str | None, messages: list[dict] | None = None, system: str = "") -> str:
    raw = (model or os.environ.get("JARVIS_MODEL") or "auto").strip()
    normalized = raw.lower()
    mapped = ANTHROPIC_MODEL_ALIASES.get(normalized, raw)
    if mapped != "auto":
        return mapped

    size = _estimate_text_size(messages or [], system)
    if os.environ.get("JARVIS_AUTO_MODEL", "1") == "0":
        return DEFAULT_ANTHROPIC_MODEL
    if size <= int(os.environ.get("JARVIS_FAST_ROUTE_CHARS", "1200")) and not _contains_complex_intent(messages or []):
        return FAST_ANTHROPIC_MODEL
    if size >= int(os.environ.get("JARVIS_PREMIUM_ROUTE_CHARS", "14000")) or _contains_complex_intent(messages or []):
        if os.environ.get("JARVIS_ALLOW_PREMIUM_ROUTING", "1") != "0":
            return PREMIUM_ANTHROPIC_MODEL
    return DEFAULT_ANTHROPIC_MODEL


def _max_tokens(value: int) -> int:
    ceiling = int(os.environ.get("JARVIS_MAX_TOKENS", "8192"))
    return max(64, min(int(value or 2048), ceiling))


def _system_cache_block(system: str) -> str | list[dict[str, Any]]:
    if os.environ.get("JARVIS_DISABLE_PROMPT_CACHE", "0") == "1":
        return system or ""
    return [{"type": "text", "text": system or "", "cache_control": {"type": "ephemeral"}}]


def _normalize_messages(messages: list[dict]) -> list[dict]:
    """Anthropic SDK에 전달하기 전 content 형식을 안전하게 정규화한다."""
    normalized: list[dict] = []
    for message in messages or []:
        role = message.get("role") or "user"
        if role not in {"user", "assistant"}:
            role = "user"
        content = message.get("content", "")
        if isinstance(content, str):
            normalized.append({"role": role, "content": content})
        elif isinstance(content, list):
            safe_blocks = []
            for block in content:
                if not isinstance(block, dict):
                    safe_blocks.append({"type": "text", "text": str(block)})
                    continue
                if block.get("type") == "text":
                    safe_blocks.append({"type": "text", "text": str(block.get("text", ""))})
                else:
                    safe_blocks.append(block)
            normalized.append({"role": role, "content": safe_blocks})
        else:
            normalized.append({"role": role, "content": str(content)})
    return normalized


def _text_from_anthropic_message(message: Any) -> str:
    chunks: list[str] = []
    for block in getattr(message, "content", []) or []:
        if getattr(block, "type", None) == "text":
            chunks.append(getattr(block, "text", ""))
        elif isinstance(block, dict) and block.get("type") == "text":
            chunks.append(str(block.get("text", "")))
    return "".join(chunks)


def _usage_dict(message: Any) -> dict[str, int]:
    usage = getattr(message, "usage", None)
    if not usage:
        return {}
    out: dict[str, int] = {}
    for key in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
        value = getattr(usage, key, None)
        if value is not None:
            out[key] = int(value)
    return out


def _record_anthropic_usage(*, mode: str, model: str, started_at: float, usage: dict[str, int] | None, ok: bool, error: str = "") -> None:
    try:
        usage_dir = Path.home() / ".jarvis" / "usage"
        usage_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": time.time(),
            "mode": mode,
            "model": model,
            "latency_ms": int((time.time() - started_at) * 1000),
            "ok": ok,
            "usage": usage or {},
            "error": error[:240],
        }
        with (usage_dir / "anthropic-usage.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _retry(operation: Callable[[], T], *, label: str) -> T:
    attempts = max(1, int(os.environ.get("JARVIS_ANTHROPIC_RETRIES", "3")))
    last_error: Exception | None = None
    for idx in range(attempts):
        try:
            return operation()
        except Exception as exc:  # noqa: BLE001 - SDK별 예외 타입이 다양함
            last_error = exc
            status = getattr(exc, "status_code", None)
            retryable = status in {408, 409, 425, 429, 500, 502, 503, 504} or status is None
            if idx >= attempts - 1 or not retryable:
                raise
            delay = float(os.environ.get("JARVIS_RETRY_BASE_DELAY", "0.32")) * (2 ** idx) + random.random() * 0.22
            time.sleep(delay)
    raise RuntimeError(f"{label} failed") from last_error


class AnthropicProvider:
    name = "anthropic"
    supports_tools = True

    def __init__(self) -> None:
        from anthropic import Anthropic

        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY 미설정")
        timeout = float(os.environ.get("JARVIS_ANTHROPIC_TIMEOUT", "60"))
        sdk_retries = int(os.environ.get("JARVIS_ANTHROPIC_SDK_RETRIES", "2"))
        beta = os.environ.get("ANTHROPIC_BETA", "prompt-caching-2024-07-31")
        headers = {"anthropic-beta": beta} if beta else None
        try:
            self.client = Anthropic(
                api_key=key,
                timeout=timeout,
                max_retries=sdk_retries,
                default_headers=headers,
            )
        except TypeError:
            self.client = Anthropic(api_key=key)

    def reply(self, messages: list[dict], system: str, model: str, max_tokens: int) -> str:
        normalized = _normalize_messages(messages)
        resolved_model = _resolve_anthropic_model(model, normalized, system)
        started_at = time.time()

        def call():
            return self.client.messages.create(
                model=resolved_model,
                max_tokens=_max_tokens(max_tokens),
                system=_system_cache_block(system),
                messages=normalized,
            )

        try:
            msg = _retry(call, label="anthropic.reply")
            _record_anthropic_usage(mode="reply", model=resolved_model, started_at=started_at, usage=_usage_dict(msg), ok=True)
            return _text_from_anthropic_message(msg)
        except Exception as exc:
            _record_anthropic_usage(mode="reply", model=resolved_model, started_at=started_at, usage=None, ok=False, error=str(exc))
            raise

    def stream(self, messages: list[dict], system: str, model: str, max_tokens: int) -> Iterator[str]:
        normalized = _normalize_messages(messages)
        resolved_model = _resolve_anthropic_model(model, normalized, system)
        started_at = time.time()
        final_message: Any = None

        def open_stream():
            return self.client.messages.stream(
                model=resolved_model,
                max_tokens=_max_tokens(max_tokens),
                system=_system_cache_block(system),
                messages=normalized,
            )

        try:
            with _retry(open_stream, label="anthropic.stream") as s:
                for text in s.text_stream:
                    yield text
                try:
                    final_message = s.get_final_message()
                except Exception:
                    final_message = None
            _record_anthropic_usage(mode="stream", model=resolved_model, started_at=started_at, usage=_usage_dict(final_message), ok=True)
        except Exception as exc:
            _record_anthropic_usage(mode="stream", model=resolved_model, started_at=started_at, usage=None, ok=False, error=str(exc))
            raise


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
