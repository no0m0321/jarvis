"""Lightweight health-check HTTP server.

GET /healthz → {"status":"ok","uptime":<sec>,"hud":{...}}
GET /metrics → JSON metrics dump
GET /tools   → 등록된 tool 목록
GET /history?n=20 → 마지막 n개 conversation turn
GET /stop    → 서버 종료

Daemon이 별도 thread로 실행. JARVIS_HEALTH_PORT 환경변수로 포트 변경 (기본 41417).
"""
from __future__ import annotations

import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse


_started_at = time.time()
_server: "Optional[ThreadingHTTPServer]" = None


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs) -> None:  # silence
        pass

    def _send_json(self, code: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        from jarvis import history, hud
        from jarvis.tools import REGISTRY

        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/healthz":
            uptime = time.time() - _started_at
            hud_state = {}
            try:
                from pathlib import Path
                p = Path.home() / "Library" / "Caches" / "jarvis-hud.json"
                if p.exists():
                    hud_state = json.loads(p.read_text())
            except Exception:
                pass
            return self._send_json(200, {
                "status": "ok",
                "uptime_sec": round(uptime, 1),
                "hud": hud_state,
                "tools_count": len(REGISTRY.names()),
            })

        if path == "/metrics":
            import subprocess
            try:
                result = subprocess.run(
                    ["bash", "/Users/swxvno/jarvis/scripts/hud-data.sh"],
                    capture_output=True, text=True, timeout=5,
                )
                return self._send_json(200, json.loads(result.stdout))
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        if path == "/tools":
            return self._send_json(200, {
                "count": len(REGISTRY.names()),
                "tools": [
                    {"name": t, "description": REGISTRY.get(t).description if REGISTRY.get(t) else ""}
                    for t in REGISTRY.names()
                ],
            })

        if path == "/history":
            n = int(params.get("n", ["20"])[0])
            return self._send_json(200, {"entries": history.tail(n)})

        if path == "/stop":
            self._send_json(200, {"status": "stopping"})
            threading.Thread(target=lambda: (time.sleep(0.2), _server.shutdown() if _server else None), daemon=True).start()
            return

        return self._send_json(404, {"error": "not found", "valid": ["/healthz", "/metrics", "/tools", "/history?n=N", "/stop"]})


def start(port: Optional[int] = None) -> int:
    """HTTP server 시작 (별도 thread). 포트 사용 중이면 41418-41430 자동 폴백."""
    global _server
    if _server is not None:
        return _server.server_address[1]

    base_port = port or int(os.environ.get("JARVIS_HEALTH_PORT", "41418"))
    candidates = [base_port] + [p for p in range(41418, 41431) if p != base_port]

    for p in candidates:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", p))
        except OSError:
            sock.close()
            continue
        sock.close()
        _server = ThreadingHTTPServer(("127.0.0.1", p), _Handler)
        t = threading.Thread(target=_server.serve_forever, daemon=True)
        t.start()
        return p
    return -1  # 모든 candidate 사용 중


def stop() -> None:
    global _server
    if _server:
        _server.shutdown()
        _server = None
