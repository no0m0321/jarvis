"""Lightweight health-check HTTP server + dashboard UI.

GET /          → HTML dashboard (live status, tools, history)
GET /healthz   → {"status":"ok","uptime":<sec>,"hud":{...}}
GET /metrics   → JSON metrics dump
GET /tools     → 등록된 tool 목록
GET /history?n=20 → 마지막 n개 conversation turn
GET /stop      → 서버 종료

Daemon이 별도 thread로 실행. JARVIS_HEALTH_PORT 환경변수로 포트 변경 (기본 41418).
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
_server: Optional[ThreadingHTTPServer] = None


_DASHBOARD_HTML = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>JARVIS · Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Orbitron:wght@500;700&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root {
  --cyan: #4cc9ff;
  --cyan-bright: #7de0ff;
  --cyan-dim: #5fb4d4;
  --cyan-glow: rgba(76, 201, 255, 0.55);
  --cyan-soft: rgba(76, 201, 255, 0.10);
  --bg-0: #02060d;
  --bg-1: #050b16;
  --bg-2: #0a1320;
  --line: rgba(76, 201, 255, 0.14);
  --line-strong: rgba(76, 201, 255, 0.32);
  --text: #d6effa;
  --text-dim: #7896a4;
  --listening: #4cc9ff;
  --analyzing: #ffd166;
  --speaking: #ff8a4c;
  --idle: #5fb4d4;
}
* { margin:0; padding:0; box-sizing:border-box; }
html, body {
  background: var(--bg-0);
  color: var(--text);
  font-family: 'Outfit', -apple-system, system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  min-height: 100vh;
}
body {
  background:
    radial-gradient(ellipse 80% 60% at 50% 0%, rgba(0, 132, 199, 0.18), transparent 60%),
    radial-gradient(ellipse 50% 50% at 85% 80%, rgba(76, 201, 255, 0.06), transparent 70%),
    var(--bg-0);
  padding: 32px 24px 80px;
}

/* ── Header ── */
.header {
  max-width: 1280px;
  margin: 0 auto 28px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}
.brand {
  font-family: 'Orbitron', sans-serif;
  font-weight: 700;
  font-size: 22px;
  letter-spacing: 0.32em;
  background: linear-gradient(135deg, var(--text) 0%, var(--cyan-bright) 80%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.brand .sub { font-size: 11px; color: var(--text-dim); letter-spacing: 0.24em; font-weight:400; margin-left: 12px;}
.header-meta { display: flex; align-items: center; gap: 14px; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--text-dim); }
.live-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--cyan-bright);
  box-shadow: 0 0 8px var(--cyan-glow);
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1;}50%{opacity:0.4;} }
.header-meta button {
  background: var(--bg-1);
  color: var(--cyan);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  cursor: pointer;
  letter-spacing: 0.08em;
  transition: all 0.15s ease;
}
.header-meta button:hover { background: var(--cyan-soft); border-color: var(--line-strong); }
.header-meta button.paused { color: var(--analyzing); }

/* ── Grid ── */
.grid {
  max-width: 1280px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}
@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }

/* ── Card ── */
.card {
  background: linear-gradient(180deg, rgba(10,19,32,0.85), rgba(5,11,22,0.85));
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 24px;
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(8px);
}
.card::before {
  content:""; position: absolute; top:0; left:0; right:0; height: 1px;
  background: linear-gradient(90deg, transparent, var(--cyan-glow), transparent);
}
.card h2 {
  font-family: 'Orbitron', sans-serif;
  font-weight: 500;
  font-size: 11px;
  letter-spacing: 0.24em;
  color: var(--cyan-bright);
  text-transform: uppercase;
  margin-bottom: 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card h2 .badge {
  background: var(--cyan-soft);
  color: var(--cyan-bright);
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  letter-spacing: 0.12em;
  border: 1px solid var(--line-strong);
}
.full-row { grid-column: 1 / -1; }

/* ── Hero (state) ── */
.hero {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 28px;
  align-items: center;
  padding: 28px;
}
.hero-orb {
  width: 120px; height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, var(--cyan-bright), var(--cyan) 60%, #0084c7 100%);
  box-shadow: 0 0 60px var(--cyan-glow), 0 0 0 1px rgba(255,255,255,0.06) inset;
  position: relative;
  animation: orbPulse 2.4s ease-in-out infinite;
}
@keyframes orbPulse {
  0%,100% { transform: scale(1); box-shadow: 0 0 60px var(--cyan-glow); }
  50%     { transform: scale(1.04); box-shadow: 0 0 90px var(--cyan-glow); }
}
.hero-orb.state-idle      { background: radial-gradient(circle at 35% 35%, #aac4d0, var(--idle), #2a4a5a); animation-duration: 4s; }
.hero-orb.state-listening { background: radial-gradient(circle at 35% 35%, var(--cyan-bright), var(--listening), #0084c7); animation-duration: 1.2s; }
.hero-orb.state-analyzing { background: radial-gradient(circle at 35% 35%, #fff0ad, var(--analyzing), #b88800); animation-duration: 0.8s; }
.hero-orb.state-speaking  { background: radial-gradient(circle at 35% 35%, #ffc8a4, var(--speaking), #b03f00); animation-duration: 1.0s; }
.hero-orb::after {
  content:""; position: absolute; inset: -8px;
  border-radius: 50%;
  border: 1px solid var(--cyan-glow);
  animation: ring 2.4s ease-out infinite;
}
@keyframes ring { 0%{transform:scale(1);opacity:1;} 100%{transform:scale(1.4);opacity:0;} }
.hero-text h3 {
  font-family: 'Orbitron', sans-serif;
  font-size: 32px;
  letter-spacing: 0.08em;
  margin-bottom: 8px;
  text-transform: uppercase;
}
.hero-text h3.state-idle      { color: var(--idle); }
.hero-text h3.state-listening { color: var(--listening); text-shadow: 0 0 20px var(--cyan-glow); }
.hero-text h3.state-analyzing { color: var(--analyzing); text-shadow: 0 0 20px rgba(255,209,102,0.4); }
.hero-text h3.state-speaking  { color: var(--speaking); text-shadow: 0 0 20px rgba(255,138,76,0.4); }
.hero-text .msg {
  color: var(--text-dim);
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  margin-bottom: 14px;
  min-height: 18px;
}
.hero-stats {
  display: flex;
  gap: 28px;
  flex-wrap: wrap;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}
.hero-stats .stat-block {
  border-left: 2px solid var(--line);
  padding-left: 14px;
}
.hero-stats .stat-block .lbl { color: var(--text-dim); font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px;}
.hero-stats .stat-block .num { color: var(--cyan-bright); font-size: 22px; font-weight: 500; }

/* ── Stat list ── */
.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid rgba(76,201,255,0.06);
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
}
.stat-row:last-child { border-bottom: none; }
.stat-row .k { color: var(--text-dim); }
.stat-row .v { color: var(--text); font-weight: 500; }

/* ── Tools list ── */
.tools-search {
  width: 100%;
  background: var(--bg-1);
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  margin-bottom: 14px;
  outline: none;
  transition: border-color 0.15s ease;
}
.tools-search:focus { border-color: var(--cyan-dim); box-shadow: 0 0 0 3px var(--cyan-soft); }
.tools-list { max-height: 360px; overflow-y: auto; padding-right: 6px; }
.tools-list::-webkit-scrollbar { width: 6px; }
.tools-list::-webkit-scrollbar-thumb { background: var(--line); border-radius: 3px; }
.tool {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(76,201,255,0.04);
  font-size: 12px;
}
.tool:last-child { border-bottom: none; }
.tool b { color: var(--cyan-bright); font-family: 'JetBrains Mono', monospace; font-weight: 500; min-width: 140px; }
.tool .desc { color: var(--text-dim); flex: 1; }

/* ── History ── */
.history-list { max-height: 420px; overflow-y: auto; padding-right: 6px; }
.history-list::-webkit-scrollbar { width: 6px; }
.history-list::-webkit-scrollbar-thumb { background: var(--line); border-radius: 3px; }
.turn { padding: 12px 0; border-bottom: 1px solid rgba(76,201,255,0.05); }
.turn:last-child { border-bottom: none; }
.turn-head {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}
.turn-head .role-user      { color: var(--cyan-bright); }
.turn-head .role-assistant { color: var(--analyzing); }
.turn-head .role-other     { color: var(--text-dim); }
.turn-head .ts             { color: var(--text-dim); }
.turn-content {
  color: var(--text);
  font-size: 13px;
  white-space: pre-wrap;
  max-height: 100px;
  overflow: hidden;
  position: relative;
}
.turn-content::after {
  content: ""; position: absolute; bottom: 0; left: 0; right: 0; height: 24px;
  background: linear-gradient(180deg, transparent, var(--bg-2));
  pointer-events: none;
}
.turn .meta {
  margin-top: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--text-dim);
  display: flex;
  gap: 12px;
}
.turn .meta .tier-fast { color: var(--cyan-bright); }
.turn .meta .tier-deep { color: var(--analyzing); }

/* ── Bar chart (routing tier) ── */
.bar-chart { padding: 4px 0; }
.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}
.bar-row .lbl { width: 56px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; font-size: 10px; }
.bar-row .bar-track {
  flex: 1;
  height: 6px;
  background: var(--bg-1);
  border-radius: 3px;
  overflow: hidden;
}
.bar-row .bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--cyan), var(--cyan-bright));
  border-radius: 3px;
  transition: width 0.5s cubic-bezier(.2,.7,.2,1);
}
.bar-row .bar-fill.deep { background: linear-gradient(90deg, var(--analyzing), #ffe6a0); }
.bar-row .num { color: var(--cyan-bright); width: 56px; text-align: right; }

/* ── Footer ── */
.footer {
  max-width: 1280px;
  margin: 32px auto 0;
  text-align: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--text-dim);
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

/* ── Empty state ── */
.empty { color: var(--text-dim); font-size: 12px; padding: 24px 0; text-align: center; font-family: 'JetBrains Mono', monospace; }
</style></head>
<body>

<div class="header">
  <div class="brand">JARVIS<span class="sub">CONTROL · CENTER</span></div>
  <div class="header-meta">
    <span><span class="live-dot" id="liveDot"></span> LIVE · <span id="port">PORTNUM</span></span>
    <button id="pauseBtn" type="button">⏸ PAUSE</button>
  </div>
</div>

<div class="grid">
  <!-- Hero state -->
  <div class="card hero">
    <div class="hero-orb state-idle" id="orb"></div>
    <div class="hero-text">
      <h3 id="stateLabel" class="state-idle">IDLE</h3>
      <div class="msg" id="stateMsg">— ready —</div>
      <div class="hero-stats">
        <div class="stat-block"><div class="lbl">UPTIME</div><div class="num" id="upt">0s</div></div>
        <div class="stat-block"><div class="lbl">TOOLS</div><div class="num" id="tcCount">0</div></div>
        <div class="stat-block"><div class="lbl">TURNS</div><div class="num" id="turnsCount">0</div></div>
        <div class="stat-block"><div class="lbl">LATENCY</div><div class="num" id="latencyAvg">—</div></div>
      </div>
    </div>
  </div>

  <!-- Routing tier -->
  <div class="card">
    <h2>Routing Tier <span class="badge" id="routeTotal">0</span></h2>
    <div class="bar-chart" id="routeBars">
      <div class="empty">대기 중…</div>
    </div>
  </div>

  <!-- System -->
  <div class="card">
    <h2>System</h2>
    <div id="sys"><div class="empty">불러오는 중…</div></div>
  </div>

  <!-- Tools -->
  <div class="card">
    <h2>Tools <span class="badge" id="tcBadge">0</span></h2>
    <input type="text" class="tools-search" id="toolSearch" placeholder="도구 이름 검색…"/>
    <div class="tools-list" id="tools"><div class="empty">불러오는 중…</div></div>
  </div>

  <!-- History -->
  <div class="card full-row">
    <h2>Recent History <span class="badge"><span id="histCount">0</span> turns</span></h2>
    <div class="history-list" id="hist"><div class="empty">대화 기록 없음</div></div>
  </div>
</div>

<div class="footer">localhost:<span id="portFoot">PORTNUM</span> · 자동 새로고침 2초 · /healthz · /tools · /history</div>

<script>
const $ = (id) => document.getElementById(id);
let paused = false;
let allTools = [];

async function jget(p) {
  const r = await fetch(p);
  if (!r.ok) throw new Error(p + ' → ' + r.status);
  return await r.json();
}

function row(k, v) {
  return `<div class="stat-row"><span class="k">${k}</span><span class="v">${v}</span></div>`;
}

function fmtUptime(sec) {
  if (sec < 60) return Math.floor(sec) + 's';
  if (sec < 3600) return Math.floor(sec/60) + 'm ' + Math.floor(sec%60) + 's';
  if (sec < 86400) return Math.floor(sec/3600) + 'h ' + Math.floor((sec%3600)/60) + 'm';
  return Math.floor(sec/86400) + 'd ' + Math.floor((sec%86400)/3600) + 'h';
}

function setState(state, message) {
  state = state || 'idle';
  const orb = $('orb');
  const lbl = $('stateLabel');
  orb.className = 'hero-orb state-' + state;
  lbl.className = 'state-' + state;
  lbl.textContent = state.toUpperCase();
  $('stateMsg').textContent = message ? '› ' + message : '— ready —';
}

function escapeHtml(s) {
  return (s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function renderHistory(entries) {
  const sorted = (entries || []).slice().sort((a, b) => b.ts - a.ts);
  if (!sorted.length) {
    $('hist').innerHTML = '<div class="empty">대화 기록 없음</div>';
    return;
  }
  $('hist').innerHTML = sorted.map(e => {
    const role = e.role || 'other';
    const klass = (role === 'user' || role === 'assistant') ? 'role-' + role : 'role-other';
    const tier = e.meta && e.meta.router && e.meta.router.tier;
    const reason = e.meta && e.meta.router && e.meta.router.reason;
    const tierBadge = tier ? `<span class="tier-${tier}">${tier.toUpperCase()}</span>${reason ? ' · ' + escapeHtml(reason) : ''}` : '';
    return `<div class="turn">
      <div class="turn-head">
        <span class="${klass}">${role}</span>
        <span class="ts">${new Date(e.ts*1000).toLocaleTimeString()}</span>
      </div>
      <div class="turn-content">${escapeHtml(e.content).slice(0, 600)}</div>
      ${tierBadge ? `<div class="meta">${tierBadge}</div>` : ''}
    </div>`;
  }).join('');
}

function renderRouting(entries) {
  const counts = { fast: 0, deep: 0 };
  let total = 0;
  let latencyAcc = 0, latencyN = 0;
  for (const e of entries || []) {
    const tier = e.meta && e.meta.router && e.meta.router.tier;
    if (tier === 'fast' || tier === 'deep') {
      counts[tier]++;
      total++;
    }
  }
  $('routeTotal').textContent = total + ' calls';
  if (total === 0) {
    $('routeBars').innerHTML = '<div class="empty">라우팅 데이터 없음</div>';
    $('latencyAvg').textContent = '—';
    return;
  }
  const fastPct = Math.round(counts.fast / total * 100);
  const deepPct = Math.round(counts.deep / total * 100);
  $('routeBars').innerHTML = `
    <div class="bar-row">
      <div class="lbl">Fast</div>
      <div class="bar-track"><div class="bar-fill" style="width:${fastPct}%"></div></div>
      <div class="num">${counts.fast} · ${fastPct}%</div>
    </div>
    <div class="bar-row">
      <div class="lbl">Deep</div>
      <div class="bar-track"><div class="bar-fill deep" style="width:${deepPct}%"></div></div>
      <div class="num">${counts.deep} · ${deepPct}%</div>
    </div>`;
}

function renderTools() {
  const q = $('toolSearch').value.trim().toLowerCase();
  const filtered = q ? allTools.filter(t => t.name.toLowerCase().includes(q) || (t.description || '').toLowerCase().includes(q)) : allTools;
  if (!filtered.length) {
    $('tools').innerHTML = `<div class="empty">${q ? '일치하는 도구 없음' : '도구 없음'}</div>`;
    return;
  }
  $('tools').innerHTML = filtered.slice(0, 100).map(t =>
    `<div class="tool"><b>${escapeHtml(t.name)}</b><span class="desc">${escapeHtml((t.description || '').slice(0, 100))}</span></div>`
  ).join('') + (filtered.length > 100 ? `<div class="empty">+ ${filtered.length - 100}개 더 (검색으로 좁히기)</div>` : '');
}

$('toolSearch').addEventListener('input', renderTools);

$('pauseBtn').addEventListener('click', () => {
  paused = !paused;
  $('pauseBtn').textContent = paused ? '▶ RESUME' : '⏸ PAUSE';
  $('pauseBtn').classList.toggle('paused', paused);
  $('liveDot').style.opacity = paused ? '0.3' : '1';
});

async function tick() {
  if (paused) return;
  try {
    const h = await jget('/healthz');
    setState((h.hud && h.hud.state) || 'idle', h.hud && h.hud.message);
    $('upt').textContent = fmtUptime(h.uptime_sec || 0);
    $('tcCount').textContent = h.tools_count || 0;
    $('sys').innerHTML =
      row('Status', h.status) +
      row('Uptime', fmtUptime(h.uptime_sec || 0)) +
      row('Tools registered', h.tools_count) +
      row('HUD update', (h.hud && h.hud.ts) ? new Date(h.hud.ts*1000).toLocaleTimeString() : '—');

    const t = await jget('/tools');
    allTools = t.tools || [];
    $('tcBadge').textContent = t.count || allTools.length;
    renderTools();

    const hi = await jget('/history?n=30');
    const entries = hi.entries || [];
    $('turnsCount').textContent = entries.length;
    $('histCount').textContent = entries.length;
    renderHistory(entries);
    renderRouting(entries);
  } catch (e) {
    console.warn('[dashboard]', e);
  }
}

tick();
setInterval(tick, 2000);
</script>
</body></html>"""


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

    def _send_html(self, code: int, html: str) -> None:
        data = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        from jarvis import history
        from jarvis.tools import REGISTRY

        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/" or path == "/ui":
            port = self.server.server_address[1]
            html = _DASHBOARD_HTML.replace("PORTNUM", str(port))  # str.replace는 모든 occurrence
            return self._send_html(200, html)

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
            from pathlib import Path
            script = Path(__file__).resolve().parents[2] / "scripts" / "hud-data.sh"
            try:
                result = subprocess.run(
                    ["bash", str(script)],
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
