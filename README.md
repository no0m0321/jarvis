# 자비스 (JARVIS) v0.3.1

[![CI](https://github.com/no0m0321/jarvis/actions/workflows/ci.yml/badge.svg)](https://github.com/no0m0321/jarvis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

> Voice-first personal AI assistant — Claude-powered, autonomous, holographic HUD

macOS 네이티브 개인 AI 비서. 한국어 우선, "자비스" wake word 음성 대화 + **296개 도구**를 통한 실제 시스템 동작 + 시네마틱 데스크톱 HUD + plugin/config 시스템.

📐 [아키텍처](docs/ARCHITECTURE.md) · 🔒 [보안 노트](docs/SECURITY.md) · 🤝 [기여](CONTRIBUTING.md) · 📜 [LICENSE (MIT)](LICENSE)

## 시연

```bash
# wake word 대기 — "자비스 ~~ 해줘" 발화 시 자동 실행
.venv/bin/jarvis daemon install --no-chime --debug

# 단발 명령
.venv/bin/jarvis listen
.venv/bin/jarvis ask "오늘 할 일 정리"
.venv/bin/jarvis do "~/Documents 디렉토리 정리해서 메모해줘"

# CLI 단축
.venv/bin/jarvis note "내일 회의 9시"
.venv/bin/jarvis timer 5 -m "물 마실 시간"
.venv/bin/jarvis memory --add "나는 미니멀 디자인 선호"
```

## 빠른 시작 — 한 줄 설치

```bash
curl -fsSL https://raw.githubusercontent.com/no0m0321/jarvis/main/install.sh | bash
```

또는 수동:

```bash
git clone https://github.com/no0m0321/jarvis.git && cd jarvis
./install.sh
```

설치 후:

```bash
jarvis init             # 첫 실행 마법사 — API 키 / 호칭 / 메모 템플릿
jarvis permissions      # macOS 자동화 권한 다이얼로그 일괄 트리거
jarvis doctor           # API 키 / 마이크 / 의존성 / launchd / HUD 진단
jarvis daemon install   # wake daemon 백그라운드 등록
```

## 구조

```
src/jarvis/
├── cli.py            # Typer 진입점 (version/ask/chat/do/listen/voice/wake/note/timer/memory/update + daemon/hud 서브커맨드)
├── agent.py          # Tool use agentic loop (Claude Opus 4.7)
├── assistant.py      # 단발/스트리밍 LLM 호출 (prompt caching)
├── persona.py        # 4종 system prompt (jarvis/casual/formal/creative)
├── config.py         # pydantic-settings + .env 로더 (ANTHROPIC_API_KEY 우회 패턴)
├── history.py        # ~/.jarvis/history.jsonl 영구 저장
├── hud.py            # ~/Library/Caches/jarvis-hud.json 상태 + 음성 RMS streaming + 사운드 효과
├── daemon.py         # launchd plist + bootstrap/bootout
├── health_server.py  # :41417 HTTP /healthz /metrics /tools /history
├── voice/
│   ├── recorder.py     # 마이크 녹음 (capture_phrase, record_until_silence)
│   ├── transcribe.py   # faster-whisper STT (initial_prompt 기반 정확도 향상)
│   └── wake.py         # wake word 매칭 + listen_for_wake 무한 루프
└── tools/            # 30개 client-side tools — agent이 자동 사용
    ├── shell.py            # run_shell
    ├── fs.py               # read/write/list/search files
    ├── web.py              # fetch_url
    ├── macos.py            # notify, say (Reed/Yuna), open_url
    ├── macos_extra.py      # calendar_add/list_today, screen_capture, clipboard
    ├── macos_more.py       # mail_compose, spotlight_search, activate_app, play_sound
    └── macos_extras2.py    # music_control, set_volume, set_brightness, reminder_add,
                            # note_search/list, battery_info, wifi_info, bookmark_add,
                            # top_processes, system_action(sleep/lock/screensaver)
```

## 핵심 기능

| 기능 | 설명 |
|---|---|
| **Wake word** | "자비스" 부르면 daemon이 자동 listen → Claude 호출 → TTS 답변 |
| **Tool use agentic loop** | 30개 도구를 LLM이 자율 호출 (다회 turn) |
| **Web search** | Anthropic server-side `web_search` tool |
| **Persistent memory** | `~/.jarvis/memory.md` 가 시스템 프롬프트에 자동 첨부 |
| **History** | `~/.jarvis/history.jsonl` append-only, `jarvis hud history`로 조회 |
| **Holographic HUD** | Übersicht widget, voice-reactive 80-particle 3D cloud |
| **Premium TTS** | Reed (남성, 자비스 톤) 기본. `JARVIS_VOICE` env로 변경 |
| **Multi-persona** | jarvis / casual / formal / creative — `JARVIS_PERSONA` env |
| **Health server** | `:41417/healthz` `/metrics` `/tools` `/history` |
| **launchd daemon** | RunAtLoad + KeepAlive, macOS 부팅 시 자동 시작 |

## HUD v6 시각 효과 (30+)

- 80개 particle 3D cloud (voice-reactive scale + push)
- Wake-time auto-zoom (1.0 → 1.18) + glow surge
- 8 keyframe 애니메이션 (shake, pulse, float, edge-pulse, shimmer, spin, blink, flash)
- Hexagonal grid + perspective grid floor (sci-fi sweep)
- Code rain (양쪽 gutter)
- Particle explosion burst on wake
- Voice peak flash overlay
- Voice waveform 32-bar
- CPU/MEM SVG sparkline (60s history)
- Glitch text on header during analyzing
- Day/night palette (시간대별 idle accent)
- 4상태 color theme (cyan / amber / gold / day-night)
- Corner brackets, scanlines, gradient mesh
- Dynamic shimmer overlay
- Multi-layer 3D depth (translateZ)

## CLI 전체

```
jarvis init              # 첫 실행 마법사 (API 키 / 호칭 / 메모)
jarvis doctor            # 진단 (API 키 / 마이크 / 의존성 / launchd / HUD)
jarvis permissions       # macOS 자동화 권한 일괄 트리거
jarvis version
jarvis ask <prompt> [--fast]
jarvis chat
jarvis do <task> [--max-turns N] [-q]
jarvis listen [--model M] [--lang L]
jarvis voice
jarvis wake [--no-chime] [--detect-model M] [--word <extra>]
jarvis note <text>
jarvis timer <minutes> [-m message]
jarvis memory [--show|--add|--edit|--clear]
jarvis update
jarvis daemon {install|uninstall|status|restart|logs}
jarvis hud {start|stop|state|history}
jarvis plugin {init|list|reload}
```

## 도구 (49종)

**파일/시스템**: shell · read_file · write_file · list_dir · search_files · file_info · hash_file
**Web/네트워크**: fetch_url · web_search (server) · network_test · ip_info · port_check · wifi_info
**macOS UI**: notify · say · open_url · activate_app · play_sound · screen_capture · system_action
**클립보드/메모**: clipboard_read · clipboard_write · note_search · note_list · bookmark_add
**Apps**: calendar_add · calendar_list_today · reminder_add · mail_compose · spotlight_search · music_control
**디바이스**: set_volume · get_volume · set_brightness · battery_info · top_processes
**유틸**: now · whoami · jarvis_status · env_get · calc · json_format · json_extract · base64_encode/decode · url_encode/decode
**Git**: git_status · git_log · git_diff

## 플러그인 시스템

`~/.jarvis/plugins/*.py` 자동 import. 각 plugin은 `register()` 콜백 또는 module-level에서 `REGISTRY.register(Tool(...))`.

```bash
jarvis plugin init                              # ~/.jarvis/plugins/example.py 템플릿
jarvis plugin install https://github.com/user/repo   # GitHub repo에서 plugin.py 자동 감지
jarvis plugin install https://example.com/x.py       # 직접 URL
jarvis plugin list                              # 등록된 plugin 목록
jarvis plugin remove <name>                     # 제거
jarvis plugin reload                            # 강제 재로드
```

⚠ 플러그인은 임의 Python 코드 실행. 신뢰하는 source만 설치.

## Vector Memory (선택)

`pip install 'jarvis-voice[memory]'` 로 chromadb 활성화. LLM이 자동으로 사용:

- `memory_save("주인님은 미니멀 디자인 선호")` — 영구 저장
- `memory_recall("디자인 취향")` — 의미 검색

저장 위치: `~/.jarvis/vectorstore/`

## LLM Provider 전환

```bash
# OpenAI
export JARVIS_PROVIDER=openai
export OPENAI_API_KEY=sk-...
jarvis ask "안녕"

# 로컬 Ollama
export JARVIS_PROVIDER=ollama
export JARVIS_MODEL=llama3.2
jarvis ask "안녕"
```

⚠ wake daemon과 `jarvis do` (도구 use)는 Anthropic 권장 — 다른 provider는 chat-only.

## Web Dashboard

Daemon 실행 중이면 [http://localhost:41418/](http://localhost:41418/) 에서 실시간 상태/도구/히스토리 모니터링 가능.

## Docker (Headless)

```bash
docker build -t jarvis-voice:latest .
docker run --rm -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY jarvis-voice:latest ask "안녕"
```

음성/HUD 없이 `jarvis ask` `jarvis do` `jarvis chat` 만 사용 가능.

## 사용자 설정

`~/.jarvis/config.toml` — JARVIS_* env vars로 export (env가 우선):

```toml
voice = "Reed"        # TTS voice
persona = "jarvis"    # jarvis|casual|formal|creative
hud_sounds = true     # sci-fi 사운드
wake_debug = false    # wake 이벤트 stderr 로그
health_port = 41418
```

```bash
jarvis config --init     # 기본 config 생성
jarvis config --show     # 현재 설정 조회
jarvis config --edit     # $EDITOR로 편집
```

## 환경 변수

| Var | Default | 효과 |
|---|---|---|
| `ANTHROPIC_API_KEY` | (필수) | Claude API |
| `JARVIS_OWNER_NAME` | `주인님` | 사용자 호칭 (예: "민지님", "Boss") |
| `JARVIS_WAKE_WORD` | (없음) | 추가 wake word (쉼표 구분, 기본 변종에 더해짐) |
| `JARVIS_VOICE` | `Reed` | TTS voice (Yuna/Eddy/Sandy 등) |
| `JARVIS_PERSONA` | `jarvis` | system prompt 모드 |
| `JARVIS_HUD_SOUNDS` | `1` | 0이면 sci-fi 사운드 끔 |
| `JARVIS_WAKE_DEBUG` | `0` | 1이면 stderr에 wake 이벤트 로그 |
| `JARVIS_HEALTH_PORT` | `41417` | health server 포트 |
| `JARVIS_HISTORY_PATH` | `~/.jarvis/history.jsonl` | history 파일 위치 |
| `JARVIS_HOVER_GATE` | `1` | 0이면 hover 없이도 mic 항상 listening |
| `JARVIS_PROVIDER` | `anthropic` | LLM provider — `anthropic` / `openai` / `ollama` |
| `OPENAI_API_KEY` | (옵션) | `JARVIS_PROVIDER=openai` 시 |
| `OLLAMA_HOST` | `http://localhost:11434` | `JARVIS_PROVIDER=ollama` 시 |

## 검증

```bash
.venv/bin/pytest -q          # 36 passing
.venv/bin/jarvis daemon status
curl http://127.0.0.1:41417/healthz
```

## 라이선스

[MIT](LICENSE) — 자유 활용·수정·재배포 가능. credit 유지 필요.

## 기여

[CONTRIBUTING.md](CONTRIBUTING.md) 참고. PR 환영. 코드 기준: ruff + mypy + pytest 통과.

## 보안

> **사용자 주의**: `.env`/`docs/env.js`/`landing/env.js`는 절대 commit하지 말 것 (`.gitignore`에 차단). API 키는 코드/HTML에 hardcode하지 말고 환경변수만 사용.

| 영역 | 보호 |
|---|---|
| **시크릿** | `.env` gitignored. pre-commit `gitleaks` + GitHub Actions 자동 검사 |
| **인증** | Supabase Auth (이메일/Google/매직링크) + JWT |
| **권한** | Postgres RLS — 본인 row만 SELECT. INSERT/UPDATE는 서버(service_role)만 |
| **결제** | Stripe Checkout (카드정보 우리 서버 0 거침) + Webhook HMAC 서명 검증 |
| **다운로드** | Supabase Storage private 버킷 + 24h signed URL (paid 사용자만) |
| **API** | JWT + paid 검증 + IP/사용자 rate limit (분당 60) + CORS 화이트리스트 |
| **Headers** | HSTS, X-Frame-Options DENY, Permissions-Policy |
| **의존성** | Dependabot 주간 자동 업데이트 PR |

```bash
# 보안 자동 검사 활성화 (개발자)
brew install pre-commit gitleaks
pre-commit install
```

취약점 발견 시 GitHub issue 대신 [SECURITY.md](SECURITY.md) 참고하여 비공개 보고 부탁 (swxvno0m@gmail.com).

---

Made with ◈ + Claude Opus 4.7
