// JARVIS HUD v4 — Cinematic Voice Visualizer
// 검정 배경 + 60개 3D particle cloud + voice-reactive (RMS에 따라 폭발/수축)
// 미니멀: 큰 particle sphere가 메인, 작은 mini-stats가 하단.
// React.Fragment는 사용 X (Übersicht jsx 환경 호환).

export const command = "bash /Users/swxvno/jarvis/scripts/hud-data.sh"
export const refreshFrequency = 1000

// ── Module-level state ─────────────────────────────────────────────────
const HISTORY_LEN = 40
let cpuHistory = []
let memHistory = []

// 60개 particle: 두 spherical layer (inner 30, outer 30)
const mkParticle = (theta, phi, r, sizeBase) => ({ theta, phi, r, size: sizeBase })
const PARTICLES = []
for (let i = 0; i < 30; i++) {
  PARTICLES.push(
    mkParticle(
      Math.random() * 360,
      Math.random() * 180 - 90,
      52 + Math.random() * 18,
      1.4 + Math.random() * 1.2
    )
  )
}
for (let i = 0; i < 30; i++) {
  PARTICLES.push(
    mkParticle(
      Math.random() * 360,
      Math.random() * 180 - 90,
      82 + Math.random() * 22,
      0.9 + Math.random() * 1.0
    )
  )
}

const fmtBytes = (n) => {
  if (n < 1024) return `${n}B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)}K`
  return `${(n / 1024 / 1024).toFixed(2)}M`
}

const Sparkline = ({ data, color, width = 60, height = 8 }) => {
  if (data.length < 2) return null
  const pts = data
    .map((v, i) => {
      const x = (i / (HISTORY_LEN - 1)) * width
      const y = height - (Math.min(v, 100) / 100) * height
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
        strokeWidth="0.6"
        style={{ filter: `drop-shadow(0 0 1px ${color})` }}
      />
    </svg>
  )
}

export const render = ({ output }) => {
  let data = {
    cpu: 0, mem: 0, net_in: 0, net_out: 0,
    disk: 0, top_proc: "?:0",
    jarvis: { state: "idle", message: "", ts: 0 },
    voice: { rms: 0, peak: 0, ts: 0 },
    ts: 0,
  }
  try { data = JSON.parse(output) } catch (e) {}
  const { cpu, mem, net_in, net_out, disk, jarvis, voice } = data
  const state = (jarvis && jarvis.state) || "idle"
  const message = (jarvis && jarvis.message) || ""
  const ts = (jarvis && jarvis.ts) || 0
  const stale = ts > 0 && Date.now() / 1000 - ts > 30
  const effectiveState = stale ? "idle" : state

  cpuHistory.push(cpu)
  memHistory.push(mem)
  if (cpuHistory.length > HISTORY_LEN) cpuHistory.shift()
  if (memHistory.length > HISTORY_LEN) memHistory.shift()

  // Voice RMS (마이크 음량) → particle 폭발
  const voiceTs = (voice && voice.ts) || 0
  const voiceFresh = voiceTs > 0 && Date.now() / 1000 - voiceTs < 3
  const rms = voiceFresh ? Math.min(0.12, (voice && voice.rms) || 0) : 0
  // RMS 0.0 → 1.0 (정상 size), 0.06 → 2.5 (폭발), 0.12 → 4.0 (큰 폭발)
  const voiceScale = 1 + rms * 30
  // particle 외향 push (voice 폭발 시 멀리 퍼짐)
  const voicePush = rms * 60

  // 상태별 accent 색
  const accent =
    effectiveState === "analyzing" ? "#ff7b00"
    : effectiveState === "speaking" ? "#ffd700"
    : effectiveState === "listening" ? "#00ffe5"
    : "#5fdfd0"
  const accentSoft =
    effectiveState === "analyzing" ? "rgba(255, 123, 0, 0.55)"
    : effectiveState === "speaking" ? "rgba(255, 215, 0, 0.55)"
    : effectiveState === "listening" ? "rgba(0, 255, 229, 0.6)"
    : "rgba(95, 223, 208, 0.45)"

  // 외곽 ring color
  const outerStyle = {
    borderColor:
      effectiveState === "analyzing" ? "rgba(255, 123, 0, 0.7)"
      : effectiveState === "speaking" ? "rgba(255, 215, 0, 0.65)"
      : "rgba(0, 255, 229, 0.45)",
    boxShadow:
      effectiveState === "analyzing" ? "0 0 60px rgba(255, 123, 0, 0.55), inset 0 0 40px rgba(255, 123, 0, 0.18)"
      : effectiveState === "speaking" ? "0 0 50px rgba(255, 215, 0, 0.45), inset 0 0 30px rgba(255, 215, 0, 0.12)"
      : "0 0 40px rgba(0, 255, 229, 0.3), inset 0 0 30px rgba(0, 255, 229, 0.08)",
  }

  return (
    <div className="vis" style={outerStyle}>
      <div className="bg-radial" style={{ background: `radial-gradient(circle at center, ${accentSoft}11 0%, transparent 60%)` }} />
      <span className="corner corner-tl" style={{ borderColor: accent }} />
      <span className="corner corner-tr" style={{ borderColor: accent }} />
      <span className="corner corner-bl" style={{ borderColor: accent }} />
      <span className="corner corner-br" style={{ borderColor: accent }} />

      <div className="header">
        <span className="brand" style={{ textShadow: `0 0 14px ${accent}` }}>▣ JARVIS</span>
        <span className={`state state-${effectiveState}`} style={{ color: accent, textShadow: `0 0 10px ${accent}` }}>
          ● {effectiveState.toUpperCase()}
        </span>
      </div>

      <div className="cloud-stage">
        <div className="cloud" style={{ animationDuration: effectiveState === "analyzing" ? "5s" : "16s" }}>
          <div
            className="core"
            style={{
              background: `radial-gradient(circle, ${accent}, ${accent}33 50%, transparent 78%)`,
              boxShadow: `0 0 ${30 + voiceScale * 12}px ${accent}, 0 0 ${50 + voiceScale * 20}px ${accent}88`,
              transform: `scale(${0.85 + voiceScale * 0.15})`,
            }}
          />
          {PARTICLES.map((p, i) => (
            <div
              key={i}
              className="particle"
              style={{
                transform: `rotateY(${p.theta}deg) rotateX(${p.phi}deg) translateZ(${p.r + voicePush}px)`,
                width: `${p.size * voiceScale}px`,
                height: `${p.size * voiceScale}px`,
                background: accent,
                boxShadow: `0 0 ${4 + voiceScale * 4}px ${accent}, 0 0 ${1 + voiceScale * 2}px ${accent}`,
                opacity: 0.6 + Math.min(0.4, rms * 4),
              }}
            />
          ))}
        </div>
        {message && effectiveState !== "idle" && (
          <div className="msg" style={{ color: accent }}>{message}</div>
        )}
      </div>

      <div className="mini">
        <div className="mini-row">
          <span className="mini-label">CPU</span>
          <Sparkline data={cpuHistory} color={cpu > 70 ? "#ff9500" : "#00ffe5"} />
          <span className="mini-val">{cpu.toFixed(0)}%</span>
        </div>
        <div className="mini-row">
          <span className="mini-label">MEM</span>
          <Sparkline data={memHistory} color={mem > 70 ? "#ff9500" : "#7fffd4"} />
          <span className="mini-val">{mem.toFixed(0)}%</span>
        </div>
        <div className="mini-row">
          <span className="mini-label">NET</span>
          <span className="mini-val flex"> ↓{fmtBytes(net_in)}/s · ↑{fmtBytes(net_out)}/s</span>
        </div>
        <div className="mini-row">
          <span className="mini-label">DISK</span>
          <span className="mini-val flex">{disk}% used</span>
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
  width: 340px;
  padding: 18px 20px 14px;
  perspective: 1600px;
  transform-style: preserve-3d;
  font-family: 'SF Mono', 'Menlo', 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #a0e8e0;
  background: #000000;
  border: 1px solid rgba(0, 255, 229, 0.45);
  border-radius: 12px;
  overflow: hidden;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  will-change: transform, box-shadow;
  transition: box-shadow 0.4s, border-color 0.4s;

  .bg-radial {
    position: absolute;
    inset: 0;
    pointer-events: none;
    border-radius: 12px;
    z-index: 0;
  }

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: repeating-linear-gradient(
      0deg,
      rgba(0, 255, 229, 0.04) 0px,
      rgba(0, 255, 229, 0.04) 1px,
      transparent 1px,
      transparent 4px
    );
    mix-blend-mode: screen;
    z-index: 1;
    border-radius: 12px;
  }

  .corner {
    position: absolute;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(0, 255, 229, 0.85);
    z-index: 3;
    transition: border-color 0.4s;
  }
  .corner-tl { top: 6px; left: 6px; border-right: 0; border-bottom: 0; }
  .corner-tr { top: 6px; right: 6px; border-left: 0; border-bottom: 0; }
  .corner-bl { bottom: 6px; left: 6px; border-right: 0; border-top: 0; }
  .corner-br { bottom: 6px; right: 6px; border-left: 0; border-top: 0; }

  .header {
    position: relative;
    z-index: 5;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    padding-bottom: 7px;
    border-bottom: 1px solid rgba(0, 255, 229, 0.18);
    font-size: 10px;
  }
  .brand {
    color: #ffffff;
    font-weight: bold;
    letter-spacing: 0.18em;
  }
  .state {
    font-size: 8px;
    letter-spacing: 0.12em;
    transition: color 0.3s;
  }
  .state-listening { animation: vis-blink 0.8s ease-in-out infinite; }
  .state-analyzing { animation: vis-blink 0.28s ease-in-out infinite; }

  .cloud-stage {
    position: relative;
    z-index: 4;
    height: 230px;
    display: flex;
    align-items: center;
    justify-content: center;
    perspective: 1000px;
    margin-bottom: 12px;
  }
  .cloud {
    position: relative;
    width: 0;
    height: 0;
    transform-style: preserve-3d;
    animation: cloud-spin linear infinite;
  }
  .core {
    position: absolute;
    width: 14px;
    height: 14px;
    margin-left: -7px;
    margin-top: -7px;
    border-radius: 50%;
    transition: box-shadow 0.18s, transform 0.18s, background 0.4s;
    z-index: 2;
  }
  .particle {
    position: absolute;
    top: 0;
    left: 0;
    margin-left: -1px;
    margin-top: -1px;
    border-radius: 50%;
    transition: width 0.16s, height 0.16s, box-shadow 0.16s, background 0.4s, opacity 0.16s, transform 0.18s;
  }
  .msg {
    position: absolute;
    bottom: 6px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 9px;
    letter-spacing: 0.12em;
    text-shadow: 0 0 8px currentColor;
    text-transform: uppercase;
    white-space: nowrap;
    max-width: 280px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .mini {
    position: relative;
    z-index: 5;
    padding: 6px 8px;
    background: rgba(0, 255, 229, 0.03);
    border: 1px solid rgba(0, 255, 229, 0.12);
    border-radius: 4px;
    margin-bottom: 8px;
  }
  .mini-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 9px;
    margin-bottom: 3px;
  }
  .mini-row:last-child { margin-bottom: 0; }
  .mini-label {
    color: #5fa9a0;
    width: 30px;
    flex-shrink: 0;
    letter-spacing: 0.12em;
  }
  .mini-val {
    color: #00ffe5;
    text-shadow: 0 0 4px rgba(0, 255, 229, 0.55);
    font-variant-numeric: tabular-nums;
    font-weight: bold;
    font-size: 9px;
    margin-left: auto;
  }
  .mini-val.flex { margin-left: 0; flex: 1; }
  .sparkline {
    flex: 1;
    height: 8px;
    opacity: 0.85;
  }

  .footer {
    position: relative;
    z-index: 5;
    display: flex;
    justify-content: space-between;
    color: #4a8a8a;
    font-size: 8px;
    letter-spacing: 0.18em;
  }

  @keyframes cloud-spin {
    from { transform: rotateY(0deg) rotateX(8deg); }
    to { transform: rotateY(360deg) rotateX(8deg); }
  }
  @keyframes vis-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
`
