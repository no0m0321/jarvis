# Changelog

## v0.2.0 — 2026-04-28 (대규모 업데이트)

### 추가 (50+ 변경)

**HUD widget v6 — 시네마틱 풀 overhaul**
- 위젯 크기 340 → **460**, **wake 시 자동 확대 (scale 1.16배 + glow surge)**
- 80-particle 3D cloud (40 inner + 40 outer 두 spherical layer)
- Voice-reactive (RMS에 따라 size 1.0→3.0, push outward)
- Hexagonal grid background overlay
- Animated perspective grid floor (sci-fi sweep)
- Code rain 양쪽 gutter (ｱｲｳｴｵ + 0/1/▓░ 6 columns)
- Wake burst expansion ring on listening 진입
- Voice peak flash overlay (RMS spike 감지)
- Voice waveform 32-bar (gradient + glow)
- CPU/MEM SVG sparkline (60s rolling history)
- Glitch text on header (analyzing 시 ▓░╳▣▦▩▤≡≣)
- Day/night palette (idle 시간대별: mint/cyan/std/magenta)
- 4 상태 dynamic theme + smooth cubic-bezier transitions
- 11 keyframe 애니메이션 (shake, pulse, float, edge-pulse, shimmer, cloud-spin, blink, burst-expand, rain-fall, rain-flicker, flash-fade, grid-sweep)
- Multi-layer 3D depth (translateZ per element)
- Aux ring orbit + corner brackets + scanlines + gradient mesh
- Cinematic boot fade-in (1.5s)
- Last log line 표시 (mini 영역)

**도구 (24개 신규 → 총 38개)**
- macos_extra: calendar_add, calendar_list_today, screen_capture, clipboard_read, clipboard_write
- macos_more: mail_compose, spotlight_search, activate_app, play_sound
- macos_extras2: music_control, set_volume, get_volume, set_brightness, reminder_add, note_search, note_list, battery_info, wifi_info, bookmark_add, top_processes, system_action
- utils: now, whoami, network_test, file_info, jarvis_status, ip_info, hash_file, env_get
- agent: web_search (Anthropic server tool 추가)

**신규 모듈**
- `src/jarvis/persona.py` — 4종 system prompt (jarvis/casual/formal/creative)
- `src/jarvis/history.py` — `~/.jarvis/history.jsonl` append-only
- `src/jarvis/health_server.py` — HTTP server :41418-41430 (`/healthz`, `/metrics`, `/tools`, `/history`)
- `~/.jarvis/memory.md` cross-session 기억 (system prompt에 자동 첨부)

**CLI 추가 명령**
- `jarvis note <text>` — 메모 timestamp 기록
- `jarvis timer <minutes> [-m message]` — N분 타이머
- `jarvis memory --show/--add/--edit/--clear`
- `jarvis update` — git pull + pip install
- `jarvis stats` — 자체 상태 dump
- `jarvis tools_list [--detail]` — 도구 list
- `jarvis hud {start|stop|state|history}`
- `jarvis daemon install --debug` 옵션 추가

**음성**
- TTS voice 기본 Yuna → **Reed** (남성, 자비스 톤)
- `JARVIS_VOICE` env로 override
- Voice RMS streaming (`capture_phrase` callback)
- Multi-language auto-detect (`language="auto"`)
- 32-sample waveform history

**Wake/Detection 개선**
- `strip_wake`이 모든 wake word 등장 제거 (반복 호출 → 단독 분기)
- False-positive 단어 제거 ("서비스/지비스/자비슨")
- `_WAKE_PROMPT` 약화로 hallucination 감소
- 전사 길이 < 3자 reject

**Sound effects**
- Listening: Tink.aiff (0.4 vol, async)
- Analyzing: Glass.aiff (0.4 vol, async)
- `JARVIS_HUD_SOUNDS=0` 으로 disable

### 수정
- React.Fragment 사용 제거 (Übersicht jsx 환경 호환)
- `config.py` dotenv_values 우회 패턴 (빈 shell env가 .env 로드 차단 버그)
- daemon plist `EnvironmentVariables` 동적 (`--debug` 옵션)

### 검증
- pytest 36 passed (29 + 7 new tests)
- 30+ HUD 시각 효과 모두 적용
- 38 tool 등록 확인
- health server :41418 작동
- daemon launchd 안정 작동

---

## v0.1.0 — 2026-04-28 (초기 릴리스)

### 추가
- 자비스 스캐폴딩 (Python 3.9, Anthropic SDK + Typer + Rich)
- 9개 client-side tools (shell/fs/web/macOS basic)
- Voice I/O (sounddevice + faster-whisper)
- Wake word 감지 (initial_prompt hint 트릭)
- launchd daemon (RunAtLoad + KeepAlive)
- HUD v1 widget (cyan glow, voice-reactive 32 particles)
- Prompt caching (system + tools)

---

Made with ◈ by swxvno + Claude Opus 4.7
