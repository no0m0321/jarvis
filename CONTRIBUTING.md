# Contributing to Jarvis

자비스에 기여해 주셔서 감사합니다.

## 개발 환경

```bash
git clone https://github.com/no0m0321/jarvis.git
cd jarvis
./install.sh   # 또는 수동: python -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

`.env`에 `ANTHROPIC_API_KEY`를 채우고 `jarvis doctor`로 진단 통과 확인.

## 변경 흐름

1. 이슈 먼저 — 큰 변경은 issue 열어 합의 후 PR
2. 브랜치: `feat/<설명>` / `fix/<설명>`
3. 커밋 메시지: [Conventional Commits](https://www.conventionalcommits.org/) 권장
   - `feat: HUD 색상 매핑 추가`
   - `fix: wake word race condition`
   - `docs: README 설치 절차 정정`
   - `BREAKING CHANGE:` 헤더 또는 `!` (e.g. `feat!:`) 는 major bump 트리거

## 검사 (PR 전 로컬에서 모두 통과)

```bash
ruff check src tests
mypy src/jarvis --ignore-missing-imports
pytest -q
```

CI는 macOS 14 + Ubuntu / Python 3.9, 3.11, 3.12에서 같은 검사를 돌립니다.

## 릴리즈 (관리자)

```bash
.venv/bin/cz bump          # 커밋 분석 → 버전 bump + CHANGELOG + tag
git push --follow-tags     # GitHub Actions가 release artifacts 빌드
```

## 코드 스타일

- Python 3.9+ 호환 (CI 매트릭스가 가장 오래된 버전)
- ruff 규칙: E, F, I, N, W, UP, B, SIM (line-length 100)
- 타입 힌트: 새 함수는 모두 type hint
- 한국어 주석 OK — 단, public docstring/error 메시지는 한국어 또는 영어 일관 유지

## 새 도구 (Tool) 추가

`src/jarvis/tools/<name>.py` 작성 후 `REGISTRY.register(...)` 호출. 또는 사용자 plugin은 `~/.jarvis/plugins/example.py` 참고 (`jarvis plugin init`).

## PR 체크리스트

- [ ] ruff/mypy/pytest 통과
- [ ] 새 기능은 test 추가 (`tests/`)
- [ ] 사용자가 보는 변경(CLI/HUD/wake word 등)은 `CHANGELOG.md`에 한 줄 또는 conventional commit으로
- [ ] `~/.jarvis/memory.md` 같은 사용자 데이터를 코드에 하드코딩하지 않음
- [ ] **secret leak 없음** (gitleaks pre-commit 통과 — 아래 §보안)

## 보안 (필수)

기여 전에 이것만은 꼭:

### 1. pre-commit hook 설치
```bash
brew install pre-commit gitleaks
pre-commit install
```
이후 모든 `git commit`이 자동으로 secret scan 통과해야 commit됨.

### 2. 절대 commit 금지 항목
- `.env` 파일 (`.gitignore` 됨, 그래도 주의)
- `ANTHROPIC_API_KEY`, `STRIPE_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY` — 코드/HTML/주석 어디에도 hardcode 금지
- 실제 Supabase project URL이 포함된 anon JWT — `docs/env.js` (gitignored) 또는 Vercel env vars로
- 개인 정보 (이메일, 전화번호 등) — 테스트 코드에도

### 3. 클라이언트 vs 서버 키 구분
- **클라이언트 (브라우저, Jarvis CLI)**: `NEXT_PUBLIC_SUPABASE_ANON_KEY`만 — RLS가 보안 레이어
- **서버 (Vercel Functions)**: `SUPABASE_SERVICE_ROLE_KEY`, `STRIPE_SECRET_KEY`, `ANTHROPIC_API_KEY` — RLS 우회. 클라이언트 노출 0
- 새 도구 추가 시 어느 쪽에서 호출되는지 명확히 (`src/jarvis/tools/`는 로컬 CLI라 사용자 머신에서 실행 — 본인 키)

### 4. 새 API endpoint 추가 시
[`docs/api/`](docs/api/) 안의 기존 패턴 따르기:
1. `applyCors(req, res)` 호출
2. `validateBodySize(req, res)` (POST의 경우)
3. `rateLimit(rateLimitKey(req, userId))` (인증 후)
4. JWT 검증 → paid 검증
5. 입력 `validateBody(body, schema)` 강제

### 5. 취약점 발견 시
GitHub Issue에 올리지 말고 `swxvno0m@gmail.com`로 직접 — [SECURITY.md](SECURITY.md) 참조.
