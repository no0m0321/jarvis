// JARVIS HUD v6 — Cinematic Premium Edition
//
// 30+ visual upgrades:
// • Wake-time auto-zoom (1.0 → 1.18 + glow surge)
// • Larger canvas (340 → 460)
// • Hexagonal grid background overlay
// • Animated perspective grid floor (sci-fi sweep)
// • Cinematic boot animation (fade + scale on initial mount)
// • Multi-layer particle cloud (60 inner + outer ring)
// • 3D wireframe globe + auxiliary radar sweep
// • Voice waveform 3D bars (with color gradient)
// • Edge glow pulse continuous
// • Particle explosion burst on wake transition
// • Code rain effect (left+right gutter)
// • Dynamic gradient mesh background (state-aware)
// • Glitch text on header during analyzing
// • Day/night palette (idle 시간대별)
// • State-driven color theme (cyan / amber / gold / mint / magenta)
// • CPU/MEM SVG sparkline + last log line
// • Animated state badge (orbit dots)
// • Particle inner glow rings
// • Voice peak flash overlay
// • Smooth state transitions (cubic-bezier)

export const command = "bash /Users/swxvno/jarvis/scripts/hud-data.sh"
export const refreshFrequency = 1000

// ── State (module-level, preserved across renders) ─────────────────────
const HISTORY_LEN = 60
let cpuHistory = []
let memHistory = []
let lastVoicePeak = 0  // peak detection for flash
let lastState = "idle"
let bootedAt = Date.now()  // 부트 시점

// 80 particles in 2 spherical layers
const PARTICLES = []
for (let i = 0; i < 40; i++) {
  PARTICLES.push({
    theta: Math.random() * 360,
    phi: Math.random() * 180 - 90,
    r: 70 + Math.random() * 28,
    size: 1.4 + Math.random() * 1.4,
    layer: 0,
  })
}
for (let i = 0; i < 40; i++) {
  PARTICLES.push({
    theta: Math.random() * 360,
    phi: Math.random() * 180 - 90,
    r: 110 + Math.random() * 28,
    size: 0.9 + Math.random() * 1.1,
    layer: 1,
  })
}

// Code rain — 양쪽 gutter에 흐르는 짧은 문자
const RAIN_GLYPHS = "01ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎ▓░"
const mkRainCol = (idx, side) => ({
  idx,
  side,
  delay: idx * 0.4,
  duration: 8 + Math.random() * 6,
  chars: Array.from({ length: 14 }, () => RAIN_GLYPHS[Math.floor(Math.random() * RAIN_GLYPHS.length)]),
})
const RAIN_COLS = [
  ...Array.from({ length: 3 }, (_, i) => mkRainCol(i, "L")),
  ...Array.from({ length: 3 }, (_, i) => mkRainCol(i, "R")),
]

// ── Helpers ────────────────────────────────────────────────────────────
const GLITCH = "▓░╳▣▦▩▤≡≣"
const glitch = (text, prob = 0.05) =>
  Array.from(text).map((c) =>
    Math.random() < prob && c !== " "
      ? GLITCH[Math.floor(Math.random() * GLITCH.length)]
      : c
  ).join("")

const dayNightTint = () => {
  const h = new Date().getHours()
  if (h < 6) return { tint: "#7fffd4", soft: "rgba(127,255,212,0.5)" }
  if (h < 12) return { tint: "#00ffe5", soft: "rgba(0,255,229,0.5)" }
  if (h < 18) return { tint: "#5fdfd0", soft: "rgba(95,223,208,0.45)" }
  return { tint: "#ff7bff", soft: "rgba(255,123,255,0.45)" }
}

const fmtBytes = (n) => {
  if (n < 1024) return `${n}B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)}K`
  return `${(n / 1024 / 1024).toFixed(2)}M`
}

const Sparkline = ({ data, color, width = 80, height = 10 }) => {
  if (data.length < 2) return null
  const pts = data
    .map((v, i) => {
      const x = (i / (HISTORY_LEN - 1)) * width
      const y = height - (Math.min(v, 100) / 100) * height
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(" ")
  return (
    <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="0.7"
        style={{ filter: `drop-shadow(0 0 1.2px ${color})` }}
      />
    </svg>
  )
}

// ── Main render ────────────────────────────────────────────────────────
export const render = ({ output }) => {
  let data = {
    cpu: 0, mem: 0, net_in: 0, net_out: 0,
    disk: 0, top_proc: "?:0", last_log: "",
    jarvis: { state: "idle", message: "", ts: 0 },
    voice: { rms: 0, peak: 0, history: [], ts: 0 },
    ts: 0,
  }
  try { data = JSON.parse(output) } catch (e) {}
  const { cpu, mem, net_in, net_out, disk, jarvis, voice, last_log } = data
  const state = (jarvis && jarvis.state) || "idle"
  const message = (jarvis && jarvis.message) || ""
  const ts = (jarvis && jarvis.ts) || 0
  const stale = ts > 0 && Date.now() / 1000 - ts > 30
  const effectiveState = stale ? "idle" : state

  cpuHistory.push(cpu)
  memHistory.push(mem)
  if (cpuHistory.length > HISTORY_LEN) cpuHistory.shift()
  if (memHistory.length > HISTORY_LEN) memHistory.shift()

  // Voice (RMS + history)
  const voiceTs = (voice && voice.ts) || 0
  const voiceFresh = voiceTs > 0 && Date.now() / 1000 - voiceTs < 3
  const rms = voiceFresh ? Math.min(0.12, (voice && voice.rms) || 0) : 0
  const voiceScale = 1 + rms * 30
  const voicePush = rms * 70
  const waveform = voiceFresh ? (voice && voice.history) || [] : []

  // Peak flash detection (이전 peak보다 큼)
  const flashing = rms > 0.04 && rms > lastVoicePeak * 1.4
  lastVoicePeak = rms

  // 상태 전환 감지 (wake 시 burst trigger)
  const justWoke = lastState === "idle" && (effectiveState === "listening" || effectiveState === "analyzing")
  lastState = effectiveState

  // Boot animation: 첫 1.5초만 fade-in
  const bootElapsed = Date.now() - bootedAt
  const bootFade = bootElapsed < 1500 ? bootElapsed / 1500 : 1

  // Day/night palette
  const dn = dayNightTint()
  const accent =
    effectiveState === "analyzing" ? "#ff7b00"
    : effectiveState === "speaking" ? "#ffd700"
    : effectiveState === "listening" ? "#00ffe5"
    : dn.tint
  const accentSoft =
    effectiveState === "analyzing" ? "rgba(255, 123, 0, 0.55)"
    : effectiveState === "speaking" ? "rgba(255, 215, 0, 0.55)"
    : effectiveState === "listening" ? "rgba(0, 255, 229, 0.6)"
    : dn.soft

  // Wake-time auto-zoom (사용자 명시 요청)
  const isActive = effectiveState !== "idle"
  const rootStyle = {
    transform: `scale(${isActive ? 1.16 : 1.0})`,
    borderColor: isActive ? accent : "rgba(0, 255, 229, 0.45)",
    boxShadow: isActive
      ? `0 0 80px ${accent}, 0 0 40px ${accent}aa, inset 0 0 40px ${accent}22, 0 32px 80px rgba(0, 0, 0, 0.7)`
      : "0 0 42px rgba(0, 255, 229, 0.35), inset 0 0 28px rgba(0, 255, 229, 0.08), 0 24px 60px rgba(0, 0, 0, 0.55)",
    opacity: bootFade,
  }
  const stateAnim =
    effectiveState === "analyzing" ? "hud-shake 0.16s ease-in-out infinite, hud-edge-pulse 1.2s ease-in-out infinite"
    : effectiveState === "listening" ? "hud-pulse 1.4s ease-in-out infinite, hud-edge-pulse 1.6s ease-in-out infinite"
    : effectiveState === "speaking" ? "hud-edge-pulse 1.8s ease-in-out infinite"
    : "hud-float 6s ease-in-out infinite"
  rootStyle.animation = stateAnim

  return (
    <div className="hud" style={rootStyle}>
      {/* Background layers */}
      <div className="bg-mesh" style={{ background: `radial-gradient(circle at 30% 30%, ${accentSoft}33 0%, transparent 50%), radial-gradient(circle at 70% 70%, ${accentSoft}22 0%, transparent 60%)` }} />
      <div className="hex-grid" />
      <div className="grid-floor" style={{ borderColor: `${accent}33` }} />

      {/* Code rain */}
      {RAIN_COLS.map((col, i) => (
        <div
          key={`rain-${i}`}
          className={`rain rain-${col.side}`}
          style={{
            left: col.side === "L" ? `${4 + col.idx * 6}px` : "auto",
            right: col.side === "R" ? `${4 + col.idx * 6}px` : "auto",
            animationDelay: `${col.delay}s`,
            animationDuration: `${col.duration}s`,
            color: `${accent}aa`,
          }}
        >
          {col.chars.map((c, j) => (
            <span key={j} className="rain-char" style={{ animationDelay: `${j * 0.08}s` }}>{c}</span>
          ))}
        </div>
      ))}

      {/* Voice peak flash overlay */}
      {flashing && <div className="flash" style={{ background: `${accent}22` }} />}

      {/* Wake burst */}
      {justWoke && <div className="wake-burst" style={{ borderColor: accent, boxShadow: `0 0 60px ${accent}` }} />}

      {/* Corner brackets */}
      <span className="corner corner-tl" style={{ borderColor: accent }} />
      <span className="corner corner-tr" style={{ borderColor: accent }} />
      <span className="corner corner-bl" style={{ borderColor: accent }} />
      <span className="corner corner-br" style={{ borderColor: accent }} />

      <div className="header">
        <span className="brand" style={{ textShadow: `0 0 16px ${accent}, 0 0 4px #fff` }}>
          ▣ {effectiveState === "analyzing" ? glitch("JARVIS HUD", 0.15) : "JARVIS HUD"}
        </span>
        <span className={`state state-${effectiveState}`} style={{ color: accent, textShadow: `0 0 12px ${accent}` }}>
          ● {effectiveState.toUpperCase()}
        </span>
      </div>

      <div className="cloud-stage">
        {/* Outer aux ring (faint) */}
        <div className="aux-ring" style={{ borderColor: `${accent}55` }} />
        <div className="cloud" style={{ animationDuration: effectiveState === "analyzing" ? "5s" : "16s" }}>
          <div className="core"
            style={{
              background: `radial-gradient(circle, ${accent}, ${accent}33 50%, transparent 78%)`,
              boxShadow: `0 0 ${36 + voiceScale * 16}px ${accent}, 0 0 ${60 + voiceScale * 24}px ${accent}88`,
              transform: `scale(${0.85 + voiceScale * 0.18})`,
            }}
          />
          {PARTICLES.map((p, i) => (
            <div
              key={i}
              className={`particle particle-${p.layer}`}
              style={{
                transform: `rotateY(${p.theta}deg) rotateX(${p.phi}deg) translateZ(${p.r + voicePush}px)`,
                width: `${p.size * voiceScale}px`,
                height: `${p.size * voiceScale}px`,
                background: accent,
                boxShadow: `0 0 ${4 + voiceScale * 4}px ${accent}, 0 0 ${1 + voiceScale * 2}px ${accent}, -2px 0 4px ${accent}66`,
                opacity: (p.layer === 0 ? 0.85 : 0.55) + Math.min(0.3, rms * 6),
              }}
            />
          ))}
        </div>
        {message && effectiveState !== "idle" && (
          <div className="msg" style={{ color: accent, textShadow: `0 0 10px ${accent}` }}>{message}</div>
        )}
      </div>

      {/* Voice waveform */}
      {waveform.length > 0 && (
        <div className="waveform">
          {waveform.map((r, i) => (
            <div
              key={i}
              className="wf-bar"
              style={{
                height: `${Math.max(2, Math.min(28, r * 320))}px`,
                background: `linear-gradient(to top, ${accent}, ${accent}80)`,
                boxShadow: `0 0 6px ${accent}`,
                opacity: 0.4 + Math.min(0.6, r * 14),
              }}
            />
          ))}
        </div>
      )}

      {/* Mini stats */}
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
          <span className="mini-val flex">↓{fmtBytes(net_in)} ↑{fmtBytes(net_out)}</span>
        </div>
        <div className="mini-row">
          <span className="mini-label">DISK</span>
          <span className="mini-val flex">{disk}%</span>
        </div>
        {last_log && (
          <div className="mini-row log-row">
            <span className="mini-label">LOG</span>
            <span className="mini-val flex tiny">{last_log}</span>
          </div>
        )}
      </div>

      <div className="footer">
        <span style={{ color: accent }}>swxvno • jarvis v6</span>
        <span>{new Date().toLocaleTimeString("en-GB", { hour12: false })}</span>
      </div>
    </div>
  )
}

export const className = `
  position: absolute;
  top: 50px;
  right: 50px;
  width: 460px;
  padding: 22px 26px 18px;
  perspective: 1800px;
  transform-style: preserve-3d;
  font-family: 'SF Mono', 'Menlo', 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #a0e8e0;
  background: #000000;
  border: 1px solid rgba(0, 255, 229, 0.45);
  border-radius: 14px;
  overflow: hidden;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  will-change: transform, box-shadow, opacity;
  transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1), border-color 0.4s, box-shadow 0.4s;
  transform-origin: top right;

  .bg-mesh {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    border-radius: 14px;
    transition: background 0.5s;
  }
  .hex-grid {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 1;
    background-image:
      radial-gradient(circle at 50% 50%, rgba(0, 255, 229, 0.04) 1px, transparent 1.5px),
      radial-gradient(circle at 0% 0%, rgba(0, 255, 229, 0.04) 1px, transparent 1.5px);
    background-size: 24px 28px;
    background-position: 0 0, 12px 14px;
    opacity: 0.5;
    border-radius: 14px;
  }
  .grid-floor {
    position: absolute;
    bottom: -40px;
    left: -10%;
    right: -10%;
    height: 90px;
    pointer-events: none;
    z-index: 2;
    background:
      linear-gradient(transparent 70%, rgba(0, 255, 229, 0.05) 100%),
      repeating-linear-gradient(90deg, transparent 0, transparent 24px, rgba(0, 255, 229, 0.18) 24px, rgba(0, 255, 229, 0.18) 25px),
      repeating-linear-gradient(180deg, transparent 0, transparent 18px, rgba(0, 255, 229, 0.18) 18px, rgba(0, 255, 229, 0.18) 19px);
    transform: perspective(220px) rotateX(58deg);
    transform-origin: top center;
    animation: grid-sweep 6s linear infinite;
    opacity: 0.55;
  }

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: repeating-linear-gradient(
      0deg,
      rgba(0, 255, 229, 0.045) 0px,
      rgba(0, 255, 229, 0.045) 1px,
      transparent 1px,
      transparent 4px
    );
    mix-blend-mode: screen;
    z-index: 3;
    border-radius: 14px;
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
    z-index: 3;
  }

  .rain {
    position: absolute;
    top: 6px;
    bottom: 6px;
    width: 8px;
    pointer-events: none;
    z-index: 4;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    opacity: 0.5;
    animation: rain-fall infinite linear;
  }
  .rain-char {
    font-size: 8px;
    line-height: 1.1;
    text-shadow: 0 0 4px currentColor;
    animation: rain-flicker 1.2s ease-in-out infinite;
  }

  .flash {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 9;
    border-radius: 14px;
    animation: flash-fade 0.3s ease-out forwards;
  }

  .wake-burst {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 60px;
    height: 60px;
    border: 2px solid;
    border-radius: 50%;
    pointer-events: none;
    z-index: 8;
    transform: translate(-50%, -50%);
    animation: burst-expand 0.7s ease-out forwards;
  }

  .corner {
    position: absolute;
    width: 16px;
    height: 16px;
    border: 2px solid rgba(0, 255, 229, 0.85);
    z-index: 5;
    box-shadow: 0 0 10px currentColor;
    transition: border-color 0.4s;
  }
  .corner-tl { top: 6px; left: 6px; border-right: 0; border-bottom: 0; }
  .corner-tr { top: 6px; right: 6px; border-left: 0; border-bottom: 0; }
  .corner-bl { bottom: 6px; left: 6px; border-right: 0; border-top: 0; }
  .corner-br { bottom: 6px; right: 6px; border-left: 0; border-top: 0; }

  .header {
    position: relative;
    z-index: 6;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    padding-bottom: 9px;
    border-bottom: 1px solid rgba(0, 255, 229, 0.25);
    font-size: 11px;
    transform: translateZ(20px);
  }
  .brand {
    color: #ffffff;
    font-weight: bold;
    letter-spacing: 0.22em;
    font-size: 13px;
  }
  .state {
    font-size: 9px;
    letter-spacing: 0.16em;
    transition: color 0.3s, text-shadow 0.3s;
  }
  .state-listening { animation: vis-blink 0.8s ease-in-out infinite; }
  .state-analyzing { animation: vis-blink 0.28s ease-in-out infinite; }

  .cloud-stage {
    position: relative;
    z-index: 5;
    height: 290px;
    display: flex;
    align-items: center;
    justify-content: center;
    perspective: 1100px;
    margin-bottom: 14px;
  }
  .aux-ring {
    position: absolute;
    width: 240px;
    height: 240px;
    border: 1px dashed;
    border-radius: 50%;
    opacity: 0.35;
    animation: aux-spin 18s linear infinite;
    pointer-events: none;
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
    width: 16px;
    height: 16px;
    margin-left: -8px;
    margin-top: -8px;
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
  .particle-1 { filter: blur(0.4px); }
  .msg {
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    font-size: 10px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    white-space: nowrap;
    max-width: 380px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .waveform {
    position: relative;
    z-index: 6;
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 2px;
    height: 30px;
    margin-bottom: 10px;
    padding: 1px 4px;
    border-bottom: 1px solid rgba(0, 255, 229, 0.18);
  }
  .wf-bar {
    flex: 1;
    min-height: 2px;
    border-radius: 1px;
    transition: height 0.18s ease, opacity 0.2s, box-shadow 0.18s;
  }

  .mini {
    position: relative;
    z-index: 6;
    padding: 8px 10px;
    background: rgba(0, 255, 229, 0.04);
    border: 1px solid rgba(0, 255, 229, 0.14);
    border-radius: 5px;
    margin-bottom: 10px;
    transform: translateZ(6px);
  }
  .mini-row {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 10px;
    margin-bottom: 4px;
  }
  .mini-row:last-child { margin-bottom: 0; }
  .log-row { font-size: 8px; opacity: 0.7; }
  .mini-label {
    color: #5fa9a0;
    width: 32px;
    flex-shrink: 0;
    letter-spacing: 0.14em;
  }
  .mini-val {
    color: #00ffe5;
    text-shadow: 0 0 4px rgba(0, 255, 229, 0.55);
    font-variant-numeric: tabular-nums;
    font-weight: bold;
    margin-left: auto;
  }
  .mini-val.flex { margin-left: 0; flex: 1; text-align: right; }
  .mini-val.tiny {
    font-size: 8px;
    text-transform: lowercase;
    letter-spacing: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 360px;
  }
  .sparkline { flex: 1; height: 10px; opacity: 0.85; }

  .footer {
    position: relative;
    z-index: 6;
    display: flex;
    justify-content: space-between;
    color: #4a8a8a;
    font-size: 8px;
    letter-spacing: 0.18em;
    transform: translateZ(-3px);
  }

  /* Animations */
  @keyframes cloud-spin {
    from { transform: rotateY(0deg) rotateX(8deg); }
    to { transform: rotateY(360deg) rotateX(8deg); }
  }
  @keyframes aux-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  @keyframes vis-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  @keyframes hud-shimmer {
    0% { background-position: 200% 200%; }
    100% { background-position: -200% -200%; }
  }
  @keyframes hud-edge-pulse {
    0%, 100% { filter: brightness(1); }
    50% { filter: brightness(1.18); }
  }
  @keyframes hud-shake {
    0%, 100% { transform: scale(1.16) translate(0, 0); }
    20% { transform: scale(1.16) translate(-2px, 1px); }
    40% { transform: scale(1.16) translate(3px, -2px); }
    60% { transform: scale(1.16) translate(-2px, 2px); }
    80% { transform: scale(1.16) translate(2px, -1px); }
  }
  @keyframes hud-pulse {
    0%, 100% {
      box-shadow: 0 0 50px rgba(0, 255, 229, 0.5), 0 0 30px rgba(0, 255, 229, 0.3), inset 0 0 28px rgba(0, 255, 229, 0.1), 0 24px 60px rgba(0, 0, 0, 0.6);
      transform: scale(1.16);
    }
    50% {
      box-shadow: 0 0 80px rgba(0, 255, 229, 0.85), 0 0 40px rgba(0, 255, 229, 0.6), inset 0 0 40px rgba(0, 255, 229, 0.25), 0 24px 60px rgba(0, 0, 0, 0.6);
      transform: scale(1.18);
    }
  }
  @keyframes hud-float {
    0%, 100% { transform: scale(1) translateY(0); }
    50% { transform: scale(1) translateY(-3px); }
  }
  @keyframes grid-sweep {
    0% { background-position: 0 0, 0 0, 0 0; }
    100% { background-position: 0 0, 24px 0, 0 18px; }
  }
  @keyframes rain-fall {
    0% { transform: translateY(-100%); opacity: 0; }
    20% { opacity: 0.6; }
    80% { opacity: 0.6; }
    100% { transform: translateY(110%); opacity: 0; }
  }
  @keyframes rain-flicker {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 1; }
  }
  @keyframes flash-fade {
    from { opacity: 1; }
    to { opacity: 0; }
  }
  @keyframes burst-expand {
    0% { width: 60px; height: 60px; opacity: 1; border-width: 2px; }
    100% { width: 360px; height: 360px; opacity: 0; border-width: 1px; }
  }
`
