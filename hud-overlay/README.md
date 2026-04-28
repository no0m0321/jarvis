# JarvisHUD — Always-On-Top Particle Overlay

자비스의 transparent floating particle visualizer. 데스크톱 상단 중앙에 **항상 떠있는 3D 원형 sphere**. 다른 모든 창 위에 표시 (Übersicht의 desktop layer 한계 극복).

```
NSPanel (.borderless + .nonactivatingPanel)
  + .floating level (또는 .statusBar for above-fullscreen)
  + isOpaque false, backgroundColor .clear, hasShadow false
  + ignoresMouseEvents true (click-through to apps below)
  + collectionBehavior [.canJoinAllSpaces, .stationary, .ignoresCycle]
WKWebView (transparent, embedded HTML/JS)
  → 220-particle 3D sphere visualizer (Web Audio + Canvas)
  → 60-120 FPS RAF loop
```

## 빌드

```bash
cd /Users/swxvno/jarvis/hud-overlay
./build.sh                # JarvisHUD.app 빌드
./build.sh install        # + /Applications/ 설치
./build.sh launchd        # + LaunchAgent 등록 (자동 시작)
```

요구: **macOS 13+**, **Xcode CLT** (`xcode-select --install`).

## 실행

```bash
open /Applications/JarvisHUD.app
# 또는
open ./JarvisHUD.app    # 빌드 디렉토리에서 바로 테스트
```

**첫 실행 시:**
1. macOS 마이크 권한 다이얼로그 → 허용
2. 데스크톱 상단 중앙에 cyan 원형 sphere 등장
3. 클릭은 통과 (click-through) — 다른 앱과 간섭 없음

## 메뉴바 (◈ 아이콘)

- **보이기/숨기기** (⌘H)
- **위치 재설정** (⌘R) — 화면 변경 후 재배치
- **최상위 레벨 토글** — `.floating` ↔ `.statusBar`
  - `.floating`: 일반 창들 위에 표시 (기본)
  - `.statusBar`: fullscreen 앱 위에도 표시
- **종료** (⌘Q)

## 자비스 daemon과 통신

`~/Library/Caches/jarvis-hud.json` 파일을 1초마다 polling.
자비스가 `hud.set_state("listening" / "analyzing" / "speaking")`로 쓰면 overlay 색상 자동 변경:

| state | color |
|---|---|
| idle / listening | `#00FFFF` (cyan) |
| analyzing | `#FF7B00` (amber) |
| speaking | `#FFD700` (gold) |

## 자동 시작 (LaunchAgent)

```bash
./build.sh launchd
```

또는 수동:
```bash
cp com.swxvno.jarvis.hud.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.swxvno.jarvis.hud.plist
```

해제:
```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.swxvno.jarvis.hud.plist
rm ~/Library/LaunchAgents/com.swxvno.jarvis.hud.plist
```

## 설계 특징

- **Single .swift file** (~150 줄) + embedded HTML/JS payload — 외부 리소스 X
- **No third-party deps** — AppKit + WebKit + AVFoundation만
- **Click-through**: 화면 위 모든 클릭이 아래 앱으로 통과
- **Multi-screen 자동 재배치**: 모니터 추가/제거 시 NSScreen 변경 감지
- **Microphone**: WKUIDelegate `requestMediaCapturePermissionFor` → `.grant`
- **State channel**: file watch (Timer 1Hz) → JS injection
- **All Spaces**: `canJoinAllSpaces` + `stationary` — 모든 데스크톱에서 같은 위치

## 트러블슈팅

**원이 안 보임**:
- 메뉴바 ◈ 클릭 → "보이기/숨기기"로 toggle
- "위치 재설정"으로 화면 중앙 강제 이동
- 다른 앱 fullscreen 상태면 "최상위 레벨 토글"

**점이 음성에 반응 안 함**:
- 마이크 권한 확인: 시스템 환경설정 → 개인정보 보호 → 마이크 → JarvisHUD ON
- 첫 실행 다이얼로그를 거부했으면 위 환경설정에서 수동 추가

**색상이 안 바뀜**:
- 자비스 daemon 작동 중인지 확인: `jarvis daemon status`
- `cat ~/Library/Caches/jarvis-hud.json` — 파일이 있고 state가 변경되는지

## 라이선스

자비스 프로젝트의 일부. 자유 사용.
