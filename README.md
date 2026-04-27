# 자비스 (JARVIS)

> "I am inevitable... ly online to assist you."

승우의 개인 AI 비서. Claude 기반, 자율 실행 지향, 한국어 우선.

## 빠른 시작

```bash
# 1. 의존성 설치 (uv 권장)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 2. 환경 설정
cp .env.example .env
# .env 열어서 ANTHROPIC_API_KEY 채우기

# 3. 실행
jarvis chat                    # 인터랙티브 대화
jarvis ask "오늘 할 일 정리해줘"   # 단발성 질문
jarvis --help                  # 명령어 목록
```

## 구조

```
src/jarvis/
├── cli.py          # Typer 진입점 (chat, ask, ...)
├── assistant.py    # Claude 호출 + 시스템 프롬프트 (prompt caching 적용)
├── config.py       # pydantic-settings 환경변수 로더
└── tools/          # 외부 도구 통합 자리 (캘린더, 메일, 셸 등)
```

## 설계 원칙

1. **Absolute Autonomy** — 불필요한 허락 요청 없음
2. **Prompt Caching** — 시스템 프롬프트는 ephemeral 캐시
3. **확장성** — `tools/` 디렉토리에 도구 모듈 추가만으로 능력 확장
4. **로컬 우선** — 데이터는 `~/.jarvis/` 로컬 저장 (추후)

## 개발

```bash
ruff check src tests
mypy src
pytest
```
