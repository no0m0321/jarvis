from __future__ import annotations

import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from jarvis.tools.registry import REGISTRY, Tool

_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _fetch_url(url: str, max_chars: int = 8000) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return f"INVALID_SCHEME: {parsed.scheme}"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 jarvis/0.1"})
        with urlopen(req, timeout=15) as r:  # noqa: S310 (intentional URL fetch)
            charset = r.headers.get_content_charset() or "utf-8"
            raw = r.read(2_000_000).decode(charset, errors="replace")
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"

    cleaned = _SCRIPT_STYLE_RE.sub(" ", raw)
    text = _TAG_RE.sub(" ", cleaned)
    text = _WS_RE.sub(" ", text).strip()
    if len(text) > max_chars:
        return text[:max_chars] + "…[truncated]"
    return text


REGISTRY.register(Tool(
    name="fetch_url",
    description="HTTP(S) URL의 페이지 텍스트를 가져옴. HTML 태그 제거, 기본 최대 8000자.",
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "http(s) URL"},
            "max_chars": {"type": "integer", "description": "최대 반환 문자 수, 기본 8000"},
        },
        "required": ["url"],
    },
    handler=_fetch_url,
))
