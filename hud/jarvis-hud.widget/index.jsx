// JARVIS HUD v7 — Cinematic Floating Particle Visualizer
//
// Direct mic capture (Web Audio API) → 200 particles 3D field, neon cyan #00FFFF.
// Top-center 100% wide, 150px tall, fully transparent, edge-fade mask.
// 120 FPS RAF loop, GC-minimized (typed arrays, in-place mutation).
// State channel: ~/Library/Caches/jarvis-hud.json (color shift listening/analyzing/speaking).

let __jarvisInited = false
let __jarvisStateColor = "#00FFFF"
let __jarvisStateName = "idle"

// State polling — file:// fetch는 어려우므로 (Übersicht은 sandbox).
// 대신 module-level command 결과를 통해 (cat ~/Library/Caches/jarvis-hud.json) 받기.
// 1초 polling — Web Audio loop는 별개로 120FPS.

async function setupVisualizer(canvas) {
  const ctx = canvas.getContext("2d", { alpha: true })
  if (!ctx) return

  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const resize = () => {
    const rect = canvas.parentElement.getBoundingClientRect()
    const w = Math.max(220, rect.width)
    const h = Math.max(220, rect.height)
    canvas.width = w * dpr
    canvas.height = h * dpr
    canvas.style.width = w + "px"
    canvas.style.height = h + "px"
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }
  resize()
  window.addEventListener("resize", resize)

  // Particle field — pre-allocated typed arrays (no per-frame GC)
  const N = 220
  const px = new Float32Array(N)   // base X
  const py = new Float32Array(N)   // base Y
  const pz = new Float32Array(N)   // base Z (depth)
  const psize = new Float32Array(N)
  const ppx = new Float32Array(N)  // perturbation X (jitter accumulator)
  const ppy = new Float32Array(N)
  const ppz = new Float32Array(N)

  // 3D SPHERE distribution — particles on/near a sphere surface
  // theta: 0~2π, phi: -π/2~π/2  →  xyz on sphere of radius R + slight noise
  const R = 95
  for (let i = 0; i < N; i++) {
    const theta = Math.random() * 6.2832
    const phi = Math.acos(2 * Math.random() - 1) - Math.PI / 2  // uniform over sphere
    const r = R + (Math.random() - 0.5) * 12  // shell thickness
    px[i] = r * Math.cos(phi) * Math.cos(theta)
    py[i] = r * Math.sin(phi)
    pz[i] = r * Math.cos(phi) * Math.sin(theta)
    psize[i] = 1.3 + Math.random() * 1.5
  }

  // Audio analyser
  let analyser = null
  let freqData = null
  let timeData = null
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false }
    })
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    const audioCtx = new AudioCtx()
    const src = audioCtx.createMediaStreamSource(stream)
    analyser = audioCtx.createAnalyser()
    analyser.fftSize = 1024
    analyser.smoothingTimeConstant = 0.55
    src.connect(analyser)
    freqData = new Uint8Array(analyser.frequencyBinCount)
    timeData = new Uint8Array(analyser.fftSize)
  } catch (err) {
    console.warn("[jarvis] mic access denied or unavailable:", err && err.name)
  }

  // State channel polling (1 Hz)
  const updateStateColor = () => {
    const cmap = {
      idle: "#00FFFF",
      listening: "#00FFFF",
      analyzing: "#FF7B00",
      speaking: "#FFD700",
    }
    __jarvisStateColor = cmap[__jarvisStateName] || "#00FFFF"
  }

  // Animation state (smoothed)
  let smoothVol = 0
  let smoothBass = 0
  let smoothMid = 0
  let smoothTreble = 0
  let smoothPeak = 0
  let frame = 0
  let lastT = performance.now()

  const animate = (now) => {
    const dt = Math.min(0.05, (now - lastT) / 1000)
    lastT = now
    frame++

    // ── Audio analysis ─────────────────────────────────────────
    let vol = 0, bass = 0, mid = 0, treble = 0, peak = 0
    if (analyser && freqData) {
      analyser.getByteFrequencyData(freqData)
      const len = freqData.length
      const lowEnd = (len * 0.1) | 0
      const midEnd = (len * 0.4) | 0
      let sum = 0
      for (let i = 0; i < len; i++) {
        const v = freqData[i]
        sum += v
        if (i < lowEnd) bass += v
        else if (i < midEnd) mid += v
        else treble += v
        if (v > peak) peak = v
      }
      vol = sum / len / 255
      bass = bass / lowEnd / 255
      mid = mid / (midEnd - lowEnd) / 255
      treble = treble / (len - midEnd) / 255
      peak = peak / 255
    }

    // exponential smoothing for fluid motion
    const s = 0.18
    smoothVol += (vol - smoothVol) * s
    smoothBass += (bass - smoothBass) * s
    smoothMid += (mid - smoothMid) * s
    smoothTreble += (treble - smoothTreble) * s
    smoothPeak += (peak - smoothPeak) * 0.32

    // ── Clear (fully transparent) ──────────────────────────────
    ctx.clearRect(0, 0, canvas.width / dpr, canvas.height / dpr)

    const W = canvas.width / dpr
    const H = canvas.height / dpr
    const cx = W / 2
    const cy = H / 2

    // ── Idle 3D rotation ───────────────────────────────────────
    const t = frame * 0.0035
    const cosT = Math.cos(t)
    const sinT = Math.sin(t)
    const cosT2 = Math.cos(t * 0.5)
    const sinT2 = Math.sin(t * 0.5)

    // ── Update state color ─────────────────────────────────────
    updateStateColor()
    const baseColor = __jarvisStateColor

    // ── Voice-driven dynamics ──────────────────────────────────
    const explosion = smoothVol * 90      // outward Y push (vertical)
    const zPush = smoothBass * 70          // outward Z push
    const jitterAmt = Math.max(0, smoothVol - 0.04) * 14
    const sizeBoost = 1 + smoothPeak * 1.8
    const blurBoost = 12 + smoothPeak * 28

    // ── Sort by z (back to front) ──────────────────────────────
    // Allocate index array once per session would be ideal, but for clarity:
    if (!setupVisualizer._sortIdx || setupVisualizer._sortIdx.length !== N) {
      setupVisualizer._sortIdx = new Int32Array(N)
      for (let i = 0; i < N; i++) setupVisualizer._sortIdx[i] = i
    }
    const idx = setupVisualizer._sortIdx
    // Compute current Z for each particle, then sort idx
    const curZ = new Float32Array(N)  // small; could be hoisted further
    for (let i = 0; i < N; i++) {
      const x = px[i] + ppx[i]
      const z = pz[i] + ppz[i]
      curZ[i] = x * sinT + z * cosT
    }
    // simple insertion sort (N=220, near-sorted between frames — fast)
    for (let i = 1; i < N; i++) {
      const v = idx[i]
      const k = curZ[v]
      let j = i - 1
      while (j >= 0 && curZ[idx[j]] > k) {
        idx[j + 1] = idx[j]
        j--
      }
      idx[j + 1] = v
    }

    // ── Render ─────────────────────────────────────────────────
    ctx.shadowColor = baseColor
    ctx.fillStyle = baseColor

    for (let s_i = 0; s_i < N; s_i++) {
      const i = idx[s_i]

      // Decay perturbation
      ppx[i] *= 0.85
      ppy[i] *= 0.85
      ppz[i] *= 0.85

      // Add jitter on high volume
      if (jitterAmt > 0.5) {
        ppx[i] += (Math.random() - 0.5) * jitterAmt
        ppy[i] += (Math.random() - 0.5) * jitterAmt
        ppz[i] += (Math.random() - 0.5) * jitterAmt * 0.5
      }

      // Vertical voice push (away from center along Y)
      const ySign = py[i] >= 0 ? 1 : -1
      const verticalKick = ySign * explosion + smoothMid * 18 * Math.sin(frame * 0.08 + px[i] * 0.01)

      // Compute world position
      const wx = px[i] + ppx[i]
      const wy = py[i] + verticalKick + ppy[i]
      const wz = pz[i] + ppz[i] + (Math.abs(pz[i]) > 0 ? Math.sign(pz[i]) * zPush : 0)

      // Idle Y-axis rotation
      const rx = wx * cosT - wz * sinT
      const rz = wx * sinT + wz * cosT
      // light X-axis tilt for parallax
      const ry = wy * cosT2 - rz * 0.05 * sinT2

      // Perspective projection
      const fov = 320
      const sc = fov / (fov - rz)
      if (sc <= 0) continue
      const screenX = cx + rx * sc
      const screenY = cy + ry * sc

      // Skip off-screen (cull)
      if (screenX < -20 || screenX > W + 20 || screenY < -20 || screenY > H + 20) continue

      // Alpha based on depth + smooth peak
      const depthFade = Math.max(0.25, Math.min(1, sc * 0.6))
      const alpha = depthFade * (0.7 + smoothPeak * 0.3)

      // Bloom
      ctx.shadowBlur = blurBoost * sc
      ctx.globalAlpha = alpha
      ctx.beginPath()
      ctx.arc(screenX, screenY, psize[i] * sc * sizeBoost, 0, 6.2832)
      ctx.fill()
    }

    ctx.globalAlpha = 1
    ctx.shadowBlur = 0

    // ── Concentric pulse rings (voice burst) ──────────────────
    if (smoothPeak > 0.18) {
      const rings = 3
      for (let r = 0; r < rings; r++) {
        const phase = ((frame + r * 18) % 90) / 90
        const radius = 30 + phase * 250
        ctx.beginPath()
        ctx.arc(cx, cy, radius * (1 + smoothPeak * 0.4), 0, 6.2832)
        ctx.strokeStyle = baseColor
        ctx.globalAlpha = (1 - phase) * smoothPeak * 0.55
        ctx.lineWidth = 1.2
        ctx.shadowBlur = 12
        ctx.shadowColor = baseColor
        ctx.stroke()
      }
      ctx.globalAlpha = 1
      ctx.shadowBlur = 0
    }

    // ── Frequency spectrum bars (bottom strip, subtle) ─────────
    if (analyser && freqData) {
      const bars = 64
      const binsPerBar = (freqData.length / bars) | 0
      const barW = (W - 40) / bars
      const barBaseY = H - 8
      ctx.fillStyle = baseColor
      ctx.shadowBlur = 6
      ctx.shadowColor = baseColor
      for (let b = 0; b < bars; b++) {
        let m = 0
        for (let k = 0; k < binsPerBar; k++) {
          const v = freqData[b * binsPerBar + k]
          if (v > m) m = v
        }
        const h = (m / 255) * 28
        if (h < 1.5) continue
        ctx.globalAlpha = 0.45 + (m / 255) * 0.45
        ctx.fillRect(20 + b * barW, barBaseY - h, Math.max(1, barW - 1.5), h)
      }
      ctx.globalAlpha = 1
      ctx.shadowBlur = 0
    }

    requestAnimationFrame(animate)
  }
  requestAnimationFrame(animate)
}

const tryInit = () => {
  if (__jarvisInited) return
  const canvas = document.querySelector(".particle-canvas")
  if (canvas) {
    __jarvisInited = true
    setupVisualizer(canvas)
  }
}
const __initTimer = setInterval(tryInit, 100)
setTimeout(() => clearInterval(__initTimer), 8000)

// ── Übersicht widget contract ───────────────────────────────────
// command이 1초마다 hud-data.sh를 실행 → state 추출 → __jarvisStateName 갱신.
export const command = "cat ~/Library/Caches/jarvis-hud.json 2>/dev/null || echo '{}'"
export const refreshFrequency = 1000

export const render = ({ output }) => {
  try {
    const data = JSON.parse(output || "{}")
    if (data.state) __jarvisStateName = data.state
  } catch (e) {}
  return (
    <div className="vis-root">
      <canvas className="particle-canvas" />
    </div>
  )
}

// Top-center 3D sphere (260×260 원형 영역, 데스크톱 상단 중앙)
export const className = `
  position: fixed;
  top: 18px;
  left: 50%;
  transform: translateX(-50%);
  width: 260px;
  height: 260px;
  background: transparent !important;
  pointer-events: none;
  z-index: 999;

  .vis-root {
    position: relative;
    width: 100%;
    height: 100%;
    background: transparent;
    border-radius: 50%;
    -webkit-mask-image: radial-gradient(circle at center, black 55%, rgba(0,0,0,0.6) 75%, transparent 100%);
    mask-image: radial-gradient(circle at center, black 55%, rgba(0,0,0,0.6) 75%, transparent 100%);
  }

  .particle-canvas {
    display: block;
    width: 100%;
    height: 100%;
    background: transparent;
    border-radius: 50%;
  }
`
