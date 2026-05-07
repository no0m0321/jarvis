"""네트워크 확장 — arp, traceroute, http_bench, geo, mac_lookup."""
from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from jarvis.tools.registry import REGISTRY, Tool


def _run(cmd: list, timeout: int = 15) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or r.stderr).strip()
    except Exception as e:
        return f"ERROR: {e}"


def _arp_table() -> str:
    out = _run(["arp", "-an"])
    return "\n".join(out.splitlines()[:60]) or "(empty)"


def _traceroute(host: str, max_hops: int = 20) -> str:
    return _run(["traceroute", "-m", str(max_hops), "-w", "2", host], timeout=60)


def _route_default() -> str:
    out = _run(["route", "-n", "get", "default"])
    return out or "(no default route)"


def _http_bench(url: str, requests: int = 10, concurrency: int = 4) -> str:
    """간단 HTTP 벤치 — 응답 시간 통계."""
    requests = max(1, min(requests, 50))
    concurrency = max(1, min(concurrency, 16))

    def _one() -> float:
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "jarvis-bench"})
            with urllib.request.urlopen(req, timeout=10) as r:
                r.read(4096)
            return time.time() - t0
        except Exception:
            return -1

    times = []
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        for t in ex.map(lambda _: _one(), range(requests)):
            times.append(t)
    ok = [t for t in times if t > 0]
    fail = len(times) - len(ok)
    if not ok:
        return f"ERROR: all {requests} requests failed"
    ok.sort()
    p50 = ok[len(ok) // 2]
    p95 = ok[min(len(ok) - 1, int(len(ok) * 0.95))]
    return (f"url: {url}\n"
            f"requests: {requests}, concurrency: {concurrency}, ok: {len(ok)}, fail: {fail}\n"
            f"min:  {min(ok)*1000:.1f}ms\n"
            f"max:  {max(ok)*1000:.1f}ms\n"
            f"avg:  {sum(ok)/len(ok)*1000:.1f}ms\n"
            f"p50:  {p50*1000:.1f}ms\n"
            f"p95:  {p95*1000:.1f}ms")


def _ip_geo(ip: str = "") -> str:
    """ipinfo.io 무료 API (IP geo lookup). ip='' → 공인 IP."""
    url = f"https://ipinfo.io/{ip}/json" if ip else "https://ipinfo.io/json"
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        keys = ("ip", "city", "region", "country", "loc", "org", "postal", "timezone")
        return "\n".join(f"{k}: {data.get(k, '?')}" for k in keys)
    except Exception as e:
        return f"ERROR: {e}"


def _mac_lookup(mac: str) -> str:
    """MAC 주소 → 제조사 (macvendors.com 무료 API)."""
    mac = mac.replace(":", "").replace("-", "").upper()[:6]
    if len(mac) < 6:
        return "ERROR: MAC OUI 6자 이상 필요"
    try:
        with urllib.request.urlopen(f"https://api.macvendors.com/{mac}", timeout=8) as r:
            return r.read().decode().strip() or "(unknown)"
    except Exception as e:
        return f"ERROR: {e}"


def _ping_avg(host: str, count: int = 5) -> str:
    out = _run(["ping", "-c", str(count), "-q", host], timeout=count * 2 + 5)
    m = re.search(r"min/avg/max[^=]*=\s*([\d.]+)/([\d.]+)/([\d.]+)", out)
    if m:
        return f"{host}: min={m.group(1)}ms avg={m.group(2)}ms max={m.group(3)}ms"
    return out[-300:]


def _interfaces() -> str:
    """ifconfig 파싱 — 활성 인터페이스 IP만."""
    try:
        r = subprocess.run(
            ["ifconfig"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        out = []
        cur = None
        for line in r.stdout.splitlines():
            if line and not line.startswith("\t") and ":" in line:
                cur = line.split(":")[0]
            elif cur and "inet " in line:
                ip = line.split("inet ")[1].split(" ")[0]
                if not ip.startswith("127."):
                    out.append(f"{cur}: {ip}")
        return "\n".join(out) or "(no IPv4 interfaces)"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="arp_table",
    description="현재 네트워크의 ARP 테이블 (host → MAC).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_arp_table,
))
REGISTRY.register(Tool(
    name="traceroute",
    description="목표 호스트까지 경로 추적.",
    input_schema={
        "type": "object",
        "properties": {
            "host": {"type": "string"},
            "max_hops": {"type": "integer", "description": "기본 20"},
        },
        "required": ["host"],
    },
    handler=_traceroute,
))
REGISTRY.register(Tool(
    name="route_default",
    description="기본 라우트 정보.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_route_default,
))
REGISTRY.register(Tool(
    name="http_bench",
    description="HTTP 벤치마크 (min/max/avg/p50/p95 응답시간).",
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "requests": {"type": "integer", "description": "기본 10, 최대 50"},
            "concurrency": {"type": "integer", "description": "기본 4, 최대 16"},
        },
        "required": ["url"],
    },
    handler=_http_bench,
))
REGISTRY.register(Tool(
    name="ip_geo",
    description="IP → 도시/국가/ISP/timezone (ipinfo.io). 인자 없으면 내 IP.",
    input_schema={
        "type": "object",
        "properties": {"ip": {"type": "string", "description": "옵션"}},
        "required": [],
    },
    handler=_ip_geo,
))
REGISTRY.register(Tool(
    name="mac_lookup",
    description="MAC OUI → 제조사 (macvendors.com).",
    input_schema={
        "type": "object",
        "properties": {"mac": {"type": "string"}},
        "required": ["mac"],
    },
    handler=_mac_lookup,
))
REGISTRY.register(Tool(
    name="ping_avg",
    description="ping count회 평균 (min/avg/max ms).",
    input_schema={
        "type": "object",
        "properties": {
            "host": {"type": "string"},
            "count": {"type": "integer", "description": "기본 5"},
        },
        "required": ["host"],
    },
    handler=_ping_avg,
))
REGISTRY.register(Tool(
    name="net_interfaces",
    description="활성 네트워크 인터페이스 IPv4 list.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_interfaces,
))
