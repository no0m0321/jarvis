# Windows / Linux 지원 로드맵

자비스 v0.4.0부터 Windows 베타, v0.5.0부터 Linux 베타 지원. 코어(LLM·voice·STT·TTS·screen·clipboard·webcam)는 모든 OS에서 cross-platform 동작. macOS 전용 기능(launchd, AppleScript, Übersicht HUD)은 Windows/Linux 등가물로 점진 포팅 중 (P2).

## 현황 (v0.5.0)

| 영역 | macOS | Windows | Linux |
|---|---|---|---|
| LLM 호출 (Anthropic SDK) | ✅ | ✅ | ✅ |
| 음성 입력 (sounddevice + faster-whisper) | ✅ | ✅ | ✅ |
| TTS | ✅ Reed/Yuna native | ✅ pyttsx3 + SAPI5 한국어 Heami | ✅ pyttsx3 + espeak |
| 클립보드 / 화면 캡처 / 웹캠 | ✅ | ✅ | ✅ |
| 알림 | ✅ Notification Center | ✅ win10toast/PowerShell | ✅ notify-send |
| 도구 명단 (REGISTRY 카운트) | 350 | 350 (+windows_*) | 350 (+linux_*) |
| cross-platform 도구 (245개) | ✅ | ✅ | ✅ |
| 첫 만남/호칭/Passive Learning | ✅ | ✅ | ✅ |
| `personalization_observe` 도구 | ✅ | ✅ | ✅ |
| AI 헬퍼 도구 10개 (ai_helpers.py) | ✅ | ✅ | ✅ |
| macOS 전용 도구 99개 | ✅ native | ⚠️ `@mac_only` graceful ERROR | ⚠️ 동일 |
| Windows 전용 도구 17개 (windows_extras + system_xp) | ⚠️ ERROR | ✅ | ⚠️ ERROR |
| Linux 전용 도구 13개 (linux_extras) | ⚠️ ERROR | ⚠️ ERROR | ✅ |
| Wake daemon | ✅ launchd | ✅ Task Scheduler | ❌ systemd unit 미구현 |
| HUD overlay (Übersicht / Swift) | ✅ | ❌ P3 | ❌ P3 |
| 권한 다이얼로그 일괄 트리거 (`jarvis permissions`) | ✅ | N/A 설정 앱 수동 | N/A |
| CI 매트릭스 | ✅ macos-14 | ✅ windows-latest (3.11/3.12) | ✅ ubuntu-latest |

## P0 (v0.4.0 ✅ 완료)

- [x] `install.ps1` 작성
- [x] `daemon_windows.py` (Task Scheduler 백엔드)
- [x] `daemon.py` 분기 wrapper
- [x] cli.py의 osascript / launchctl 직접 호출을 OS-aware로 분기

## P1 (v0.4.0 ✅ 완료)

- [x] TTS 자동 분기 (`_say` cross-platform — macOS=`say`, Windows=pyttsx3 SAPI)
- [x] 잔여 macOS path 정리 (`hud.py`, `wake.py`, `cli.py timer`)
- [x] macOS 도구 99개 `@mac_only` graceful 분기 — Windows에서 명확한 한국어 ERROR
- [x] README + CHANGELOG 업데이트

## P2 (진행 중 — macOS 도구의 Windows/Linux 등가물 신규 구현)

| macOS 도구 | Windows 등가물 | Linux 등가물 |
|---|---|---|
| `mail_compose` | ✅ `windows_outlook_compose` (v0.4.0) | TODO `linux_thunderbird_compose` |
| `apple_script` | ✅ `windows_run_powershell` (v0.4.0) | TODO `linux_run_bash` (이미 `run_shell` 있음) |
| `calendar_add/list_today` | TODO Outlook Calendar COM | TODO `evolution-calendar` |
| `reminder_add` | TODO Microsoft To Do API | TODO `gnome-todo` |
| `music_control` | TODO Spotify Web API | TODO MPRIS D-Bus |
| `bluetooth_status` | ✅ `windows_bluetooth_status` (v0.5.0) | ✅ `linux_bluetooth_status` (v0.5.0) |
| `dark_mode_*` | ✅ `windows_dark_mode_*` (v0.5.0) | ✅ `linux_dark_mode_*` (v0.5.0) |
| `audio_device_list/set` | ✅ `windows_audio_device_list` (v0.5.0, readonly) | TODO `linux_audio_device_*` (pactl list) |
| `mic_mute` | ✅ `windows_mic_mute` (v0.5.0, AudioDeviceCmdlets) | TODO amixer/pactl set-source-mute |
| `caffeinate_*` | ✅ `windows_caffeinate_start/stop` (v0.5.0) | ✅ `linux_caffeinate_start/stop` (v0.5.0) |
| `quick_look` | TODO Windows 11 Preview | TODO `gloobus-preview`/`sushi` |
| `finder_reveal` | ✅ `system_show_in_folder` (v0.4.0) | ✅ `system_show_in_folder` (v0.4.0) |
| `spotlight_search` | TODO Windows Search Indexer COM | TODO `tracker3 search` 또는 `recoll` |
| `airdrop_reveal` | TODO Nearby Sharing | TODO `bluez-obex` |
| `frontmost_app` / `running_apps` | ✅ `windows_frontmost_app` / `windows_running_apps` (v0.5.0) | TODO `linux_frontmost_app` (xdotool) |
| `top_processes` | ✅ `windows_top_processes` (v0.5.0) | ✅ `linux_top_processes` (v0.5.0) |
| `battery_info` | ✅ `windows_battery_info` (v0.5.0, Win32_Battery) | ✅ `linux_battery_info` (v0.5.0, upower) |
| `wifi_info` | ✅ `windows_wifi_info` (v0.5.0, netsh) | ✅ `linux_wifi_info` (v0.5.0, nmcli/iwgetid) |
| `listening_ports` | ✅ `windows_listening_ports` (v0.5.0, netstat) | TODO `linux_listening_ports` (ss/lsof) |
| `defaults_read` | ✅ `windows_registry_read` (v0.5.0) | TODO `linux_dconf_read` (gsettings + dconf) |
| `set_volume`/`get_volume` | TODO `windows_volume_*` (AudioDeviceCmdlets) | ✅ `linux_volume_set/get` (v0.5.0) |
| `window_*` (focus/position/minimize) | TODO Win32 API via PowerShell | ✅ `linux_window_list` (v0.5.0, wmctrl), 나머지 TODO |
| `safari_*` / `chrome_*` | TODO Selenium 또는 PyAutoGUI | TODO 동일 |
| `imessage_send` | N/A | N/A |
| `time_machine_*` | TODO File History (`wbadmin`) | TODO `restic` 또는 `borg` (별도 백업 도구 의존) |

## P3 (장기 — HUD overlay cross-platform)

- HUD overlay Swift → C# WPF / Electron / pystray
- 카메라 hover gate signal (HOVER_FILE) 일치
- 위치/크기 조정 (Windows에서는 right-click tray)

## 알려진 제약

- **마이크 권한**: Windows는 설정 > 개인정보 보호 및 보안 > 마이크에서 수동으로 Python에 허용 필요
- **자동 시작**: `schtasks /sc onlogon` 은 사용자 로그인 시 시작 (시스템 부팅과 다름). 시스템 부팅과 동시 시작이 필요하면 `/sc onstart /ru SYSTEM` 으로 수정 가능
- **PowerShell 정책**: ExecutionPolicy Restricted 환경에서 install.ps1은 `-ExecutionPolicy Bypass`로 명시 호출 필요
- **portaudio / sounddevice**: Windows 휠은 사전 빌드되어 있음 — `pip install sounddevice`만으로 동작
- **TTS 음질**: macOS native Yuna/Reed > Windows SAPI5 Heami. 주관적 품질 차이는 있으나 명료도는 충분

## 디버깅 팁 (Windows)

```powershell
# Task Scheduler 작업 상태
schtasks /query /tn JarvisWake /v /fo list

# wake daemon 로그
type "$env:APPDATA\jarvis\logs\wake.out.log"
type "$env:APPDATA\jarvis\logs\wake.err.log"

# 도구 명단 + 분기 동작 확인
.venv\Scripts\python.exe -c "from jarvis.tools import REGISTRY; print(len(REGISTRY.specs()))"
.venv\Scripts\python.exe -c "from jarvis.tools.applescript import _apple_script; print(_apple_script('return 1'))"
# → ERROR: macOS 전용 도구 — 현재 OS(win32)에서 미지원
```
