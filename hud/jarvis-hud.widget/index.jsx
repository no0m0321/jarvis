// JARVIS HUD — Übersicht widget
// Reads bash /Users/swxvno/jarvis/scripts/hud-data.sh every 1s.
// Reacts to ~/Library/Caches/jarvis-hud.json state for shake / glow / banner effects.

export const command = "bash /Users/swxvno/jarvis/scripts/hud-data.sh"
export const refreshFrequency = 1000

const fmtBytes = (n) => {
  if (n < 1024) return `${n} B/s`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} K/s`
  return `${(n / 1024 / 1024).toFixed(2)} M/s`
}

const Bar = ({ label, value, color }) => (
  <div className="metric">
    <div className="row">
      <span className="label">{label}</span>
      <span className="value" style={{ color: color, textShadow: `0 0 8px ${color}` }}>
        {value.toFixed(1)}%
      </span>
    </div>
    <div className="track">
      <div
        className="fill"
        style={{
          width: `${Math.min(100, value)}%`,
          background: color,
          boxShadow: `0 0 10px ${color}`,
        }}
      />
    </div>
  </div>
)

export const render = ({ output }) => {
  let data = {
    cpu: 0,
    mem: 0,
    net_in: 0,
    net_out: 0,
    jarvis: { state: "idle", message: "", ts: 0 },
    ts: 0,
  }
  try {
    data = JSON.parse(output)
  } catch (e) {}
  const { cpu, mem, net_in, net_out, jarvis } = data
  const state = (jarvis && jarvis.state) || "idle"
  const message = (jarvis && jarvis.message) || ""
  const ts = (jarvis && jarvis.ts) || 0
  const stale = ts > 0 && Date.now() / 1000 - ts > 30
  const effectiveState = stale ? "idle" : state

  const cpuColor = cpu > 80 ? "#ff3b3b" : cpu > 50 ? "#ff9500" : "#00ffe5"
  const memColor = mem > 80 ? "#ff3b3b" : mem > 60 ? "#ff9500" : "#7fffd4"

  // Inline style fallbacks — guarantee animation regardless of CSS parser quirks
  const rootInline =
    effectiveState === "analyzing"
      ? { animation: "hud-shake 0.16s ease-in-out infinite",
          borderColor: "rgba(255, 123, 0, 0.78)",
          boxShadow: "0 0 48px rgba(255, 123, 0, 0.55), inset 0 0 28px rgba(255, 123, 0, 0.12)" }
      : effectiveState === "listening"
      ? { animation: "hud-pulse 1.4s ease-in-out infinite",
          borderColor: "rgba(0, 255, 229, 0.7)" }
      : effectiveState === "speaking"
      ? { borderColor: "rgba(255, 215, 0, 0.7)",
          boxShadow: "0 0 40px rgba(255, 215, 0, 0.45), inset 0 0 24px rgba(255, 215, 0, 0.1)" }
      : {}

  return (
    <div className="hud" style={rootInline}>
      <div className="header">
        <span className="brand">JARVIS HUD</span>
        <span className={`state state-${effectiveState}`}>● {effectiveState.toUpperCase()}</span>
      </div>

      {effectiveState === "analyzing" && (
        <div className="banner banner-analyzing">
          ▣ ANALYZING DATA{message ? ` — ${message}` : ""} ▣
        </div>
      )}
      {effectiveState === "listening" && (
        <div className="banner banner-listening">▶ LISTENING ◀</div>
      )}
      {effectiveState === "speaking" && (
        <div className="banner banner-speaking">◈ SPEAKING ◈</div>
      )}

      <Bar label="CPU" value={cpu} color={cpuColor} />
      <Bar label="MEM" value={mem} color={memColor} />

      <div className="metric net">
        <div className="row">
          <span className="label">NET ↓</span>
          <span className="value">{fmtBytes(net_in)}</span>
        </div>
        <div className="row">
          <span className="label">NET ↑</span>
          <span className="value">{fmtBytes(net_out)}</span>
        </div>
      </div>

      <div className="footer">
        <span>swxvno • jarvis</span>
        <span>{new Date().toLocaleTimeString("en-GB", { hour12: false })}</span>
      </div>
    </div>
  )
}

// Standard CSS (brace + semicolon) — Übersicht의 stylus/emotion 파서 모두 호환.
// nested ampersand 사용하지 않고 평문 selector로 안정성 확보.
export const className = `
  position: absolute;
  top: 60px;
  right: 60px;
  width: 340px;
  padding: 18px 22px;
  font-family: 'SF Mono', 'Menlo', 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #00ffe5;
  background: rgba(2, 8, 16, 0.74);
  border: 1px solid rgba(0, 255, 229, 0.42);
  border-radius: 6px;
  box-shadow: 0 0 32px rgba(0, 255, 229, 0.32), inset 0 0 24px rgba(0, 255, 229, 0.06);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  letter-spacing: 0.06em;
  text-transform: uppercase;

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(0, 255, 229, 0.3);
    font-size: 10px;
  }
  .brand {
    color: #fff;
    font-weight: bold;
    text-shadow: 0 0 14px rgba(0, 255, 229, 0.95);
    letter-spacing: 0.16em;
  }
  .state {
    font-size: 9px;
    letter-spacing: 0.12em;
  }
  .state-idle { color: #4a8a8a; }
  .state-listening {
    color: #00ffe5;
    text-shadow: 0 0 10px rgba(0, 255, 229, 0.85);
    animation: hud-blink 0.8s ease-in-out infinite;
  }
  .state-analyzing {
    color: #ff7b00;
    text-shadow: 0 0 12px rgba(255, 123, 0, 0.95);
    animation: hud-blink 0.28s ease-in-out infinite;
  }
  .state-speaking {
    color: #ffd700;
    text-shadow: 0 0 10px rgba(255, 215, 0, 0.85);
  }

  .banner {
    text-align: center;
    padding: 8px 10px;
    margin-bottom: 12px;
    font-size: 11px;
    border: 1px solid currentColor;
    border-radius: 3px;
    letter-spacing: 0.18em;
  }
  .banner-analyzing {
    color: #ff9500;
    background: rgba(255, 123, 0, 0.18);
    text-shadow: 0 0 10px rgba(255, 123, 0, 0.85);
    animation: hud-blink 0.4s ease-in-out infinite;
  }
  .banner-listening {
    color: #00ffe5;
    background: rgba(0, 255, 229, 0.1);
    text-shadow: 0 0 8px rgba(0, 255, 229, 0.7);
  }
  .banner-speaking {
    color: #ffd700;
    background: rgba(255, 215, 0, 0.1);
    text-shadow: 0 0 8px rgba(255, 215, 0, 0.7);
  }

  .metric { margin-bottom: 12px; }
  .row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
    font-size: 10px;
  }
  .label {
    color: #5fa9a0;
    letter-spacing: 0.14em;
  }
  .value {
    color: #00ffe5;
    text-shadow: 0 0 8px rgba(0, 255, 229, 0.65);
    font-weight: bold;
    font-variant-numeric: tabular-nums;
  }
  .track {
    height: 5px;
    background: rgba(0, 255, 229, 0.1);
    border: 1px solid rgba(0, 255, 229, 0.22);
    overflow: hidden;
    border-radius: 2px;
  }
  .fill {
    height: 100%;
    transition: width 0.4s ease;
  }
  .net .row:last-child { margin-bottom: 0; }

  .footer {
    display: flex;
    justify-content: space-between;
    margin-top: 14px;
    padding-top: 8px;
    border-top: 1px solid rgba(0, 255, 229, 0.22);
    color: #4a8a8a;
    font-size: 9px;
    letter-spacing: 0.18em;
  }

  @keyframes hud-shake {
    0%, 100% { transform: translate(0, 0); }
    20% { transform: translate(-2px, 1px) rotate(-0.3deg); }
    40% { transform: translate(3px, -2px) rotate(0.4deg); }
    60% { transform: translate(-2px, 2px) rotate(-0.2deg); }
    80% { transform: translate(2px, -1px) rotate(0.3deg); }
  }
  @keyframes hud-pulse {
    0%, 100% {
      box-shadow: 0 0 32px rgba(0, 255, 229, 0.32), inset 0 0 24px rgba(0, 255, 229, 0.06);
    }
    50% {
      box-shadow: 0 0 56px rgba(0, 255, 229, 0.65), inset 0 0 36px rgba(0, 255, 229, 0.2);
    }
  }
  @keyframes hud-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
`
