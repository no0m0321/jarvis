# Windows 지원 로드맵

자비스 v0.4.0부터 Windows 베타 지원 시작. 코어(LLM·voice·STT·TTS·screen·clipboard·webcam)는 cross-platform이지만 macOS 전용 기능(launchd, AppleScript, Übersicht HUD 등)은 Windows 등가물로 점진 포팅 필요.

## 현황 (v0.4.0)

| 영역 | 상태 |
|---|---|
| LLM 호출 (Anthropic SDK) | ✅ 완전 동일 |
| 음성 입력 (sounddevice + faster-whisper) | ✅ 완전 동일 |
| TTS (pyttsx3 + SAPI5 한국어 Heami 자동 선택) | ✅ 동작 (macOS Reed/Yuna 대비 음질 차이) |
| 클립보드 / 화면 캡처 / 웹캠 | ✅ pyperclip / mss / opencv 모두 cross-platform |
| 알림 (toast) | ✅ win10toast → PowerShell native fallback |
| 도구 명단 (REGISTRY) | ✅ 모든 OS 동일 301개 |
| cross-platform 도구 약 200개 | ✅ 정상 동작 |
| macOS 전용 도구 99개 | ⚠️ `@mac_only` graceful → 한국어 ERROR 반환 (호출 시 agent에 안내) |
| 신규 Windows 전용 도구 (`windows_run_powershell`, `windows_outlook_compose`) | ✅ pywin32 + Outlook COM |
| Wake daemon | ✅ Windows Task Scheduler (`/sc onlogon`) |
| HUD overlay (Übersicht / Swift) | ❌ macOS 전용 (P3) |
| 권한 다이얼로그 일괄 트리거 (`jarvis permissions`) | N/A — Windows는 설정 앱에서 수동 |

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

## P2 (예정 — macOS 도구의 Windows 등가물 신규 구현)

| macOS 도구 | Windows 등가물 후보 |
|---|---|
| `mail_compose` | `windows_outlook_compose` ✅ (v0.4.0 추가) |
| `apple_script` | `windows_run_powershell` ✅ (v0.4.0 추가) |
| `calendar_add/list_today` | Outlook Calendar COM |
| `reminder_add` | Microsoft To Do API or Tasks COM |
| `music_control` | Spotify Web API or `tell-spotify` PowerShell |
| `bluetooth_status/toggle` | `Get-PnpDevice -Class Bluetooth` PowerShell |
| `dark_mode_toggle/set/status` | registry HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize\AppsUseLightTheme |
| `audio_device_list/set` | NirCmd 또는 PowerShell (AudioDeviceCmdlets) |
| `mic_mute` | NirCmd `mutesysvolume 1 default_record` |
| `caffeinate_start/stop` | PowerShell SetThreadExecutionState |
| `quick_look` | Windows 11 Preview / Quicklook 앱 |
| `finder_reveal` | `system_show_in_folder` ✅ (v0.4.0 추가) |
| `spotlight_search` | Windows Search Indexer COM (Microsoft.Search.Interop) |
| `airdrop_reveal` | Nearby Sharing (Windows 10+ Settings) |
| `frontmost_app` / `running_apps` | `Get-Process -IncludeUserName` PowerShell |
| `top_processes` | `Get-Process | Sort-Object -Descending CPU` |
| `window_*` (focus/position/minimize) | `Add-Type -TypeDefinition` + Win32 API |
| `safari_*` / `chrome_*` (브라우저 탭) | claude-in-chrome MCP 또는 Selenium |
| `imessage_send` | N/A — iMessage은 macOS/iOS 전용 |
| `time_machine_*` | File History (Windows 10+) — `wbadmin` 또는 PowerShell |

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
