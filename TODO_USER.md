# 사용자(승우) 액션 필요 List

자율 진행 불가능 — 사용자가 직접 해야 하는 항목들.

## 시각 확인 (HUD 화면)
- [ ] 우측 상단 460px 위젯이 떠있는지
- [ ] Wake 시 widget이 1.16배 자동 확대되는지 (사용자 명시 요청)
- [ ] 80-particle 3D cloud 회전이 보이는지
- [ ] 양쪽 gutter에 code rain (ｱｲｳｴｵ 흐름)이 보이는지
- [ ] Listening 진입 시 wake burst (60→360px 원이 확장)이 한 번 발생하는지
- [ ] Voice 발화 시 32-bar waveform이 진동하는지
- [ ] Analyzing 시 "JARVIS HUD"가 ▓░╳▣ 글자로 글리치되는지
- [ ] 시간대별 idle accent 색이 바뀌는지 (저녁이면 magenta)
- [ ] grid floor가 perspective sweep 되는지

## 청각 확인
- [ ] Listening 진입 시 Tink.aiff (작은 chime)
- [ ] Analyzing 진입 시 Glass.aiff (sci-fi chime)
- [ ] TTS voice가 Reed (남성, 자비스 톤)인지 — Yuna(여성) 선호 시 `JARVIS_VOICE=Yuna` 환경변수
- [ ] daemon plist에 voice 환경변수 추가하려면: `JARVIS_VOICE=Yuna jarvis daemon install --debug`

## 권한 부여 (macOS 시스템 환경설정)
- [ ] **마이크** — `Python` 또는 `Terminal`에 토글 ON (이미 부여됨, 확인용)
- [ ] **접근성** — `screen_capture` 도구 사용 시 필요 (시스템 환경설정 → 개인정보 보호 → 접근성)
- [ ] **자동화** — `osascript` 통해 Calendar/Reminders/Music/Mail 제어 시 첫 실행 시 다이얼로그
  - "Terminal이 Calendar를 제어하려고 합니다" → 허용
  - 같은 다이얼로그 Music/Reminders/Mail에 대해서도

## 도구 e2e 테스트 (자비스 부르고 발화)
사용자 발화 시 LLM이 의도 파악 → 도구 실행 → 답변. 순서대로 시도:

- [ ] "자비스 현재 시간 알려줘" → `now` tool
- [ ] "자비스 IP 주소 알려줘" → `ip_info`
- [ ] "자비스 배터리 상태" → `battery_info`
- [ ] "자비스 와이파이 정보" → `wifi_info`
- [ ] "자비스 클립보드 보여줘" → `clipboard_read`
- [ ] "자비스 음악 켜줘" → `music_control(play)`
- [ ] "자비스 사파리 열어" → `activate_app(Safari)`
- [ ] "자비스 데스크톱 캡처해" → `screen_capture` (권한 다이얼로그)
- [ ] "자비스 볼륨 30% 로 줄여" → `set_volume`
- [ ] "자비스 5분 후에 물 마시라고 알림" → `reminder_add`
- [ ] "자비스 오늘 일정 알려줘" → `calendar_list_today` (Calendar 권한)
- [ ] "자비스 'Anthropic Claude' 검색" → `web_search` (server tool)
- [ ] "자비스 ~/Downloads에 뭐 있어" → `list_dir`
- [ ] "자비스 OpenAI 도메인 주소 ping 테스트" → `network_test`
- [ ] "자비스 화면 잠가" → `system_action(lock)` ⚠ 실제 잠김

## 설정/커스터마이징
- [ ] `~/.jarvis/memory.md` — 자비스에게 알리고 싶은 본인 정보 추가 (자동 시스템 프롬프트 첨부)
  ```bash
  jarvis memory --add "나는 미니멀 디자인을 선호함"
  jarvis memory --add "회의는 화/목 오후만"
  jarvis memory --add "코드 응답은 Python 3.9 호환으로"
  ```
- [ ] HUD 위치 변경 — `hud/jarvis-hud.widget/index.jsx`의 `top: 50px; right: 50px;` 수정
- [ ] Persona 전환 — `JARVIS_PERSONA=casual jarvis ask "..."` (기본 jarvis 외 casual/formal/creative)

## 경험적 검증 (작동 확인 필요)
- [ ] launchd가 부팅 시 자동 시작하는지 (`sudo reboot` 후 확인 — 강요는 X)
- [ ] daemon이 24시간 안정 작동 (KeepAlive 확인)
- [ ] 마이크 권한 후 wake daemon이 silent denial 안 일으키는지

## 선호 결정 (피드백 필요)
- [ ] HUD 위젯 크기 460px 적당? 더 크게/작게?
- [ ] Wake zoom 1.16배 적당? 더 강하게?
- [ ] code rain 너무 어수선하면 비활성 옵션 추가 가능
- [ ] 시간대별 색조 변경이 좋은지, 항상 cyan 유지가 좋은지
- [ ] sci-fi 사운드 끄려면 `JARVIS_HUD_SOUNDS=0`

---

자율 가능한 모든 작업은 별도 진행됨. CHANGELOG.md 참조.
