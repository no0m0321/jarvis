# JARVIS Premium Execution HUD 대규모 업데이트 계획

본 계획은 사용자가 지적한 요구사항 변경을 반영하여, 기존의 구매자용 웹 대시보드가 아니라 **자비스를 실행했을 때 자비스가 실제로 반응하고 상태를 보여주는 실행 창/HUD**를 중심으로 제품을 재설계한다. 목표는 단순한 설정 화면이 아니라, 고객이 앱을 켜는 순간 “AI 비서가 살아 있다”고 느낄 수 있는 상용급 데스크톱 경험을 제공하는 것이다.

## 1. 핵심 UX 재정의

| 영역 | 기존 방향 | 수정 방향 |
|---|---|---|
| 대시보드 의미 | 웹 계정/판매자용 운영 대시보드 중심 | 자비스 실행 시 뜨는 **실시간 반응형 Command HUD** 중심 |
| 첫 화면 | 설치·설정·KPI 중심 | 음성/명령/Claude 추론 상태가 보이는 **AI 코어 인터페이스** 중심 |
| 사용자 행동 | 프롬프트 입력 후 출력 확인 | 말하기, 명령 실행, 중지, wake daemon 제어, 상태 관찰, 실시간 로그 확인 |
| 제품 가치 | 패키징된 웹 대시보드 | 개인 AI 운영체제처럼 보이는 프리미엄 데스크톱 앱 |

## 2. 실행 창/HUD 필수 반영 사항

실행 창은 `idle → listening → analyzing → executing → speaking → complete/error` 상태를 명확히 시각화해야 한다. `src/jarvis/cli.py`의 wake 흐름과 `src/jarvis/hud.py`의 상태 파일을 기준으로, Electron 앱이 `~/Library/Caches/jarvis-hud.json`, `~/Library/Caches/jarvis-voice.json`, daemon 로그, Python CLI 출력을 통합 표시하도록 한다.

> 실행 창은 사용자가 자비스에게 말을 걸거나 명령을 입력하는 순간 반응해야 한다. 따라서 단순한 “대시보드”가 아니라 **자비스의 얼굴, 귀, 사고 과정, 응답 스트림을 보여주는 cockpit**이어야 한다.

## 3. 디자인 대규모 업데이트 방향

| 컴포넌트 | 업데이트 내용 |
|---|---|
| AI Reactor Core | 중앙의 살아 움직이는 원형 코어. 상태에 따라 색상·펄스·스캔 라인·음성 파형이 변경됨 |
| State Timeline | Idle, Listening, Transcribing, Thinking, Executing, Speaking 단계를 시간축으로 표시 |
| Conversation Stream | 사용자의 명령, 자비스 사고/출력, stderr, 완료 상태를 카드형 타임라인으로 표시 |
| Voice Spectrum | `jarvis-voice.json` 또는 시뮬레이션 RMS를 기반으로 마이크 입력 레벨 표시 |
| Daemon Controls | wake daemon 시작/중지/상태/로그 확인 버튼 제공 |
| Quick Missions | 고객이 바로 체감할 수 있는 프리셋 명령 제공 |
| System Readiness | Python, Claude API Key, 모델, 플랫폼, 패키징 상태를 간결한 readiness score로 표시 |
| Premium Settings | Claude 모델 라우팅, API 키 암호화 저장, 웹 계정 URL, 실행 모드(local/wake/agent) 설정 |

## 4. 기능 대규모 업데이트 방향

| 기능 | 구현 방식 |
|---|---|
| 명령 실행 모드 | `jarvis ask`, `jarvis do`, `jarvis wake` 모드 분리 지원 |
| 실시간 상태 폴링 | Electron main이 HUD/voice/log/daemon 상태를 주기적으로 읽어 renderer에 제공 |
| 자비스 반응 이벤트 | 실행 시작/출력/완료/오류 시 HUD 상태와 UI 상태를 즉시 동기화 |
| 데몬 제어 | Python `jarvis daemon status/start/stop/restart/logs` 또는 OS별 fallback 연결 |
| 응답 품질 향상 | Claude 모델 선택, smart routing, prompt cache, retry, timeout, usage estimation 강화 |
| 제품 안정성 | 입력 검증, URL 검증, API 키 safeStorage 저장, process cleanup, single instance lock |
| 판매 가치 요소 | 온보딩, readiness score, demo missions, release notes, premium documentation 추가 |

## 5. 구현 우선순위

| 우선순위 | 작업 | 산출물 |
|---:|---|---|
| 1 | Electron 실행 창을 실제 Command HUD 레이아웃으로 전면 교체 | `desktop/renderer/index.html`, `styles.css`, `renderer.js` |
| 2 | Electron main/preload에 HUD snapshot, voice, daemon, run mode IPC 추가 | `desktop/src/main.cjs`, `desktop/src/preload.cjs` |
| 3 | Claude provider/API 업그레이드 검증 및 누락된 모델/계측 보강 | `src/jarvis/providers.py`, `docs/api/*` |
| 4 | 제품 문서와 설치/빌드 지침 정리 | `desktop/README.md`, `JARVIS_DESKTOP_RELEASE_NOTES.md` |
| 5 | 실제 화면 검수 후 반응형/타이포그래피/상태 연출 보정 | 시각 검수 기록 및 수정 |
| 6 | Linux 데스크톱 산출물 빌드, GitHub 커밋·푸시 | `desktop/release/*`, GitHub |

## 6. 이번 재개 후 즉시 반영할 추가 업데이트 목록

1. **웹 계정 대시보드 중심 문구 제거**: 실행 창의 제목, 설명, KPI를 자비스 반응형 HUD 중심으로 교체한다.
2. **AI Reactor Core 강화**: 상태 클래스 기반으로 코어 색상과 애니메이션 속도를 변경한다.
3. **State Timeline 추가**: 실제 실행 단계와 CLI 출력에 맞춰 단계가 전환되도록 한다.
4. **Mission Presets 추가**: “오늘 업무 정리”, “코드 리뷰”, “시스템 진단”, “자동화 계획” 등 즉시 실행 가능한 프리셋을 제공한다.
5. **Daemon/Voice Panel 추가**: wake daemon, HUD 상태 파일, voice RMS, 최근 로그를 표시한다.
6. **Run Mode 추가**: 빠른 질의 `ask`, 도구 실행 `do`, wake daemon 제어 모드를 분리한다.
7. **운영 점수화**: Python, API Key, 모델, daemon, HUD 상태를 합산한 readiness score를 보여준다.
8. **상용화 문서 추가**: 무엇이 바뀌었는지, 설치 후 고객에게 어떻게 설명할지 정리한다.

이 문서는 구현 중 계속 갱신하지 않고, 실제 구현 결과는 최종 릴리스 노트와 검수 문서에 반영한다.
