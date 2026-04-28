import AppKit
import AVFoundation
import WebKit

// MARK: - Embedded Visualizer (single-file deploy)

let visualizerJS = #"""
window.__jarvisStateName = "idle"
window.__jarvisExpanded = false  // collapsed 시 작은 mint 반원, expanded 시 sphere

;(async function () {
  const canvas = document.getElementById("c")
  const ctx = canvas.getContext("2d", { alpha: true })
  if (!ctx) return

  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const resize = () => {
    canvas.width = window.innerWidth * dpr
    canvas.height = window.innerHeight * dpr
    canvas.style.width = window.innerWidth + "px"
    canvas.style.height = window.innerHeight + "px"
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }
  resize()
  window.addEventListener("resize", resize)

  // 3D SPHERE particles
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

  // Audio (suspend/resume by hover)
  let analyser = null, freqData = null, audioCtx = null
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false }
    })
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    audioCtx = new AudioCtx()
    const src = audioCtx.createMediaStreamSource(stream)
    analyser = audioCtx.createAnalyser()
    analyser.fftSize = 1024
    analyser.smoothingTimeConstant = 0.55
    src.connect(analyser)
    freqData = new Uint8Array(analyser.frequencyBinCount)
  } catch (err) { console.warn("[jarvis] mic:", err && err.name) }

  let smoothVol = 0, smoothBass = 0, smoothMid = 0, smoothPeak = 0
  let expansion = 0  // 0 = collapsed, 1 = expanded (smooth interp)
  let frame = 0
  const idx = new Int32Array(N)
  for (let i = 0; i < N; i++) idx[i] = i
  const curZ = new Float32Array(N)

  const animate = () => {
    frame++

    // Expansion easing
    const target = window.__jarvisExpanded ? 1 : 0
    expansion += (target - expansion) * 0.12

    // Audio analyse — only when expanded (mic suspended otherwise)
    let vol = 0, bass = 0, mid = 0, peak = 0
    if (expansion > 0.05 && analyser && freqData) {
      analyser.getByteFrequencyData(freqData)
      const len = freqData.length
      const lowEnd = (len * 0.1) | 0
      const midEnd = (len * 0.4) | 0
      let sum = 0
      for (let i = 0; i < len; i++) {
        const v = freqData[i]; sum += v
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

    ctx.clearRect(0, 0, W, H)

    const cmap = { idle: "#7FFFD4", listening: "#00FFFF", analyzing: "#FF7B00", speaking: "#FFD700" }
    const baseColor = cmap[window.__jarvisStateName || "idle"] || "#7FFFD4"

    // ── Collapsed: mint 반원 (top center, near notch) ──
    const collapsedAlpha = 1 - expansion
    if (collapsedAlpha > 0.02) {
      const halfRadius = 60
      const cyTop = 6  // close to top edge
      ctx.save()
      ctx.globalAlpha = collapsedAlpha * 0.92
      // gradient mint glow
      const grad = ctx.createRadialGradient(cx, cyTop - 5, 4, cx, cyTop - 5, halfRadius * 1.2)
      grad.addColorStop(0, "#7FFFD4")
      grad.addColorStop(0.4, "rgba(127, 255, 212, 0.7)")
      grad.addColorStop(0.85, "rgba(127, 255, 212, 0.15)")
      grad.addColorStop(1, "rgba(127, 255, 212, 0)")
      ctx.fillStyle = grad
      ctx.beginPath()
      // 반원 — only bottom half visible
      ctx.arc(cx, cyTop - 5, halfRadius, 0, Math.PI, false)
      ctx.fill()
      // bright outline arc
      ctx.strokeStyle = "#7FFFD4"
      ctx.shadowColor = "#7FFFD4"
      ctx.shadowBlur = 14
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.arc(cx, cyTop - 5, halfRadius - 3, 0, Math.PI, false)
      ctx.stroke()
      // breathing dot at center
      const breath = (Math.sin(frame * 0.08) + 1) / 2
      ctx.beginPath()
      ctx.arc(cx, cyTop + halfRadius * 0.4, 2 + breath * 1.5, 0, 6.2832)
      ctx.fillStyle = "#7FFFD4"
      ctx.fill()
      ctx.restore()
    }

    // ── Expanded: 3D sphere ──
    if (expansion > 0.05) {
      const cy = H / 2
      const t = frame * 0.0035
      const cosT = Math.cos(t), sinT = Math.sin(t)
      const cosT2 = Math.cos(t * 0.5), sinT2 = Math.sin(t * 0.5)

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
      // insertion sort by z
      for (let i = 1; i < N; i++) {
        const v = idx[i]
        const k = curZ[v]
        let j = i - 1
        while (j >= 0 && curZ[idx[j]] > k) { idx[j + 1] = idx[j]; j-- }
        idx[j + 1] = v
      }

      ctx.shadowColor = baseColor
      ctx.fillStyle = baseColor
      const expAlpha = expansion

      for (let s_i = 0; s_i < N; s_i++) {
        const i = idx[s_i]
        ppx[i] *= 0.85; ppy[i] *= 0.85; ppz[i] *= 0.85
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
        const alpha = depthFade * (0.7 + smoothPeak * 0.3) * expAlpha
        ctx.shadowBlur = blurBoost * sc
        ctx.globalAlpha = alpha
        ctx.beginPath()
        ctx.arc(screenX, screenY, psize[i] * sc * sizeBoost, 0, 6.2832)
        ctx.fill()
      }
      ctx.globalAlpha = 1
      ctx.shadowBlur = 0

      // Concentric pulse rings
      if (smoothPeak > 0.18) {
        for (let r = 0; r < 3; r++) {
          const phase = ((frame + r * 18) % 90) / 90
          const radius = 30 + phase * 100
          ctx.beginPath()
          ctx.arc(cx, cy, radius * (1 + smoothPeak * 0.4), 0, 6.2832)
          ctx.strokeStyle = baseColor
          ctx.globalAlpha = (1 - phase) * smoothPeak * 0.55 * expAlpha
          ctx.lineWidth = 1.2
          ctx.shadowBlur = 12
          ctx.shadowColor = baseColor
          ctx.stroke()
        }
        ctx.globalAlpha = 1
        ctx.shadowBlur = 0
      }
    }

    // Suspend/resume audio context based on expansion
    if (audioCtx) {
      if (window.__jarvisExpanded && audioCtx.state === "suspended") {
        audioCtx.resume()
      } else if (!window.__jarvisExpanded && expansion < 0.05 && audioCtx.state === "running") {
        audioCtx.suspend()
      }
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
  html, body { margin: 0; padding: 0; background: transparent !important; overflow: hidden; }
  canvas { display: block; width: 100%; height: 100%; background: transparent !important; }
</style>
</head>
<body><canvas id="c"></canvas><script>\(visualizerJS)</script></body></html>
"""

// MARK: - App Delegate

class JarvisOverlayApp: NSObject, NSApplicationDelegate, WKUIDelegate {
    var panel: NSPanel!
    var webView: WKWebView!
    var statusItem: NSStatusItem!
    var stateTimer: Timer?
    var lastStateContent: String = ""
    var hoverMonitor: Any?
    var localHoverMonitor: Any?
    var collapseTimer: Timer?
    var isExpanded = false

    let collapsedW: CGFloat = 280
    let collapsedH: CGFloat = 70
    let expandedW: CGFloat = 420
    let expandedH: CGFloat = 380

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        requestMicPermission()
        setupPanel()
        setupStatusItem()
        watchStateFile()
        observeScreenChange()
        setupHoverMonitor()
    }

    func requestMicPermission() {
        AVCaptureDevice.requestAccess(for: .audio) { granted in
            if !granted {
                DispatchQueue.main.async {
                    let alert = NSAlert()
                    alert.messageText = "마이크 권한 필요"
                    alert.informativeText = "시스템 환경설정 → 개인정보 보호 → 마이크에서 JarvisHUD 허용 후 재시작."
                    alert.runModal()
                }
            }
        }
    }

    func collapsedFrame() -> NSRect {
        guard let screen = NSScreen.main else { return .zero }
        let w = collapsedW, h = collapsedH
        let x = screen.frame.midX - w / 2
        let y = screen.frame.maxY - h  // top edge (notch)
        return NSRect(x: x, y: y, width: w, height: h)
    }

    func expandedFrame() -> NSRect {
        guard let screen = NSScreen.main else { return .zero }
        let w = expandedW, h = expandedH
        let x = screen.frame.midX - w / 2
        let y = screen.frame.maxY - h
        return NSRect(x: x, y: y, width: w, height: h)
    }

    func setupPanel() {
        panel = NSPanel(
            contentRect: collapsedFrame(),
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

        if let cv = panel.contentView {
            cv.wantsLayer = true
            cv.layer?.backgroundColor = NSColor.clear.cgColor
        }

        let config = WKWebViewConfiguration()
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")
        config.mediaTypesRequiringUserActionForPlayback = []
        if #available(macOS 11.0, *) {
            config.defaultWebpagePreferences.allowsContentJavaScript = true
        }

        webView = WKWebView(frame: panel.contentView!.bounds, configuration: config)
        webView.autoresizingMask = [.width, .height]
        webView.setValue(false, forKey: "drawsBackground")
        webView.wantsLayer = true
        webView.layer?.backgroundColor = NSColor.clear.cgColor
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
        let toggle = NSMenuItem(title: "보이기/숨기기", action: #selector(toggleVisibility), keyEquivalent: "h")
        toggle.target = self
        let lvl = NSMenuItem(title: "최상위 레벨 토글", action: #selector(toggleLevel), keyEquivalent: "")
        lvl.target = self
        let force = NSMenuItem(title: "강제 expand 토글", action: #selector(forceToggleExpand), keyEquivalent: "")
        force.target = self
        let quit = NSMenuItem(title: "종료", action: #selector(quitApp), keyEquivalent: "q")
        quit.target = self
        menu.addItem(toggle)
        menu.addItem(.separator())
        menu.addItem(lvl)
        menu.addItem(force)
        menu.addItem(.separator())
        menu.addItem(quit)
        statusItem.menu = menu
    }

    @objc func toggleVisibility() {
        if panel.isVisible { panel.orderOut(nil) }
        else { panel.orderFrontRegardless() }
    }

    @objc func toggleLevel() {
        panel.level = (panel.level == .floating) ? .statusBar : .floating
    }

    @objc func forceToggleExpand() {
        if isExpanded { collapse() } else { expand() }
    }

    @objc func quitApp() { NSApp.terminate(nil) }

    func observeScreenChange() {
        NotificationCenter.default.addObserver(
            forName: NSApplication.didChangeScreenParametersNotification,
            object: nil, queue: .main
        ) { [weak self] _ in
            guard let self = self else { return }
            self.panel.setFrame(self.isExpanded ? self.expandedFrame() : self.collapsedFrame(), display: true)
        }
    }

    func setupHoverMonitor() {
        // Global mouse position polling (60Hz) — works regardless of click-through
        Timer.scheduledTimer(withTimeInterval: 0.05, repeats: true) { [weak self] _ in
            self?.checkHover()
        }
    }

    func checkHover() {
        guard let screen = NSScreen.main else { return }
        let pos = NSEvent.mouseLocation  // global, in screen coords
        // Hover trigger area: collapsed panel rect (always sensitive)
        // expanded시에는 expanded panel rect 전체로 감지 (떠난 후 collapse)
        let triggerRect = isExpanded ? expandedFrame() : collapsedFrame()
        // 좀 더 넓게 — 노치 위쪽 + 좌우 약간
        let expandedTrigger = NSRect(
            x: triggerRect.minX - 30,
            y: triggerRect.minY - 30,
            width: triggerRect.width + 60,
            height: triggerRect.height + 30
        )
        let inside = NSPointInRect(pos, expandedTrigger)
        if inside {
            collapseTimer?.invalidate()
            if !isExpanded { expand() }
        } else if isExpanded {
            // schedule collapse after 0.6s of leaving
            if collapseTimer == nil || !(collapseTimer?.isValid ?? false) {
                collapseTimer = Timer.scheduledTimer(withTimeInterval: 0.6, repeats: false) { [weak self] _ in
                    self?.collapse()
                }
            }
        }
    }

    func expand() {
        isExpanded = true
        let frame = expandedFrame()
        NSAnimationContext.runAnimationGroup { ctx in
            ctx.duration = 0.32
            ctx.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
            self.panel.animator().setFrame(frame, display: true)
        }
        webView.evaluateJavaScript("window.__jarvisExpanded = true", completionHandler: nil)
        // Trigger hover signal to daemon (file flag)
        writeHoverFlag(true)
    }

    func collapse() {
        isExpanded = false
        let frame = collapsedFrame()
        NSAnimationContext.runAnimationGroup { ctx in
            ctx.duration = 0.32
            ctx.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
            self.panel.animator().setFrame(frame, display: true)
        }
        webView.evaluateJavaScript("window.__jarvisExpanded = false", completionHandler: nil)
        writeHoverFlag(false)
    }

    func writeHoverFlag(_ active: Bool) {
        // 자비스 daemon에게 hover 신호 — ~/Library/Caches/jarvis-hover.json
        let url = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Caches/jarvis-hover.json")
        let payload = "{\"hover\": \(active ? "true" : "false"), \"ts\": \(Date().timeIntervalSince1970)}"
        try? payload.write(to: url, atomically: true, encoding: .utf8)
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
            // listening/analyzing/speaking 시 자동 expand (사용자 편의)
            if state != "idle" && !self.isExpanded {
                self.expand()
            }
        }
    }

    func webView(_ webView: WKWebView,
                 requestMediaCapturePermissionFor origin: WKSecurityOrigin,
                 initiatedByFrame frame: WKFrameInfo,
                 type: WKMediaCaptureType,
                 decisionHandler: @escaping (WKPermissionDecision) -> Void) {
        decisionHandler(.grant)
    }
}

// MARK: - Entry
let app = NSApplication.shared
let delegate = JarvisOverlayApp()
app.delegate = delegate
NSApp.run()
