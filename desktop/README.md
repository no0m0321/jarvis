# JARVIS Live Command HUD Desktop

JARVIS Live Command HUD는 기존 Python 기반 자비스 런타임을 **설치형 데스크톱 앱**으로 감싼 프리미엄 실행 창입니다. 이 앱은 단순한 웹 계정 대시보드가 아니라, 사용자가 자비스를 실행했을 때 자비스의 **청취, 분석, 응답, 명령 수행, 데몬 상태, Claude 사용량, 최근 메모리**를 한 화면에서 실시간으로 확인하고 제어하는 상용형 Command HUD입니다.

## 핵심 가치

| 영역 | 설명 |
|---|---|
| Live Command HUD | 자비스 실행 시 바로 뜨는 반응형 실행 창으로, idle/listening/analyzing/executing/speaking/error 상태를 시각적으로 표시합니다. |
| 실시간 반응 시각화 | Python HUD 상태 파일과 음성 레벨 파일을 폴링해 자비스가 듣고 있는지, 분석 중인지, 답변 중인지 즉시 보여줍니다. |
| Claude 자동 라우팅 | `auto` 모델 모드에서 입력 난이도와 작업 유형을 기준으로 Haiku/Sonnet/Opus 계열 모델을 자동 선택합니다. |
| 데몬 제어 | wake daemon 상태 확인, 시작, 재시작, 중지, 로그 조회를 앱 안에서 수행합니다. |
| Command Console | `jarvis ask`와 `jarvis do`를 앱 안에서 실행하고 stdout/stderr를 실시간 콘솔로 확인합니다. |
| 프리미엄 운영 패널 | Claude 사용량, 평균 지연 시간, 입력/출력 토큰, 캐시 토큰, 최근 history, 도구 목록, 진단 결과를 표시합니다. |
| 세션 리포트 | 현재 HUD 상태, 음성 상태, Claude 사용량, 최근 기록, 세션 로그를 JSON 리포트로 내보냅니다. |
| 보안 설정 | Claude API 키를 Electron `safeStorage` 기반으로 저장하며, 환경 변수와 앱 설정을 함께 지원합니다. |
| 배포 패키징 | Linux AppImage/deb/zip을 기본 생성하며 macOS dmg/zip, Windows nsis/zip 설정도 포함합니다. |

## 개발 실행

```bash
cd desktop
pnpm install
pnpm start
```

## 설치 파일 빌드

```bash
cd desktop
pnpm install
pnpm run build
```

빌드 결과는 `dist/desktop/`에 생성됩니다. Linux 환경에서는 AppImage, deb, zip이 생성됩니다. macOS와 Windows 산출물은 각 OS 빌드 머신 또는 CI에서 `pnpm run dist:all`로 생성하는 것을 권장합니다.

## 런타임 전제 조건

데스크톱 앱은 포함된 Python 소스(`extraResources/jarvis-src`)를 기준으로 실행되며, 사용자의 시스템에 Python과 자비스 의존성이 설치되어 있어야 합니다. 상용 배포에서는 설치 스크립트 또는 별도 런처를 통해 다음 명령을 선행 실행하도록 안내하면 됩니다.

```bash
python -m pip install -e .[all]
```

## 환경 변수

| 변수 | 설명 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API 호출용 키입니다. 앱 Secure Setup 영역에서도 저장할 수 있습니다. |
| `JARVIS_MODEL` | 기본 Claude 모델입니다. 권장값은 `auto`이며, 앱 설정의 Preferred Model이 우선합니다. |
| `JARVIS_APP_URL` | 판매/계정 웹사이트 주소입니다. 앱 메뉴에서 외부 대시보드를 열 때 사용합니다. |
| `JARVIS_PYTHON` | 특정 Python 실행 파일을 강제할 때 사용합니다. 예: `/opt/homebrew/bin/python3.12`. |
| `JARVIS_HEALTH_PORT` | 로컬 health server 포트입니다. 기본값은 `41418`입니다. |

## 실행 창 사용 흐름

1. 앱을 실행하면 **JARVIS Live Command HUD**가 먼저 표시됩니다.
2. Secure Setup에서 Claude API 키와 모델(`auto` 권장)을 저장합니다.
3. Command Console에서 `ask` 또는 `do` 모드를 선택하고 명령을 실행합니다.
4. 음성 wake 환경을 사용할 경우 Daemon 패널에서 daemon을 시작합니다.
5. 우측 운영 패널에서 사용량, 최근 메모리, 도구 목록, 진단 결과를 확인합니다.
6. 필요한 경우 **세션 리포트 저장**으로 고객 지원 또는 운영 보고용 JSON을 내보냅니다.

## 상용 배포 메모

이 데스크톱 앱은 고객이 처음 실행했을 때 “자비스가 살아 움직이는 느낌”을 주도록 설계되었습니다. 따라서 판매용 패키지에서는 API 키 입력, 권한 설정, 마이크 권한, macOS 자동화 권한, Python 의존성 설치 여부를 첫 실행 온보딩에서 확인하는 것이 좋습니다. 현재 버전은 앱 내부 진단과 세션 리포트 기능을 포함하므로, 초기 고객 지원 및 고가 상품 판매 후 유지보수에도 활용할 수 있습니다.
