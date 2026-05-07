# Changelog

## v0.3.1 — 2026-05-04 (도구 확장 2차)

### 추가 — 도구 247 → **296개 (+49)**

5개 모듈 추가:

**🛠 dev_extra.py — 개발 도구 (15)**
- git: `git_branch_list`, `git_stash_list`, `git_remote_info`, `git_recent_commits`, `git_blame_line`, `git_changed_files`
- 패키지: `npm_outdated`, `pip_outdated`, `brew_outdated`, `brew_list`, `brew_info`
- Docker: `docker_ps`, `docker_logs`, `docker_images`
- 기타: `editor_open`, `loc_count`, `project_size`

**🌐 network_extra.py — 네트워크 (8)**
- `arp_table`, `traceroute`, `route_default`, `http_bench` (p50/p95 응답시간)
- `ip_geo` (ipinfo.io), `mac_lookup` (macvendors.com)
- `ping_avg`, `net_interfaces`

**📂 files_extra.py — 파일 (10)**
- `file_exif` (exiftool), `media_info` (ffprobe)
- `find_duplicates` (size+md5), `find_large_files`, `find_old_files`
- `symlink_create`, `symlink_resolve`, `chmod_set`, `tar_extract`, `trash_size`

**🎉 fun.py — 재미 (8)**
- `joke`, `riddle` (정답 옵션), `random_fact`, `compliment` (이름 prefix)
- `motivation`, `fortune`, `name_generator` (fantasy/sci-fi/petname/domain), `eight_ball_extended`

**📊 data_viz.py — ASCII 시각화 (6)**
- `bar_chart` (가로 막대), `sparkline` (▁▂▃▄▅▆▇█)
- `habit_heatmap` (30일 ■/·)
- `weight_chart` (체중 추이), `finance_chart` (일별 지출)
- `calendar_view` (텍스트 달력)

### 변경
- version 0.3.0 → 0.3.1
- README 도구 카운트 247 → 296

---

## v0.3.0 — 2026-05-04 (대규모 도구 확장)

### 추가 — 도구 168 → **247개 (+79)**

총 **6개 신규 모듈** 추가, 모두 자동 등록(REGISTRY) — daemon/agent 재기동 즉시 사용 가능.

**🌐 macos_browser.py — Safari/Chrome 제어 (8 tools)**
- `safari_new_tab`, `safari_current_url`, `safari_list_tabs`, `safari_close_current`, `safari_reload`
- `chrome_new_tab`, `chrome_current_url`, `chrome_list_tabs`

**🖥 macos_system.py — 시스템 제어 (20 tools)**
- 블루투스: `bluetooth_status`, `bluetooth_toggle` (blueutil)
- 다크모드: `dark_mode_toggle`, `dark_mode_set`, `dark_mode_status`
- 오디오: `audio_device_list`, `audio_device_set` (switchaudio-osx), `mic_mute`
- Time Machine: `time_machine_status`, `time_machine_latest`
- 시스템 진단: `listening_ports`, `memory_pressure`, `diskutil_list`, `mdls_metadata`, `log_show`, `defaults_read`
- 파일: `airdrop_reveal`, `quick_look`, `finder_reveal`
- Sleep 방지: `caffeinate_start`, `caffeinate_stop`

**⏰ productivity_extra.py — 생산성/웰니스 (12 tools)**
- 알람: `alarm_set`, `alarm_list`, `alarm_clear` (백그라운드 thread + TTS)
- 스톱워치: `stopwatch_start`, `stopwatch_lap`, `stopwatch_stop`
- 시계: `world_clock` (다중 timezone 한 번에)
- 웰니스: `eye_break_start`/`stop` (20-20-20), `breathing_478` (4-7-8 호흡), `meditation` (N분 명상)
- 천체: `sun_times` (일출/일몰, NOAA 근사), `moon_phase` (Conway algorithm)

**🔧 util_extra.py — 범용 유틸 (13 tools)**
- 텍스트: `emoji_search`, `unicode_info`, `text_stats`, `reverse_text`, `ansi_strip`
- 파일: `hex_view`, `path_info`
- 보안: `encrypt_file`, `decrypt_file` (openssl AES-256-CBC), `ssh_keygen` (ed25519), `secret_token`
- 렌더: `mermaid_render` (mmdc CLI)
- 시스템: `dictionary_define` (macOS Dictionary.app)

**💰 finance.py — 재무 추적 (5 tools)**
- `expense_log`, `income_log` (~/.jarvis/finance.jsonl)
- `finance_summary` (N일 카테고리별 요약)
- `networth_set`, `networth_history`

**🪟 window_mgmt.py — 창 관리 (7 tools)**
- `window_list` (모든 visible 창 + 위치/크기)
- `window_focus`, `window_position` (이동/리사이즈), `window_minimize`, `hide_app`
- `mission_control`, `show_desktop`

**🩺 health_extra.py — 건강 추적 (8 tools)**
- 체중: `weight_log`, `weight_history`
- 혈압: `bp_log` (자동 분류 — 정상/주의/고혈압), `bp_history`
- 심박/걸음: `hr_log`, `steps_log`, `steps_summary`
- 계산: `bmi_calc`

### 변경
- `pyproject.toml` version 0.2.0 → 0.3.0
- `src/jarvis/__init__.py` __version__ 동기화
- `README.md` 도구 카운트 49 → 247 갱신
- `src/jarvis/tools/__init__.py` 신규 6개 모듈 import 등록

### 참고
- 일부 도구는 외부 CLI 필요: `blueutil` (bluetooth), `switchaudio-osx` (audio device), `mmdc` (mermaid), `brightness` (display) — 미설치 시 안내 메시지만 출력하고 실패하지 않음.
- 알람/명상 등 백그라운드 thread는 `daemon=True` — daemon 종료 시 같이 종료됨.

---

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

Made with ◈ + Claude Opus 4.7
