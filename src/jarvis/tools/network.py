"""네트워크 진단 — DNS, whois, ssl cert, http head, network connections."""
from __future__ import annotations

import socket
import ssl
import subprocess
from datetime import datetime
from urllib.parse import urlparse

from jarvis.tools.registry import REGISTRY, Tool


def _dns_lookup(host: str, record: str = "A") -> str:
    """DNS 조회 (dig 또는 host 사용)."""
    if subprocess.run(["which", "dig"], capture_output=True).returncode == 0:
        try:
            r = subprocess.run(
                ["dig", "+short", host, record],
                capture_output=True, text=True, timeout=10, check=True,
            )
            return r.stdout.strip() or f"(no {record} record for {host})"
        except Exception as e:
            return f"ERROR: {e}"
    try:
        ip = socket.gethostbyname(host)
        return f"{record}: {ip}"
    except socket.gaierror as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="dns_lookup",
    description="DNS 조회. record: A|AAAA|CNAME|MX|TXT|NS (기본 A).",
    input_schema={
        "type": "object",
        "properties": {
            "host": {"type": "string"},
            "record": {"type": "string", "description": "기본 A"},
        },
        "required": ["host"],
    },
    handler=_dns_lookup,
))


def _ssl_cert_info(host: str, port: int = 443) -> str:
    """SSL 인증서 정보 (만료일, issuer, subject)."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
        if not cert:
            return "ERROR: no cert returned"
        subject = dict(x[0] for x in cert.get("subject", []))
        issuer = dict(x[0] for x in cert.get("issuer", []))
        not_after = cert.get("notAfter", "?")
        expire = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z") if not_after != "?" else None
        days_left = (expire - datetime.now()).days if expire else "?"
        return (
            f"subject CN: {subject.get('commonName', '?')}\n"
            f"issuer: {issuer.get('organizationName', issuer.get('commonName', '?'))}\n"
            f"not_after: {not_after} ({days_left}일 남음)"
        )
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


REGISTRY.register(Tool(
    name="ssl_cert_info",
    description="HTTPS SSL 인증서 정보 조회 (subject CN, issuer, 만료일).",
    input_schema={
        "type": "object",
        "properties": {
            "host": {"type": "string"},
            "port": {"type": "integer", "description": "기본 443"},
        },
        "required": ["host"],
    },
    handler=_ssl_cert_info,
))


def _http_head(url: str) -> str:
    """HTTP HEAD — 응답 코드 + headers."""
    from urllib.request import Request, urlopen

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return f"INVALID: {parsed.scheme}"
    try:
        req = Request(url, method="HEAD", headers={"User-Agent": "jarvis/0.2"})
        with urlopen(req, timeout=10) as r:  # noqa: S310
            out = [f"status: {r.status}", f"reason: {r.reason}"]
            for k, v in r.headers.items():
                out.append(f"{k}: {v}")
        return "\n".join(out[:30])
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


REGISTRY.register(Tool(
    name="http_head",
    description="HTTP HEAD 요청 — 응답 status + headers.",
    input_schema={
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
    handler=_http_head,
))


def _network_connections(filter_proc: str = "") -> str:
    """현재 네트워크 연결 (lsof -i). filter_proc로 프로세스명 매칭."""
    try:
        result = subprocess.run(
            ["lsof", "-i", "-P", "-n"],
            capture_output=True, text=True, timeout=15,
        )
        lines = result.stdout.strip().splitlines()
        if filter_proc:
            f = filter_proc.lower()
            lines = [lines[0]] + [ln for ln in lines[1:] if f in ln.lower()]
        return "\n".join(lines[:40]) + (
            "\n(truncated)" if len(lines) > 40 else ""
        )
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="network_connections",
    description="현재 네트워크 연결 list (lsof -i). filter_proc로 프로세스명 매칭.",
    input_schema={
        "type": "object",
        "properties": {"filter_proc": {"type": "string"}},
        "required": [],
    },
    handler=_network_connections,
))


def _public_ip() -> str:
    """공인 IP (ifconfig.me + ipinfo.io)."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-m", "5", "https://ifconfig.me"],
            capture_output=True, text=True, timeout=8,
        )
        ip = result.stdout.strip()
        if not ip:
            return "ERROR: ifconfig.me failed"
        # geo info from ipinfo
        try:
            r2 = subprocess.run(
                ["curl", "-s", "-m", "5", f"https://ipinfo.io/{ip}/json"],
                capture_output=True, text=True, timeout=8,
            )
            return f"ip: {ip}\n{r2.stdout.strip()}"
        except Exception:
            return f"ip: {ip}"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="public_ip",
    description="공인 IP + geo 정보 (ipinfo.io).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_public_ip,
))


def _whois_lookup(domain: str) -> str:
    """domain whois 정보 (creation/expiration date 위주)."""
    if subprocess.run(["which", "whois"], capture_output=True).returncode != 0:
        return "ERROR: whois CLI 미설치 (`brew install whois`)"
    try:
        result = subprocess.run(
            ["whois", domain],
            capture_output=True, text=True, timeout=15,
        )
        # 핵심 라인만 추출
        lines = result.stdout.splitlines()
        keep_keys = ("Domain Name:", "Registrar:", "Creation Date:", "Registry Expiry Date:",
                     "Updated Date:", "Name Server:", "DNSSEC:", "Status:")
        filtered = [ln.strip() for ln in lines if any(k in ln for k in keep_keys)]
        return "\n".join(filtered[:20]) or result.stdout[:1000]
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="whois_lookup",
    description="도메인 whois 정보 (creation/expiry/registrar). whois CLI 필요.",
    input_schema={
        "type": "object",
        "properties": {"domain": {"type": "string"}},
        "required": ["domain"],
    },
    handler=_whois_lookup,
))
