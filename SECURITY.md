# Security Policy

상세 위협 모델: [docs/SECURITY.md](docs/SECURITY.md)

## 지원 버전

| Version | Supported |
|---------|-----------|
| 0.3.x | ✅ |
| 0.2.x | ⚠️ critical fix만 |
| < 0.2 | ❌ |

## 취약점 보고

**GitHub Issue로 보고하지 마세요.** 공개 노출됩니다.

- **이메일**: swxvno0m@gmail.com
- 평균 응답: 72시간 이내
- 비공개 fix 배포 → 공개 disclosure (책임 공개 / Coordinated Disclosure)
- 보고자는 CHANGELOG에 credit (원하실 경우)

## 보안 아키텍처 (요약)

| 레이어 | 보호 |
|---|---|
| **시크릿 관리** | `.env` 파일 (gitignored), Vercel/Supabase env vars. **API 키는 절대 코드/HTML에 hardcode 금지** |
| **인증** | Supabase Auth (이메일+비밀번호, Google OAuth, 매직링크). JWT는 Authorization 헤더 |
| **권한** | Postgres RLS — `purchases`/`profiles`/`usage` 모두 본인 row만 SELECT. INSERT/UPDATE는 service_role(서버)만 |
| **결제** | Stripe Checkout (hosted) — 카드 정보 우리 서버 절대 안 거침. Webhook은 HMAC 서명 검증 |
| **다운로드** | Supabase Storage 'releases' (private) + 24h signed URL. paid 사용자만 발급 |
| **API gateway** | Vercel Functions — JWT 검증 + paid 검증 + IP/user 기반 rate limit (분당 60) |
| **CORS** | `APP_URL` + localhost 화이트리스트. `*` 미사용 |
| **Headers** | HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy strict-origin |
| **자동 검사** | pre-commit gitleaks + GitHub Actions (gitleaks + trufflehog) — push마다 secret leak 검사 |
| **의존성** | Dependabot 주간 — npm/pip/actions 자동 업데이트 PR |

## 알려진 한계 (Out of scope)

- 사용자가 의도적으로 악성 plugin 설치 (`~/.jarvis/plugins/*.py`)
- 사용자가 `.env`를 실수로 commit (gitignore에 명시되어 있음, gitleaks가 자동 검사)
- macOS/Windows 자체 시스템 취약점 (Apple/Microsoft에 직접 보고)
- 사용자 본인 머신의 멀웨어로 인한 토큰 탈취

## 사용자 측 안전 수칙

1. `.env` 파일은 절대 commit하지 말 것 (`.gitignore`에 차단되어 있음)
2. Anthropic API key는 한 번만 발급하고 안전하게 보관
3. Supabase service_role key는 **클라이언트 코드에 절대 넣지 말 것** (anon key만 OK)
4. 의심스러운 plugin/tool은 설치 전 코드 리뷰
5. macOS 마이크/카메라/화면 녹화 권한은 신뢰하는 앱에만 부여

## 자동 보안 검사

```bash
# 로컬에서 push 전 한 번 검사
brew install gitleaks pre-commit
pre-commit install
git commit -m "..."   # 자동 secret scan

# 수동 전체 스캔
gitleaks detect --source . --verbose
```

GitHub Actions: `.github/workflows/secret-scan.yml` — push/PR마다 자동.
