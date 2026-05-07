"""정보 도구 — 날씨/뉴스/주식/암호화폐/위키/arxiv/환율 (외부 API 키 불필요 위주)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from jarvis.tools.registry import REGISTRY, Tool


def _http_json(url: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "jarvis-voice/0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _weather(location: str = "Seoul") -> str:
    """open-meteo (no key) 기반 현재 날씨 + 3일 예보."""
    try:
        # geocoding
        g = _http_json(f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(location)}&count=1")
        if not g.get("results"):
            return f"위치 못 찾음: {location}"
        loc = g["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]
        name = f"{loc['name']}, {loc.get('country', '')}"
        # weather
        w = _http_json(
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            "&timezone=auto&forecast_days=3"
        )
        cur = w.get("current", {})
        daily = w.get("daily", {})
        codes = {
            0: "맑음", 1: "거의 맑음", 2: "부분 흐림", 3: "흐림",
            45: "안개", 48: "착빙성 안개", 51: "약한 이슬비", 53: "이슬비", 55: "강한 이슬비",
            61: "약한 비", 63: "비", 65: "강한 비",
            71: "약한 눈", 73: "눈", 75: "강한 눈", 77: "눈송이",
            80: "약한 소나기", 81: "소나기", 82: "강한 소나기",
            95: "뇌우", 96: "뇌우+우박", 99: "강한 뇌우",
        }
        wc = cur.get("weather_code", -1)
        result = {
            "location": name,
            "current": {
                "temp": cur.get("temperature_2m"),
                "humidity": cur.get("relative_humidity_2m"),
                "wind": cur.get("wind_speed_10m"),
                "condition": codes.get(wc, f"코드 {wc}"),
            },
            "forecast": [
                {
                    "date": daily.get("time", [None] * 3)[i],
                    "high": daily.get("temperature_2m_max", [None] * 3)[i],
                    "low": daily.get("temperature_2m_min", [None] * 3)[i],
                    "rain_prob": daily.get("precipitation_probability_max", [None] * 3)[i],
                    "condition": codes.get(daily.get("weather_code", [-1] * 3)[i], "?"),
                }
                for i in range(min(3, len(daily.get("time", []))))
            ],
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f"날씨 조회 실패: {e}"


def _wikipedia(query: str, lang: str = "ko") -> str:
    """위키피디아 요약."""
    try:
        d = _http_json(
            f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}"
        )
        return json.dumps({
            "title": d.get("title"),
            "extract": d.get("extract", "")[:1500],
            "url": d.get("content_urls", {}).get("desktop", {}).get("page"),
        }, ensure_ascii=False)
    except Exception as e:
        return f"위키 조회 실패 (다른 lang 시도? lang=ko/en/ja): {e}"


def _arxiv_search(query: str, limit: int = 5) -> str:
    """arxiv.org 논문 검색."""
    try:
        url = (
            f"http://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(query)}"
            f"&start=0&max_results={min(limit, 20)}&sortBy=relevance"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "jarvis-voice"})
        with urllib.request.urlopen(req, timeout=10) as r:
            xml = r.read().decode()
        # 간단한 파싱
        import re
        entries = re.findall(r"<entry>(.*?)</entry>", xml, re.S)
        out = []
        for e in entries:
            title = (re.search(r"<title>(.*?)</title>", e, re.S) or [None, ""])[1].strip()
            summary = (re.search(r"<summary>(.*?)</summary>", e, re.S) or [None, ""])[1].strip()[:300]
            link = (re.search(r'<id>(.*?)</id>', e, re.S) or [None, ""])[1].strip()
            authors = re.findall(r"<author><name>(.*?)</name>", e)
            out.append({
                "title": title.replace("\n", " "),
                "authors": authors[:3],
                "summary": summary.replace("\n", " "),
                "url": link,
            })
        return json.dumps(out, ensure_ascii=False)
    except Exception as e:
        return f"arxiv 실패: {e}"


def _hn_top(limit: int = 10) -> str:
    """Hacker News top stories."""
    try:
        ids = _http_json("https://hacker-news.firebaseio.com/v0/topstories.json")[:limit]
        items = []
        for i in ids:
            try:
                it = _http_json(f"https://hacker-news.firebaseio.com/v0/item/{i}.json", timeout=5)
                items.append({
                    "title": it.get("title"),
                    "url": it.get("url") or f"https://news.ycombinator.com/item?id={i}",
                    "score": it.get("score"),
                })
            except Exception:
                continue
        return json.dumps(items, ensure_ascii=False)
    except Exception as e:
        return f"HN 실패: {e}"


def _crypto_price(symbol: str = "BTC") -> str:
    """암호화폐 시세 (Coinbase)."""
    try:
        s = symbol.upper()
        d = _http_json(f"https://api.coinbase.com/v2/exchange-rates?currency={s}")
        rates = d.get("data", {}).get("rates", {})
        return json.dumps({
            "symbol": s,
            "USD": rates.get("USD"),
            "KRW": rates.get("KRW"),
            "EUR": rates.get("EUR"),
            "JPY": rates.get("JPY"),
        }, ensure_ascii=False)
    except Exception as e:
        return f"crypto 실패: {e}"


def _stock_price(ticker: str) -> str:
    """주식 시세 — Yahoo Finance public quote endpoint."""
    try:
        d = _http_json(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}?interval=1d&range=5d"
        )
        result = d.get("chart", {}).get("result", [])
        if not result:
            return f"ticker 없음: {ticker}"
        meta = result[0].get("meta", {})
        return json.dumps({
            "symbol": meta.get("symbol"),
            "currency": meta.get("currency"),
            "price": meta.get("regularMarketPrice"),
            "previous_close": meta.get("chartPreviousClose"),
            "high": meta.get("regularMarketDayHigh"),
            "low": meta.get("regularMarketDayLow"),
            "exchange": meta.get("exchangeName"),
        }, ensure_ascii=False)
    except Exception as e:
        return f"주식 실패: {e}"


def _exchange_rate(base: str = "USD", target: str = "KRW") -> str:
    """환율 — exchangerate.host (no key)."""
    try:
        d = _http_json(
            f"https://api.exchangerate-api.com/v4/latest/{base.upper()}"
        )
        rate = d.get("rates", {}).get(target.upper())
        return json.dumps({
            "base": base.upper(),
            "target": target.upper(),
            "rate": rate,
            "date": d.get("date"),
        }, ensure_ascii=False)
    except Exception as e:
        return f"환율 실패: {e}"


def _rss_feed(url: str, limit: int = 10) -> str:
    """RSS/Atom feed 파싱."""
    import re
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "jarvis-voice/0.2"})
        with urllib.request.urlopen(req, timeout=10) as r:
            xml = r.read().decode("utf-8", errors="replace")
        items = re.findall(r"<item>(.*?)</item>", xml, re.S) or re.findall(r"<entry>(.*?)</entry>", xml, re.S)
        out = []
        for it in items[:limit]:
            title = (re.search(r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S) or [None, ""])[1].strip()
            link = (re.search(r"<link[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", it, re.S) or [None, ""])[1].strip()
            if not link:
                m = re.search(r'<link[^>]*href="([^"]+)"', it)
                if m:
                    link = m.group(1)
            out.append({"title": title, "url": link})
        return json.dumps(out, ensure_ascii=False)
    except Exception as e:
        return f"RSS 실패: {e}"


REGISTRY.register(Tool(
    name="weather",
    description="현재 날씨 + 3일 예보 (open-meteo). 한국어 도시명 OK ('서울','부산' 등).",
    input_schema={
        "type": "object",
        "properties": {"location": {"type": "string", "default": "Seoul"}},
    },
    handler=_weather,
))

REGISTRY.register(Tool(
    name="wikipedia",
    description="위키피디아 요약 검색. lang='ko'(기본)/'en'/'ja' 등.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "lang": {"type": "string", "default": "ko"},
        },
        "required": ["query"],
    },
    handler=_wikipedia,
))

REGISTRY.register(Tool(
    name="arxiv_search",
    description="arxiv.org 논문 검색 — title/authors/summary/url 반환.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
    handler=_arxiv_search,
))

REGISTRY.register(Tool(
    name="hackernews_top",
    description="Hacker News top stories.",
    input_schema={
        "type": "object",
        "properties": {"limit": {"type": "integer", "default": 10}},
    },
    handler=_hn_top,
))

REGISTRY.register(Tool(
    name="crypto_price",
    description="암호화폐 시세 (USD/KRW/EUR/JPY). symbol: BTC/ETH/SOL/XRP/...",
    input_schema={
        "type": "object",
        "properties": {"symbol": {"type": "string", "default": "BTC"}},
    },
    handler=_crypto_price,
))

REGISTRY.register(Tool(
    name="stock_price",
    description="주식 시세 (Yahoo Finance). ticker: AAPL/TSLA/005930.KS 등.",
    input_schema={
        "type": "object",
        "properties": {"ticker": {"type": "string"}},
        "required": ["ticker"],
    },
    handler=_stock_price,
))

REGISTRY.register(Tool(
    name="exchange_rate",
    description="환율 조회. 예: base=USD target=KRW.",
    input_schema={
        "type": "object",
        "properties": {
            "base": {"type": "string", "default": "USD"},
            "target": {"type": "string", "default": "KRW"},
        },
    },
    handler=_exchange_rate,
))

REGISTRY.register(Tool(
    name="rss_feed",
    description="RSS/Atom feed 파싱 — 뉴스 사이트 등.",
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "limit": {"type": "integer", "default": 10},
        },
        "required": ["url"],
    },
    handler=_rss_feed,
))
