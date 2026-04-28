import AppKit
import AVFoundation
import WebKit

// MARK: - Embedded Visualizer (single-file deploy — no external resources)

let visualizerJS = #"""
window.__jarvisStateName = "idle"

;(async function () {
  const canvas = document.getElementById("c")
  const ctx = canvas.getContext("2d", { alpha: true })
  if (!ctx) return

  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const resize = () => {
    const w = window.innerWidth
    const h = window.innerHeight
    canvas.width = w * dpr
    canvas.height = h * dpr
    canvas.style.width = w + "px"
    canvas.style.height = h + "px"
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }
  resize()
  window.addEventListener("resize", resize)

  // 3D SPHERE distribution — particles on/near a sphere surface
  const N = 220
  const px = new Float32Array(N), py = new Float32Array(N), pz = new Float32Array(N)
  const psize = new Float32Array(N)
  const ppx = new Float32Array(N), ppy = new Float32Array(N), ppz = new Float32Array(N)
  const R = 95
  for (let i = 0; i < N; i++) {
    const theta = Math.random() * 6.2832
    const phi = Math.acos(2 * Math.random() - 1) - Math.PI / 2
    const r = R + (Math.random() - 0.5) * 12
    px[i] = r * Math.cos(phi) * Math.cos(theta)
    py[i] = r * Math.sin(phi)
    pz[i] = r * Math.cos(phi) * Math.sin(theta)
    psize[i] = 1.3 + Math.random() * 1.5
  }

  // Audio
  let analyser = null, freqData = null
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
  } catch (err) {
    console.warn("[jarvis] mic access denied:", err && err.name)
  }

  let smoothVol = 0, smoothBass = 0, smoothMid = 0, smoothPeak = 0
  let frame = 0
  const idx = new Int32Array(N)
  for (let i = 0; i < N; i++) idx[i] = i
  const curZ = new Float32Array(N)

  const animate = () => {
    frame++

    let vol = 0, bass = 0, mid = 0, peak = 0
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
        if (v > peak) peak = v
      }
      vol = sum / len / 255
      bass = bass / lowEnd / 255
      mid = mid / (midEnd - lowEnd) / 255
      peak = peak / 255
    }

    const s = 0.18
    smoothVol += (vol - smoothVol) * s
    smoothBass += (bass - smoothBass) * s
    smoothMid += (mid - smoothMid) * s
    smoothPeak += (peak - smoothPeak) * 0.32

    const W = canvas.width / dpr
    const H = canvas.height / dpr
    const cx = W / 2
    const cy = H / 2

    ctx.clearRect(0, 0, W, H)

    const t = frame * 0.0035
    const cosT = Math.cos(t), sinT = Math.sin(t)
    const cosT2 = Math.cos(t * 0.5), sinT2 = Math.sin(t * 0.5)

    const cmap = { idle: "#00FFFF", listening: "#00FFFF", analyzing: "#FF7B00", speaking: "#FFD700" }
    const baseColor = cmap[window.__jarvisStateName || "idle"] || "#00FFFF"

    const explosion = smoothVol * 90
    const zPush = smoothBass * 70
    const jitterAmt = Math.max(0, smoothVol - 0.04) * 14
    const sizeBoost = 1 + smoothPeak * 1.8
    const blurBoost = 12 + smoothPeak * 28

    for (let i = 0; i < N; i++) {
      const x = px[i] + ppx[i]
      const z = pz[i] + ppz[i]
      curZ[i] = x * sinT + z * cosT
    }
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

    ctx.shadowColor = baseColor
    ctx.fillStyle = baseColor

    for (let s_i = 0; s_i < N; s_i++) {
      const i = idx[s_i]
      ppx[i] *= 0.85
      ppy[i] *= 0.85
      ppz[i] *= 0.85

      if (jitterAmt > 0.5) {
        ppx[i] += (Math.random() - 0.5) * jitterAmt
        ppy[i] += (Math.random() - 0.5) * jitterAmt
        ppz[i] += (Math.random() - 0.5) * jitterAmt * 0.5
      }

      const ySign = py[i] >= 0 ? 1 : -1
      const verticalKick = ySign * explosion + smoothMid * 18 * Math.sin(frame * 0.08 + px[i] * 0.01)

      const wx = px[i] + ppx[i]
      const wy = py[i] + verticalKick + ppy[i]
      const wz = pz[i] + ppz[i] + (Math.abs(pz[i]) > 0 ? Math.sign(pz[i]) * zPush : 0)

      const rx = wx * cosT - wz * sinT
      const rz = wx * sinT + wz * cosT
      const ry = wy * cosT2 - rz * 0.05 * sinT2

      const fov = 320
      const sc = fov / (fov - rz)
      if (sc <= 0) continue
      const screenX = cx + rx * sc
      const screenY = cy + ry * sc

      if (screenX < -20 || screenX > W + 20 || screenY < -20 || screenY > H + 20) continue

      const depthFade = Math.max(0.25, Math.min(1, sc * 0.6))
      const alpha = depthFade * (0.7 + smoothPeak * 0.3)

      ctx.shadowBlur = blurBoost * sc
      ctx.globalAlpha = alpha
      ctx.beginPath()
      ctx.arc(screenX, screenY, psize[i] * sc * sizeBoost, 0, 6.2832)
      ctx.fill()
    }

    ctx.globalAlpha = 1
    ctx.shadowBlur = 0

    if (smoothPeak > 0.18) {
      const rings = 3
      for (let r = 0; r < rings; r++) {
        const phase = ((frame + r * 18) % 90) / 90
        const radius = 30 + phase * 100
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

    requestAnimationFrame(animate)
  }
  requestAnimationFrame(animate)
})()
"""#

let htmlPayload = """
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  html, body { margin: 0; padding: 0; background: transparent; overflow: hidden; }
  canvas {
    display: block;
    width: 100%;
    height: 100%;
    background: transparent;
    border-radius: 50%;
    -webkit-mask-image: radial-gradient(circle at center, black 60%, rgba(0,0,0,0.6) 78%, transparent 100%);
    mask-image: radial-gradient(circle at center, black 60%, rgba(0,0,0,0.6) 78%, transparent 100%);
  }
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
\(visualizerJS)
</script>
</body></html>
"""

// MARK: - App Delegate

class JarvisOverlayApp: NSObject, NSApplicationDelegate, WKUIDelegate {
    var panel: NSPanel!
    var webView: WKWebView!
    var statusItem: NSStatusItem!
    var stateTimer: Timer?
    var lastStateContent: String = ""
    let panelSize: CGFloat = 260

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        requestMicPermission()
        setupPanel()
        setupStatusItem()
        watchStateFile()
        observeScreenChange()
    }

    func requestMicPermission() {
        AVCaptureDevice.requestAccess(for: .audio) { granted in
            if !granted {
                DispatchQueue.main.async {
                    let alert = NSAlert()
                    alert.messageText = "마이크 권한 필요"
                    alert.informativeText = "시스템 환경설정 → 개인정보 보호 → 마이크에서 JarvisHUD를 허용한 뒤 앱을 재시작하시오."
                    alert.runModal()
                }
            }
        }
    }

    func computeFrame() -> NSRect {
        guard let screen = NSScreen.main else {
            return NSRect(x: 0, y: 0, width: panelSize, height: panelSize)
        }
        let x = screen.frame.origin.x + (screen.frame.width - panelSize) / 2
        let y = screen.frame.maxY - panelSize - 24
        return NSRect(x: x, y: y, width: panelSize, height: panelSize)
    }

    func setupPanel() {
        let frame = computeFrame()
        panel = NSPanel(
            contentRect: frame,
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        panel.level = .floating
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = false
        panel.ignoresMouseEvents = true
        panel.collectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle]
        panel.isMovableByWindowBackground = false
        panel.isFloatingPanel = true
        panel.hidesOnDeactivate = false

        let config = WKWebViewConfiguration()
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")
        config.mediaTypesRequiringUserActionForPlayback = []
        if #available(macOS 11.0, *) {
            config.defaultWebpagePreferences.allowsContentJavaScript = true
        }

        webView = WKWebView(frame: panel.contentView!.bounds, configuration: config)
        webView.autoresizingMask = [.width, .height]
        webView.setValue(false, forKey: "drawsBackground")
        webView.uiDelegate = self
        webView.loadHTMLString(htmlPayload, baseURL: URL(string: "https://localhost/jarvis"))

        panel.contentView?.addSubview(webView)
        panel.orderFrontRegardless()
    }

    func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let button = statusItem.button {
            button.title = "◈"
            button.toolTip = "Jarvis HUD"
        }
        let menu = NSMenu()
        let toggleItem = NSMenuItem(title: "보이기/숨기기", action: #selector(toggleVisibility), keyEquivalent: "h")
        toggleItem.target = self
        let reposItem = NSMenuItem(title: "위치 재설정", action: #selector(reposition), keyEquivalent: "r")
        reposItem.target = self
        let levelItem = NSMenuItem(title: "최상위 레벨 토글 (floating ↔ statusBar)", action: #selector(toggleLevel), keyEquivalent: "")
        levelItem.target = self
        let quitItem = NSMenuItem(title: "종료", action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(toggleItem)
        menu.addItem(.separator())
        menu.addItem(reposItem)
        menu.addItem(levelItem)
        menu.addItem(.separator())
        menu.addItem(quitItem)
        statusItem.menu = menu
    }

    @objc func toggleVisibility() {
        if panel.isVisible {
            panel.orderOut(nil)
        } else {
            panel.orderFrontRegardless()
        }
    }

    @objc func reposition() {
        panel.setFrame(computeFrame(), display: true)
        panel.orderFrontRegardless()
    }

    @objc func toggleLevel() {
        if panel.level == .floating {
            panel.level = .statusBar  // above fullscreen apps
        } else {
            panel.level = .floating
        }
    }

    @objc func quit() {
        NSApp.terminate(nil)
    }

    func observeScreenChange() {
        NotificationCenter.default.addObserver(
            forName: NSApplication.didChangeScreenParametersNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in self?.reposition() }
    }

    func watchStateFile() {
        let url = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Caches/jarvis-hud.json")
        stateTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            guard let content = try? String(contentsOf: url, encoding: .utf8) else { return }
            if content == self.lastStateContent { return }
            self.lastStateContent = content
            guard let data = content.data(using: .utf8),
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let state = json["state"] as? String else { return }
            let escaped = state.replacingOccurrences(of: "'", with: "\\'")
            self.webView.evaluateJavaScript("window.__jarvisStateName = '\(escaped)'", completionHandler: nil)
        }
    }

    // MARK: WKUIDelegate — microphone permission grant
    func webView(_ webView: WKWebView,
                 requestMediaCapturePermissionFor origin: WKSecurityOrigin,
                 initiatedByFrame frame: WKFrameInfo,
                 type: WKMediaCaptureType,
                 decisionHandler: @escaping (WKPermissionDecision) -> Void) {
        decisionHandler(.grant)
    }
}

// MARK: - Entry point
let app = NSApplication.shared
let delegate = JarvisOverlayApp()
app.delegate = delegate
NSApp.run()
