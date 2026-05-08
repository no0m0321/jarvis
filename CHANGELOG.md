# Changelog

## v0.6.0 — 2026-05-08 (다국어 지원 + 다운로드 사이트)

### 추가 — 8개 언어 i18n 시스템

**🌍 src/jarvis/i18n.py 신규** — 8개 언어 정의 + helpers:
- 지원 언어: ko / en / ja / zh / es / fr / de / pt
- 각 언어 메타데이터: name, english_name, native, flag, default_title, tts_voice_macos/windows
- 첫 만남 인사 (4단계 인사 명세) — 8개 언어 모두
- 응답 강제 directive — non-native 언어를 위한 "ALWAYS respond in X" suffix
- `detect_lang()` — env JARVIS_LANG > config.toml language > locale > "en" fallback
- CLI 메시지 8개 언어 (lang_current/set_ok/unsupported/supported_list)
- API: `lang_meta(code)`, `default_title(code)`, `tts_voice(code, platform)`, `is_supported(code)`,
  `first_meeting_greeting(code)`, `respond_in_lang_suffix(code)`, `msg(key, lang)`

**🎭 src/jarvis/persona.py 변경** — 언어 분기:
- `PERSONAS_KO` (한국어 native) + `PERSONAS_EN` (영어 native) 분리
- `get_active()`가 `JARVIS_LANG` 인식 → 네이티브 prompt 또는 영어 base + i18n directive
- `PERSONAS` (기존 backward-compat) = `PERSONAS_KO`

**🤖 src/jarvis/assistant.py 변경**:
- 첫 만남 인사 블록을 `i18n.first_meeting_greeting()` 사용 → 언어별 자동 적용
- 한국어 hardcoded 제거, 모든 언어에서 동일한 4단계 인사 + personalization_observe + memory_save 안내

**🔊 src/jarvis/tools/macos.py 변경**:
- `_say_macos`가 JARVIS_VOICE env → `i18n.tts_voice()` → 'Yuna' fallback 우선순위로 voice 선택
- 한국어=Yuna, English=Reed, 日本語=Kyoko 등 자동

**📋 src/jarvis/config.py + user_config.py**:
- `Settings.lang` 필드 추가 (env JARVIS_LANG 자동 매핑)
- `apply_to_env()`에 `language: JARVIS_LANG` 매핑 추가
- `user_config.set_value(key, value)` 신규 — config.toml에 atomic update/append
  - 기존 [section] 헤더 보존, root-level 키만 update
  - 새 키는 첫 [section] 앞 (또는 끝)에 추가

**💻 src/jarvis/cli.py — `jarvis lang` 서브커맨드 신규**:
- `jarvis lang` (인자 없음) — 현재 언어 + 결정 source 표시
- `jarvis lang --list` — 8개 언어 목록 (현재 ●, 다른 ○ 마커)
- `jarvis lang <code>` — 언어 설정 (~/.jarvis/config.toml에 영구 저장)
- 미지원 언어 입력 시 한국어 ERROR + exit 1

**🚀 install.sh / install.ps1 — JARVIS_LANG 자동 사전 저장**:
- `JARVIS_LANG=ja curl ... | bash` 또는 `$env:JARVIS_LANG="ja"; iwr ... | iex`
- 설치 시점에 `~/.jarvis/config.toml`에 `language = "ja"` 자동 작성
- 기존 config.toml이면 language 라인만 update (다른 키 보존)
- 미지원 코드 입력 시 warning만 표시 (설치 자체는 진행)

**🌐 docs/download.html 신규 — 사이트에서 언어 선택 → 다운로드**:
- 8개 언어 카드 그리드 (깃발, 네이티브 이름, 영어 이름, 호칭, TTS voice)
- 클릭하면 install panel 펼쳐짐 + macOS/Linux vs Windows OS 탭
- 언어별 install 명령 자동 생성 (curl + JARVIS_LANG=xx)
- "Copy" 버튼 → clipboard에 복사
- 브라우저 언어 자동 감지 (navigator.language) → 사용자 언어 미리 선택
- FAQ 섹션 (언어 결정 우선순위, 변경 방법, TTS voice, 새 언어 추가)
- 톤 일관성: index.html과 동일한 cyan/black sci-fi theme

### 테스트 — +34 (총 181)

- `tests/test_i18n.py` (34) — 6개 클래스로 구성:
  - `TestI18nCore` (8) — 8개 언어 메타데이터 / 인사 / suffix / 호칭 / TTS / supported / fallback
  - `TestDetectLang` (5) — env / config.toml / locale / 정규화 / fallback 우선순위
  - `TestPersonaLanguageBranch` (4) — ko/en native, 그 외 영어+directive, 모드별
  - `TestAssistantFirstMeetingI18n` (8) — 8개 언어 모두 첫 만남 prompt 검증 (인사/호칭/도구 안내)
  - `TestCliLangCommand` (2) — `jarvis lang --list` / 미지원 언어 exit 1
  - `TestI18nMessages` (3) — msg() 다국어 lookup + fallback
  - `TestUserConfigSetValue` (4) — create / update / append / [section] 헤더 보존
- 회귀 fix: `test_extras.test_persona_module` + `test_profile_observations.TestSystemPromptIntegration` —
  i18n 적용 후 시스템 locale fallback이 영어로 가는 환경에서 한국어 명시 monkeypatch 추가

### 변경 요약

- 도구 카운트: **350 (변동 없음)** — i18n은 시스템 인프라이지 도구 추가 아님
- pyproject 0.5.0 → 0.6.0
- README: 8개 언어 지원 안내 + download.html link
- pytest 181/181 통과 (이전 147 + i18n 34)

### 사용 예시

```bash
# 한국어로 설치 (URL 한 줄)
curl -fsSL https://raw.githubusercontent.com/no0m0321/jarvis/main/install.sh | JARVIS_LANG=ko bash

# 일본어로 설치 (Windows)
$env:JARVIS_LANG="ja"; iwr https://raw.githubusercontent.com/no0m0321/jarvis/main/install.ps1 -UseBasicParsing | iex

# 설치 후 언어 변경
jarvis lang fr           # → 프랑스어
jarvis lang --list       # → 8개 언어 목록
jarvis lang              # → 현재 언어 + source 표시
```

---

## v0.5.0 — 2026-05-08 (cross-platform 대규모 확장 + 개인화)

### 추가 — 도구 301 → **350 (+49)**

**🎭 첫 만남 / 호칭 / Passive Learning 시스템** — "관찰을 통한 사후 개인화":
- `src/jarvis/profile.py` 신규 — `~/.jarvis/profile.json` (title, owner_name, first_met_at, interactions, preferences)
  - `is_first_meeting()`, `mark_first_meeting()`, `set_title()`, `get_preference()`, `reset()` API
- `src/jarvis/observations.py` 신규 — `~/.jarvis/observations.jsonl` (append-only, 최대 10000줄 후 자동 archive)
  - `append(category, content, source, weight, extra)`, `recent(n)`, `by_category(cat)`, `clear()`
  - `format_for_system_prompt(n)` — 시스템 프롬프트에 첨부할 형태로 포맷
- `src/jarvis/tools/personalization.py` 신규 — `personalization_observe` 도구 1개
  - agent가 사용자 패턴(반복 검색/명시 선호) 발견 시 즉시 기록 → 다음 대화의 시스템 프롬프트에 자동 첨부
- `src/jarvis/assistant.py` 변경 — `_build_system_prompt()`에 첫 만남/호칭/관찰 자동 첨부 로직
  - 첫 만남이면 → "주인님 반갑습니다. 저는 자비스입니다. 호칭 알려주세요" 4단계 인사 명시
  - 첫 만남 후엔 → 사용자 정보 블록 (호칭/첫 만남일/누적 대화)
  - 매 reply/stream/agent 호출마다 prompt rebuild (첫 만남 → 이후 분기 즉시 반영)
- `src/jarvis/agent.py` 변경 — `_build_system_prompt()` 매 agent 실행 호출, finally에서 `increment_interactions()`
- `src/jarvis/persona.py` 변경 — jarvis persona의 도구 list에 windows/linux/cross-platform/AI 헬퍼/personalization_observe 안내 추가, "Passive Learning" 행동 원칙 명시
- `src/jarvis/cli.py` 변경 — `jarvis profile` 서브커맨드 신규 (--title, --name, --pref, --reset, --observations N, --clear-observations)

**🪟 windows_extras.py — Windows 등가물 14개**:

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

**🔧 system_xp.py 확장 +10개**:
- `system_screenshot_to_file` — 화면 캡처 → PNG 파일 (mss, cross-platform)
- `system_record_audio` — 마이크 녹음 → WAV 파일 (sounddevice)
- `system_env_summary` — OS / Python / CPU / Memory / Disk / ~/.jarvis / API key 종합 진단
- `system_default_browser_url` — 기본 브라우저로 URL 열기
- `system_open_terminal_at` — 지정 폴더에서 새 터미널 (Terminal.app / wt.exe / gnome-terminal)
- `system_uptime` — 시스템 uptime + boot 시각 (psutil 우선, OS별 fallback)
- `system_locale` — locale / timezone / 키보드 레이아웃 (cross-platform)
- `file_compare_dirs` — 두 디렉토리 파일 차이 비교 (재귀, ONLY/DIFFER 분리, size+mtime 비교)
- `system_kill_process` — PID로 프로세스 종료 (graceful SIGTERM 또는 force SIGKILL/taskkill /F, PID 0/1/자기 자신 거부)
- `network_speedtest_simple` — 1.1.1.1 latency + Cloudflare 1MB 다운로드 throughput + public IP

### 변경

- `pyproject.toml` version 0.4.0 → 0.5.0
- `src/jarvis/tools/__init__.py` — 신규 모듈 import (ai_helpers, linux_extras, windows_extras)
- `.github/workflows/ci.yml` — `windows-latest` runner 추가 (Python 3.11/3.12, 3.9는 sounddevice wheel 안정성 이슈로 exclude). lint/type check는 Linux runner에서만 실행 (CI 시간 단축).
- README/CHANGELOG/TODO_WINDOWS — 도구 카운트 갱신, 신규 모듈 안내

### 테스트 — +99 (총 147개)

- `tests/test_system_xp.py` (9) — system_xp 9개 도구 동작 + windows_only graceful 분기
- `tests/test_platform_branching.py` (7) — `mac_only`/`windows_only` 데코레이터 동작, mock OS spoof
- `tests/test_xp_modules.py` (9) — windows_extras / linux_extras / ai_helpers 등록 + 분기 + input validation
- `tests/test_daemon_windows.py` (8) — schtasks subprocess mock 검증 (install/uninstall/status/tail_log)
- `tests/test_xp_extra.py` (22) — system_xp 추가 5개 도구 + 모든 v0.5.0 신규 도구 일괄 dispatch smoke + 도구 카운트=350 가드 + description/schema 검증 + regression 가드
- `tests/test_profile_observations.py` (33) — profile/observations 단위 테스트 + personalization_observe 도구 + 시스템 프롬프트 통합 (첫 만남/호칭/관찰 자동 첨부)
- `tests/test_cli_integration.py` (11) — subprocess로 jarvis CLI 직접 호출: version/profile/stats/tools-list/daemon status/help/한국어 출력 정상 검증

검증 결과: pytest 147/147 통과. mypy clean (신규 3개 파일). ruff: 안전한 fix 적용, 한국어 description의 라인-길이 경고는 기존 스타일과 일치.

### 기존 동작 유지

- macOS native 동작 unchanged (mac_only는 macOS에선 그대로 통과)
- v0.4.0 graceful 분기 정책 유지 (모든 OS에서 도구 명단 일관 노출)
- Windows에서 cross-platform 도구 약 245개 정상 동작 (이전 200개 → 245개로 증가)
- 기존 사용자 (~/.jarvis/profile.json 없음): 다음 호출에서 첫 만남 인사 → 호칭 묻기 → 답변 받으면 영구 저장

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
