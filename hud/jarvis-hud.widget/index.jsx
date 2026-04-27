// JARVIS HUD v3 — Holographic Dashboard, Premium Edition
// Features:
//   1. 3D wireframe globe + perspective tilt
//   2. 32-particle 3D field orbiting globe (voice-reactive)
//   3. CPU/MEM SVG sparkline (60s rolling history)
//   4. Typewriter banner reveal
//   5. Idle floating motion
//   6. Multi-layer 3D depth (translateZ per element)
//   7. Holographic shimmer + scanlines + corner brackets
//   8. State-driven color theme (cyan / amber / gold / orange-shake)
//   9. Voice RMS reactive — particles 진동 + scale
//  10. Disk / Top process / Response message overlay

export const command = "bash /Users/swxvno/jarvis/scripts/hud-data.sh"
export const refreshFrequency = 1000

// ── Module-level state (preserved across renders by Übersicht) ─────────
const HISTORY_LEN = 60
let cpuHistory = []
let memHistory = []

// 32개 particle: 두 개 orbit ring에 분산 배치
const PARTICLES_RING_A = Array.from({ length: 16 }, (_, i) => ({
  theta: (i / 16) * 360 + Math.random() * 22,
  phi: -8 + Math.random() * 16,
  r: 56 + Math.random() * 14,
  size: 1.5 + Math.random() * 1.8,
}))
const PARTICLES_RING_B = Array.from({ length: 16 }, (_, i) => ({
  theta: (i / 16) * 360 + Math.random() * 22,
  phi: 70 + Math.random() * 30,
  r: 56 + Math.random() * 14,
  size: 1.2 + Math.random() * 1.4,
}))

const fmtBytes = (n) => {
  if (n < 1024) return `${n} B/s`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} K/s`
  return `${(n / 1024 / 1024).toFixed(2)} M/s`
}

const Sparkline = ({ data, color, width = 100, height = 14 }) => {
  if (data.length < 2) return <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} />
  const max = 100
  const pts = data
    .map((v, i) => {
      const x = (i / (HISTORY_LEN - 1)) * width
      const y = height - (Math.min(v, max) / max) * height
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(" ")
  return (
    <svg
      className="sparkline"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
    >
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="0.7"
        strokeLinejoin="round"
        strokeLinecap="round"
        style={{ filter: `drop-shadow(0 0 1.5px ${color})` }}
      />
    </svg>
  )
}

const Bar = ({ label, value, color, history }) => (
  <div className="metric">
    <div className="row">
      <span className="label">{label}</span>
      <span className="value" style={{ color: color, textShadow: `0 0 10px ${color}` }}>
        {value.toFixed(1)}%
      </span>
    </div>
    <div className="track">
      <div
        className="fill"
        style={{
          width: `${Math.min(100, value)}%`,
          background: `linear-gradient(90deg, ${color}, ${color}cc)`,
          boxShadow: `0 0 12px ${color}, 0 0 4px ${color}`,
        }}
      />
    </div>
    <Sparkline data={history} color={color} />
  </div>
)

const Typewriter = ({ text }) => (
  <>
    {Array.from(text).map((c, i) => (
      <span key={i} className="tw-char" style={{ animationDelay: `${i * 28}ms` }}>
        {c === " " ? " " : c}
      </span>
    ))}
  </>
)

const Particle = ({ p, scale, color }) => (
  <div
    className="particle"
    style={{
      transform: `rotateY(${p.theta}deg) rotateX(${p.phi}deg) translateZ(${p.r}px)`,
      width: `${p.size * scale}px`,
      height: `${p.size * scale}px`,
      background: color,
      boxShadow: `0 0 ${4 + scale * 4}px ${color}, 0 0 ${2 + scale * 2}px ${color}`,
    }}
  />
)

export const render = ({ output }) => {
  let data = {
    cpu: 0, mem: 0, net_in: 0, net_out: 0,
    disk: 0, top_proc: "?:0",
    jarvis: { state: "idle", message: "", ts: 0 },
    voice: { rms: 0, peak: 0, ts: 0 },
    ts: 0,
  }
  try { data = JSON.parse(output) } catch (e) {}
  const { cpu, mem, net_in, net_out, disk, top_proc, jarvis, voice } = data
  const state = (jarvis && jarvis.state) || "idle"
  const message = (jarvis && jarvis.message) || ""
  const ts = (jarvis && jarvis.ts) || 0
  const stale = ts > 0 && Date.now() / 1000 - ts > 30
  const effectiveState = stale ? "idle" : state

  // History (모듈 레벨 — refresh 사이 유지)
  cpuHistory.push(cpu)
  memHistory.push(mem)
  if (cpuHistory.length > HISTORY_LEN) cpuHistory.shift()
  if (memHistory.length > HISTORY_LEN) memHistory.shift()

  // Voice RMS (0.0 ~ ~0.1) → particle scale 1.0 ~ 3.0
  const voiceTs = (voice && voice.ts) || 0
  const voiceFresh = voiceTs > 0 && Date.now() / 1000 - voiceTs < 3
  const rms = voiceFresh ? Math.min(0.1, (voice && voice.rms) || 0) : 0
  const voiceScale = 1 + rms * 25  // 0.0→1.0, 0.04→2.0

  const cpuColor = cpu > 80 ? "#ff3b3b" : cpu > 50 ? "#ff9500" : "#00ffe5"
  const memColor = mem > 80 ? "#ff3b3b" : mem > 60 ? "#ff9500" : "#7fffd4"

  // 상태별 outer style (inline)
  const stateStyles = {
    analyzing: {
      animation: "hud-shake 0.16s ease-in-out infinite",
      borderColor: "rgba(255, 123, 0, 0.78)",
      boxShadow:
        "0 0 56px rgba(255, 123, 0, 0.55), inset 0 0 32px rgba(255, 123, 0, 0.12), 0 24px 60px rgba(0, 0, 0, 0.6)",
    },
    listening: {
      animation: "hud-pulse 1.4s ease-in-out infinite",
      borderColor: "rgba(0, 255, 229, 0.7)",
    },
    speaking: {
      borderColor: "rgba(255, 215, 0, 0.7)",
      boxShadow:
        "0 0 48px rgba(255, 215, 0, 0.5), inset 0 0 28px rgba(255, 215, 0, 0.12), 0 24px 60px rgba(0, 0, 0, 0.6)",
    },
    idle: {
      animation: "hud-float 6s ease-in-out infinite",
    },
  }
  const rootStyle = stateStyles[effectiveState] || {}

  const accent =
    effectiveState === "analyzing" ? "#ff7b00"
    : effectiveState === "speaking" ? "#ffd700"
    : "#00ffe5"
  const ringHi = effectiveState === "analyzing" ? "rgba(255, 123, 0, 0.9)"
    : effectiveState === "speaking" ? "rgba(255, 215, 0, 0.85)"
    : "rgba(0, 255, 229, 0.78)"
  const ringLo = effectiveState === "analyzing" ? "rgba(255, 123, 0, 0.55)"
    : effectiveState === "speaking" ? "rgba(255, 215, 0, 0.55)"
    : "rgba(0, 255, 229, 0.55)"

  const banner =
    effectiveState === "analyzing" ? `▣ ANALYZING DATA${message ? " — " + message : ""} ▣`
    : effectiveState === "listening" ? "▶ LISTENING ◀"
    : effectiveState === "speaking" ? `◈ ${message || "SPEAKING"} ◈`
    : null

  return (
    <div className="hud" style={rootStyle}>
      <span className="corner corner-tl" />
      <span className="corner corner-tr" />
      <span className="corner corner-bl" />
      <span className="corner corner-br" />

      <div className="header">
        <span className="brand">▣ JARVIS HUD</span>
        <span className={`state state-${effectiveState}`}>● {effectiveState.toUpperCase()}</span>
      </div>

      <div className="globe-container">
        <div className="globe">
          <div className="ring ring-1" style={{ borderColor: ringHi, boxShadow: `0 0 16px ${ringHi}` }} />
          <div className="ring ring-2" style={{ borderColor: ringLo, boxShadow: `0 0 12px ${ringLo}` }} />
          <div className="ring ring-3"
            style={{
              borderColor: effectiveState === "analyzing" ? "rgba(255, 215, 0, 0.65)" : "rgba(127, 255, 212, 0.55)",
              boxShadow: effectiveState === "analyzing" ? "0 0 12px rgba(255, 215, 0, 0.5)" : "0 0 10px rgba(127, 255, 212, 0.4)",
            }}
          />
          <div className="core"
            style={{
              background: `radial-gradient(circle, ${ringHi}, ${ringHi}33 60%, transparent 80%)`,
              boxShadow: `0 0 ${30 + voiceScale * 10}px ${ringHi}, 0 0 60px ${ringHi}80`,
              transform: `scale(${0.9 + voiceScale * 0.1})`,
            }}
          />
          <div className="orbit orbit-a">
            {PARTICLES_RING_A.map((p, i) => (
              <Particle key={`a${i}`} p={p} scale={voiceScale} color={accent} />
            ))}
          </div>
          <div className="orbit orbit-b">
            {PARTICLES_RING_B.map((p, i) => (
              <Particle key={`b${i}`} p={p} scale={voiceScale} color={ringLo} />
            ))}
          </div>
          <div className="radar-sweep" />
        </div>
        <div className="globe-label">CORE • {effectiveState.toUpperCase()}</div>
      </div>

      {banner && (
        <div className={`banner banner-${effectiveState}`} key={effectiveState + banner}>
          <Typewriter text={banner} />
        </div>
      )}

      <Bar label="CPU" value={cpu} color={cpuColor} history={cpuHistory} />
      <Bar label="MEM" value={mem} color={memColor} history={memHistory} />

      <div className="metric net">
        <div className="row"><span className="label">NET ↓</span><span className="value">{fmtBytes(net_in)}</span></div>
        <div className="row"><span className="label">NET ↑</span><span className="value">{fmtBytes(net_out)}</span></div>
      </div>

      <div className="extra">
        <div className="row">
          <span className="label">DISK</span>
          <span className="value">{disk}%</span>
        </div>
        <div className="row">
          <span className="label">TOP</span>
          <span className="value tiny">{top_proc}</span>
        </div>
      </div>

      <div className="footer">
        <span>swxvno • jarvis</span>
        <span>{new Date().toLocaleTimeString("en-GB", { hour12: false })}</span>
      </div>
    </div>
  )
}

export const className = `
  position: absolute;
  top: 60px;
  right: 60px;
  width: 360px;
  padding: 22px 24px;
  perspective: 1500px;
  transform-style: preserve-3d;
  font-family: 'SF Mono', 'Menlo', 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #00ffe5;
  background: linear-gradient(135deg, rgba(2, 8, 16, 0.86), rgba(0, 22, 30, 0.78));
  border: 1px solid rgba(0, 255, 229, 0.45);
  border-radius: 8px;
  box-shadow:
    0 0 42px rgba(0, 255, 229, 0.35),
    inset 0 0 28px rgba(0, 255, 229, 0.08),
    0 24px 60px rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  overflow: hidden;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  will-change: transform, box-shadow;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: repeating-linear-gradient(
      0deg,
      rgba(0, 255, 229, 0.05) 0px,
      rgba(0, 255, 229, 0.05) 1px,
      transparent 1px,
      transparent 3px
    );
    mix-blend-mode: screen;
    z-index: 1;
    border-radius: 8px;
  }
  &::after {
    content: '';
    position: absolute;
    inset: -50%;
    pointer-events: none;
    background: linear-gradient(
      115deg,
      transparent 30%,
      rgba(0, 255, 229, 0.1) 48%,
      rgba(255, 215, 0, 0.05) 56%,
      transparent 75%
    );
    background-size: 200% 200%;
    animation: hud-shimmer 6s linear infinite;
    z-index: 2;
  }

  .corner {
    position: absolute;
    width: 12px;
    height: 12px;
    border: 2px solid rgba(0, 255, 229, 0.9);
    z-index: 3;
    box-shadow: 0 0 8px rgba(0, 255, 229, 0.7);
  }
  .corner-tl { top: 5px; left: 5px; border-right: 0; border-bottom: 0; }
  .corner-tr { top: 5px; right: 5px; border-left: 0; border-bottom: 0; }
  .corner-bl { bottom: 5px; left: 5px; border-right: 0; border-top: 0; }
  .corner-br { bottom: 5px; right: 5px; border-left: 0; border-top: 0; }

  .header {
    position: relative;
    z-index: 5;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(0, 255, 229, 0.3);
    font-size: 10px;
    transform: translateZ(10px);
  }
  .brand {
    color: #fff;
    font-weight: bold;
    text-shadow: 0 0 16px rgba(0, 255, 229, 1);
    letter-spacing: 0.18em;
  }
  .state { font-size: 9px; letter-spacing: 0.12em; }
  .state-idle { color: #4a8a8a; }
  .state-listening {
    color: #00ffe5;
    text-shadow: 0 0 10px rgba(0, 255, 229, 0.85);
    animation: hud-blink 0.8s ease-in-out infinite;
  }
  .state-analyzing {
    color: #ff7b00;
    text-shadow: 0 0 14px rgba(255, 123, 0, 0.95);
    animation: hud-blink 0.28s ease-in-out infinite;
  }
  .state-speaking {
    color: #ffd700;
    text-shadow: 0 0 12px rgba(255, 215, 0, 0.9);
  }

  .globe-container {
    position: relative;
    z-index: 5;
    height: 130px;
    margin: 4px auto 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    perspective: 800px;
    transform: translateZ(0);
  }
  .globe {
    position: relative;
    width: 96px;
    height: 96px;
    transform-style: preserve-3d;
    animation: hud-globe-spin 11s linear infinite;
  }
  .ring {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    box-sizing: border-box;
    border-width: 1px;
    border-style: solid;
  }
  .ring-1 { transform: rotateX(72deg); }
  .ring-2 { transform: rotateY(72deg); }
  .ring-3 { transform: rotateZ(45deg) rotateX(38deg); }
  .core {
    position: absolute;
    inset: 36%;
    border-radius: 50%;
    animation: hud-core-pulse 1.9s ease-in-out infinite;
    transition: box-shadow 0.15s, transform 0.15s;
  }

  .orbit {
    position: absolute;
    inset: 0;
    transform-style: preserve-3d;
    pointer-events: none;
  }
  .orbit-a { animation: orbit-spin 14s linear infinite; }
  .orbit-b { animation: orbit-spin 11s linear infinite reverse; }
  .particle {
    position: absolute;
    top: 50%;
    left: 50%;
    margin-left: -1px;
    margin-top: -1px;
    border-radius: 50%;
    transition: width 0.18s, height 0.18s, box-shadow 0.18s;
  }

  .radar-sweep {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 110%;
    height: 110%;
    border-radius: 50%;
    background: conic-gradient(
      from 0deg,
      transparent 0deg,
      rgba(0, 255, 229, 0.22) 28deg,
      transparent 56deg
    );
    transform: translate(-50%, -50%);
    animation: hud-radar 3.4s linear infinite;
    pointer-events: none;
    filter: blur(1.5px);
  }
  .globe-label {
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    font-size: 8px;
    color: rgba(0, 255, 229, 0.65);
    letter-spacing: 0.22em;
    white-space: nowrap;
    text-shadow: 0 0 8px rgba(0, 255, 229, 0.5);
  }

  .banner {
    position: relative;
    z-index: 5;
    text-align: center;
    padding: 8px 10px;
    margin-bottom: 12px;
    font-size: 11px;
    border: 1px solid currentColor;
    border-radius: 3px;
    letter-spacing: 0.18em;
    transform: translateZ(8px);
  }
  .banner-analyzing {
    color: #ff9500;
    background: rgba(255, 123, 0, 0.18);
    text-shadow: 0 0 12px rgba(255, 123, 0, 0.9);
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
  .tw-char {
    display: inline-block;
    opacity: 0;
    transform: translateY(2px);
    animation: tw-reveal 0.32s forwards;
  }

  .metric {
    position: relative;
    z-index: 5;
    margin-bottom: 12px;
    transform: translateZ(4px);
  }
  .row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
    font-size: 10px;
  }
  .label { color: #5fa9a0; letter-spacing: 0.14em; }
  .value {
    color: #00ffe5;
    text-shadow: 0 0 8px rgba(0, 255, 229, 0.65);
    font-weight: bold;
    font-variant-numeric: tabular-nums;
  }
  .value.tiny {
    font-size: 8px;
    letter-spacing: 0;
    text-transform: lowercase;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .track {
    height: 6px;
    background: rgba(0, 255, 229, 0.08);
    border: 1px solid rgba(0, 255, 229, 0.22);
    overflow: hidden;
    border-radius: 2px;
    position: relative;
  }
  .fill { height: 100%; transition: width 0.4s ease; }
  .sparkline {
    width: 100%;
    height: 14px;
    margin-top: 3px;
    opacity: 0.85;
  }
  .net .row:last-child { margin-bottom: 0; }

  .extra {
    position: relative;
    z-index: 5;
    margin-bottom: 12px;
    padding: 8px 10px;
    background: rgba(0, 255, 229, 0.04);
    border: 1px solid rgba(0, 255, 229, 0.18);
    border-radius: 3px;
    transform: translateZ(2px);
  }
  .extra .row { font-size: 9px; margin-bottom: 3px; }
  .extra .row:last-child { margin-bottom: 0; }

  .footer {
    position: relative;
    z-index: 5;
    display: flex;
    justify-content: space-between;
    margin-top: 14px;
    padding-top: 8px;
    border-top: 1px solid rgba(0, 255, 229, 0.22);
    color: #4a8a8a;
    font-size: 9px;
    letter-spacing: 0.18em;
    transform: translateZ(-3px);
  }

  @keyframes hud-globe-spin {
    from { transform: rotateY(0deg) rotateX(15deg); }
    to { transform: rotateY(360deg) rotateX(15deg); }
  }
  @keyframes orbit-spin {
    from { transform: rotateY(0deg); }
    to { transform: rotateY(360deg); }
  }
  @keyframes hud-core-pulse {
    0%, 100% { opacity: 0.85; }
    50% { opacity: 1; }
  }
  @keyframes hud-radar {
    from { transform: translate(-50%, -50%) rotate(0deg); }
    to { transform: translate(-50%, -50%) rotate(360deg); }
  }
  @keyframes hud-shimmer {
    0% { background-position: 200% 200%; }
    100% { background-position: -200% -200%; }
  }
  @keyframes hud-shake {
    0%, 100% { transform: rotateY(-3deg) rotateX(2deg) translate(0, 0); }
    20% { transform: rotateY(-3deg) rotateX(2deg) translate(-2px, 1px); }
    40% { transform: rotateY(-3deg) rotateX(2deg) translate(3px, -2px); }
    60% { transform: rotateY(-3deg) rotateX(2deg) translate(-2px, 2px); }
    80% { transform: rotateY(-3deg) rotateX(2deg) translate(2px, -1px); }
  }
  @keyframes hud-pulse {
    0%, 100% {
      box-shadow: 0 0 36px rgba(0, 255, 229, 0.32), inset 0 0 24px rgba(0, 255, 229, 0.06), 0 24px 60px rgba(0, 0, 0, 0.55);
      transform: rotateY(-3deg) rotateX(2deg);
    }
    50% {
      box-shadow: 0 0 64px rgba(0, 255, 229, 0.7), inset 0 0 36px rgba(0, 255, 229, 0.22), 0 24px 60px rgba(0, 0, 0, 0.55);
      transform: rotateY(-3deg) rotateX(2deg) scale(1.005);
    }
  }
  @keyframes hud-float {
    0%, 100% { transform: rotateY(-3deg) rotateX(2deg) translateY(0); }
    50% { transform: rotateY(-3deg) rotateX(2deg) translateY(-3px); }
  }
  @keyframes hud-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  @keyframes tw-reveal {
    to { opacity: 1; transform: translateY(0); }
  }
`
