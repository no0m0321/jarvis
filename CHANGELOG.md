# Changelog

## v0.5.0 — 2026-05-08 (cross-platform 대규모 확장)

### 추가 — 도구 301 → **344 (+43)**

**🪟 windows_extras.py — Windows 등가물 14개**:
- 다크모드: `windows_dark_mode_status` / `windows_dark_mode_set` / `windows_dark_mode_toggle` (registry HKCU)
- 시스템: `windows_top_processes`, `windows_frontmost_app`, `windows_running_apps`, `windows_audio_device_list`, `windows_mic_mute`
- 진단: `windows_battery_info` (Win32_Battery), `windows_wifi_info` (netsh), `windows_bluetooth_status` (Get-PnpDevice)
- Sleep 방지: `windows_caffeinate_start` / `windows_caffeinate_stop` (SetThreadExecutionState)
- 네트워크/시스템: `windows_listening_ports` (netstat), `windows_registry_read`

**🐧 linux_extras.py — Linux 등가물 13개**:
- `linux_notify` (notify-send)
- `linux_dark_mode_status/set/toggle` (gsettings GNOME)
- `linux_top_processes` (ps -eo pid,pcpu,pmem,comm)
- `linux_volume_set/get` (amixer 우선, pactl fallback)
- `linux_battery_info` (upower)
- `linux_wifi_info` (nmcli/iwgetid)
- `linux_bluetooth_status` (bluetoothctl)
- `linux_caffeinate_start/stop` (systemd-inhibit/xset)
- `linux_window_list` (wmctrl)

**🤖 ai_helpers.py — Claude 기반 cross-platform 10개**:
- `text_summarize` — 긴 텍스트 N줄 요약 (lang ko/en)
- `text_proofread` — 맞춤법/문법 교정 + 변경점 설명
- `text_explain` — 어려운 개념 풀이 (파인만 기법, audience 지정)
- `text_korean_polish` — 어색한 한국어/번역체 다듬기 (tone: neutral/formal/casual/professional)
- `email_draft` — 이메일 초안 (tone, lang, recipient)
- `code_explain` — 코드 동작 설명 (lang_hint)
- `code_review_quick` — 빠른 코드 리뷰 (focus: all/security/performance/style)
- `decision_helper` — 의사결정 보조 (장단점 + 조건부 추천)
- `task_decompose` — 큰 작업을 단계별 분해 (depth 1/2/3)
- `meeting_notes_format` — 자유 메모 → 구조화된 회의록

**🔧 system_xp.py 확장 5개**:
- `system_screenshot_to_file` — 화면 캡처 → PNG 파일 (mss, cross-platform)
- `system_record_audio` — 마이크 녹음 → WAV 파일 (sounddevice)
- `system_env_summary` — OS / Python / CPU / Memory / Disk / ~/.jarvis / API key 종합 진단
- `system_default_browser_url` — 기본 브라우저로 URL 열기
- `system_open_terminal_at` — 지정 폴더에서 새 터미널 (Terminal.app / wt.exe / gnome-terminal)

### 변경

- `pyproject.toml` version 0.4.0 → 0.5.0
- `src/jarvis/tools/__init__.py` — 신규 모듈 import (ai_helpers, linux_extras, windows_extras)
- `.github/workflows/ci.yml` — `windows-latest` runner 추가 (Python 3.11/3.12, 3.9는 sounddevice wheel 안정성 이슈로 exclude). lint/type check는 Linux runner에서만 실행 (CI 시간 단축).
- README/CHANGELOG/TODO_WINDOWS — 도구 카운트 갱신, 신규 모듈 안내

### 테스트 — +33 (총 81개)

- `tests/test_system_xp.py` — system_xp 9개 도구 동작 + windows_only graceful 분기
- `tests/test_platform_branching.py` — `mac_only`/`windows_only` 데코레이터 동작, mock OS spoof
- `tests/test_xp_modules.py` — windows_extras / linux_extras / ai_helpers 등록 + 분기 + input validation
- `tests/test_daemon_windows.py` — schtasks mock 검증 (install/uninstall/status/tail_log)

### 기존 동작 유지

- macOS native 동작 unchanged (mac_only는 macOS에선 그대로 통과)
- v0.4.0 graceful 분기 정책 유지 (모든 OS에서 도구 명단 일관 노출)
- Windows에서 cross-platform 도구 약 240개 정상 동작 (이전 200개 → 240개로 증가)

---

## v0.4.0 — 2026-05-08 (Windows 베타 + 도구 graceful 분기)

### 변경 — Windows 베타 지원 (P0 + P1 + 도구 graceful 분기)

**인프라**:
- `install.ps1` 신규 — PowerShell 5+ 설치 스크립트 (Python venv + pip + jarvis.bat 래퍼)
- `install.sh` — Linux 분기 추가, Windows 진입 시 install.ps1 안내
- `src/jarvis/daemon_windows.py` 신규 — `schtasks /sc onlogon` 기반 Task Scheduler 백엔드 (install/uninstall/restart/status/tail_log)
- `src/jarvis/daemon.py` — IS_WINDOWS 분기 wrapper로 변경, daemon_windows에 위임
- `src/jarvis/cli.py` — `jarvis doctor` / `permissions` / `timer` 가 OS-aware 분기 (Windows: schtasks 체크 + winsound MessageBeep)
- `src/jarvis/voice/wake.py` — `_HOVER_FILE` macOS는 `~/Library/Caches`, 그 외는 `~/.jarvis/cache`. `JARVIS_HOVER_GATE` 기본값 Windows/Linux=OFF
- `pyproject.toml` — version 0.3.1 → 0.4.0

**graceful 분기 (반복 작업)**:
- `tools/__init__.py` — macOS 전용 모듈 10개의 `if IS_MACOS:` 가드 제거. Windows에서도 모든 도구가 REGISTRY에 등록되어 명단 노출.
- macOS 핸들러 99개에 `@mac_only` 데코레이터 부착 — Windows/Linux 호출 시 `"ERROR: macOS 전용 도구 — 현재 OS(win32)에서 미지원"` 한국어 string 반환
  - `applescript.py` (5), `comm.py` (1: imessage), `extras.py` (9: shortcuts/spotify/dnd/dock/trash), `macos_browser.py` (8), `macos_extras2.py` (9), `macos_more.py` (4), `macos_system.py` (21), `productivity.py` (5), `productivity_extra.py` (5: alarm_set/eye_break/breathing/meditation), `window_mgmt.py` (7)

### 추가 — 도구 297 → **301 (+4)**

신규 모듈 [`src/jarvis/tools/system_xp.py`](src/jarvis/tools/system_xp.py):

- `system_open_path` (cross-platform): 로컬 파일/폴더를 OS 기본 앱으로 열기 — macOS=`open`, Windows=`os.startfile`, Linux=`xdg-open`
- `system_show_in_folder` (cross-platform): 파일 탐색기에서 select/reveal — macOS=`open -R`, Windows=`explorer /select,`, Linux=부모 폴더
- `windows_run_powershell` (Windows 전용 — `apple_script` Windows 등가물): NoProfile + ExecutionPolicy Bypass로 PowerShell 실행
- `windows_outlook_compose` (Windows 전용 — `mail_compose` Windows 등가물): pywin32 Outlook COM, 실패 시 mailto fallback

### 문서

- README — "macOS 네이티브" → "macOS 우선, Windows 베타", 도구 카운트 296 → 301, install.ps1 안내 추가
- `docs/TODO_WINDOWS.md` 신규 — Windows 지원 P0/P1/P2/P3 로드맵 + 현황 표

### 기존 동작 유지

- macOS에서는 모든 도구 동작 unchanged (mac_only 데코레이터는 macOS에서 그대로 통과)
- Windows에서 cross-platform 도구 약 200개 정상 동작 (notify/say/clipboard/screen_capture/web_search 등)
- Windows에서 macOS 전용 도구 99개는 명확한 한국어 ERROR string 반환 (raise 없음 → agent loop 안전)

---

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
