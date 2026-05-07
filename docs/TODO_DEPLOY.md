# 자비스 v0.4.0 — 사용자 콘솔 작업 가이드

이 문서는 **사용자가 직접 해야 하는 콘솔 작업**만 모은 체크리스트입니다.
Claude가 작성한 코드는 모두 준비됐고, 아래 순서로 외부 서비스 연결만 하면 즉시 작동합니다.

순서: **Supabase → Stripe → Vercel → 검증**.

---

## 1. Supabase (15분)

### 1-A. 프로젝트 사용 결정
- 기존 Supabase 프로젝트 그대로 사용 가능 (URL/키 손에 있다면)
- 또는 자비스 전용 신규 프로젝트 생성 (https://app.supabase.com → New project)
- 기존을 쓸 거면 다음 단계로 바로

### 1-B. SQL 스키마 적용
1. Supabase 콘솔 → 좌측 메뉴 **SQL Editor** → "New query"
2. `/Users/swxvno/jarvis/supabase/schema.sql` 파일 내용 전체 복사 → 붙여넣기 → **Run**
3. 정상 실행 메시지 (Success. No rows returned) 확인
4. 좌측 **Table Editor** → `purchases`, `profiles` 두 테이블 보이는지 확인

### 1-C. Storage 버킷 생성
1. 좌측 **Storage** → "New bucket" → 이름 `releases` → **Public bucket OFF** (private 필수) → Create
2. 생성된 버킷 클릭 → "Upload file" → `/Users/swxvno/jarvis-v0.3.0.zip` 업로드
3. 업로드 후 파일명이 `jarvis-v0.3.0.zip` 그대로인지 확인 (`api/download.ts`에 하드코딩됨)

### 1-D. API 키 3개 복사
콘솔 → **Project Settings → API**:
- [ ] **Project URL**: `https://xxxxxx.supabase.co` 형태
- [ ] **anon public** key: `eyJhbG...` 형태 (브라우저 노출 OK)
- [ ] **service_role** key: `eyJhbG...` 형태 (**절대 client 노출 금지** — 서버 함수만)

### 1-E. (옵션) 이메일 확인 끄기
- 콘솔 → **Authentication → Providers → Email** → "Confirm email" 토글 **OFF**
- ON이면 가입 후 이메일 확인 클릭해야 로그인됨. 데모용으로는 OFF가 빠름

### 1-F. URL Configuration (배포 후 다시 채울 것)
- 콘솔 → **Authentication → URL Configuration**
- Site URL은 일단 `http://localhost:3000` 그대로
- Redirect URLs는 Vercel 배포 후 채울 예정 (3-D에서)

---

## 2. Stripe (10분)

### 2-A. 계정 + Test 모드
1. https://dashboard.stripe.com → 가입 또는 로그인
2. 좌측 상단 **Test mode** 토글 ON (right side에 "Viewing test data" 표시)

### 2-B. 상품 + 가격 생성
1. **Products** → "+ Add product"
2. Name: `Jarvis v0.3 Source`
3. Description: `한국어 우선 macOS 음성 비서 — 일회성 구매` (선택)
4. Pricing model: **One-time**
5. Price: **$6.00 USD**
6. Save product
7. 생성된 상품 → Pricing 섹션의 **Price ID** 복사 (`price_xxxxxxxxxxxx` 형태)
   - [ ] STRIPE_PRICE_ID: `price_...`

### 2-C. Secret API Key
1. **Developers → API keys**
2. **Secret key** 옆 "Reveal test key" → 복사 (`sk_test_...` 형태)
   - [ ] STRIPE_SECRET_KEY: `sk_test_...`

### 2-D. Webhook (배포 후 진행 — 일단 skip)
Vercel 배포 URL이 있어야 webhook endpoint를 등록할 수 있음. 3-D 에서 진행.

---

## 3. Vercel (15분)

### 3-A. 프로젝트 임포트
1. https://vercel.com → "Add New" → "Project"
2. GitHub 연결 → `no0m0321/jarvis` repo 선택 → Import
3. **중요 설정**:
   - **Framework Preset**: `Other` (Next.js 아님)
   - **Root Directory**: `docs/` ⭐ (자비스 repo 루트가 아닌 docs/)
   - Build Command: 비움 (또는 `echo skip`)
   - Output Directory: `.` (또는 비움)
   - Install Command: `npm install` (자동)

### 3-B. 환경변수 입력 (가장 중요)
"Environment Variables" 섹션 → 아래 8개 추가 (모두 Production + Preview + Development 적용):

| Name | 값 | 출처 |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://xxx.supabase.co` | 1-D |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `eyJhbG...` | 1-D |
| `SUPABASE_URL` | `https://xxx.supabase.co` (위와 동일) | 1-D |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJhbG...` | 1-D (service_role) |
| `STRIPE_SECRET_KEY` | `sk_test_...` | 2-C |
| `STRIPE_WEBHOOK_SECRET` | (3-D 후 채움) | 3-D |
| `STRIPE_PRICE_ID` | `price_...` | 2-B |
| `APP_URL` | (Deploy 후 채움, 예: `https://jarvis-xxx.vercel.app`) | 3-C |

> 일단 STRIPE_WEBHOOK_SECRET 과 APP_URL 은 비워두고 Deploy → URL 받은 후 다시 입력.

### 3-C. Deploy
1. **Deploy** 클릭 → 1~2분 후 URL 확보 (예: `https://jarvis-no0m.vercel.app`)
2. 환경변수 페이지로 돌아가 `APP_URL` 채우기
3. **Redeploy** 클릭 (환경변수 반영)

### 3-D. Stripe Webhook 등록 + secret 받기
이제 Vercel URL이 있으니 Stripe webhook 설정:

1. Stripe 콘솔 → **Developers → Webhooks** → "+ Add endpoint"
2. **Endpoint URL**: `https://<Vercel-URL>/api/webhook`
3. **Events to send**: 다음 3개 선택
   - [x] `checkout.session.completed`
   - [x] `checkout.session.expired`
   - [x] `checkout.session.async_payment_failed`
4. Add endpoint
5. 생성된 endpoint 클릭 → "Signing secret" → "Reveal" → 복사 (`whsec_...`)
6. Vercel 환경변수 → `STRIPE_WEBHOOK_SECRET`에 붙여넣기 → **Redeploy**

### 3-E. Supabase Redirect URLs (Vercel URL 등록)
Supabase 콘솔 → **Authentication → URL Configuration**:
- **Site URL**: `https://<Vercel-URL>` (예: `https://jarvis-no0m.vercel.app`)
- **Redirect URLs**: 한 줄에 하나씩 입력:
  ```
  https://<Vercel-URL>/**
  https://<Vercel-URL>/login.html
  https://<Vercel-URL>/success.html
  http://localhost:3000/**
  ```

### 3-F. env.js 자동 생성 (이미 셋업됨, 추가 작업 없음)

`vercel.json`의 `buildCommand: "node build-env.js"`가 매 deploy마다 자동 실행되어
Vercel 환경변수 `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`를 읽고 `env.js`를 만들어줍니다.

`docs/env.js` 파일은 `.gitignore`에 차단되어 있어 commit되지 않습니다 — Vercel build에서만 생성.

**확인 방법**: Vercel deploy 로그에서:
```
> node build-env.js
OK: env.js 생성됨 (XXX bytes) — URL ✓ · KEY ✓ (208자)
```
이 줄이 안 보이면 환경변수 누락이거나 build 실패. Vercel project settings → Environment Variables 다시 확인.

**로컬 테스트** (선택): 이미 `docs/env.js`가 직접 작성돼 있어 그대로 사용 가능. dev server에서 즉시 작동:
```bash
cd /Users/swxvno/jarvis/docs
python3 -m http.server 8001
# http://localhost:8001/login.html
```

---

## 4. 검증 (10분)

### 4-A. 페이지 접속
1. `https://<Vercel-URL>/` → 헤더에 "로그인" 표시
2. CTA 버튼 텍스트가 `로그인 후 구매 · $6` 인지 확인

### 4-B. 회원가입 → 로그인
1. "로그인" 클릭 → `/login.html`
2. 이메일 + 비밀번호 (8자+) → "가입하기"
3. 헤더 우측에 이메일 + 녹색 dot 표시

### 4-C. 결제 흐름
1. 메인 페이지로 → CTA 버튼이 `BUY · $6 · GET SOURCE`
2. 클릭 → Stripe Checkout 페이지로 이동
3. **테스트 카드**: `4242 4242 4242 4242` / 만료 임의 미래 / CVC 임의 / ZIP 임의
4. 결제 → `/success.html?session_id=cs_test_...`로 redirect
5. 5~10초 내 polling 통과 → "PAID" 상태
6. 1.5초 후 `/?paid=1`로 자동 redirect → 녹색 배너 4초 표시

### 4-D. Webhook 확인
- Stripe 콘솔 → **Developers → Webhooks** → 등록한 endpoint → "Recent events"
- `checkout.session.completed` 이벤트가 **200 OK** 응답인지 확인
- 4xx/5xx면 환경변수 누락이거나 webhook secret 불일치

### 4-E. Supabase DB 확인
- Supabase 콘솔 → **Table Editor → purchases**
- 방금 결제한 row가 `status='paid'`, `paid_at` 채워져 있는지

### 4-F. 다운로드 흐름
1. 메인 페이지 → CTA 버튼이 `DOWNLOAD JARVIS v0.3.0` (녹색)
2. 클릭 → 24h signed URL 발급 → 자동 redirect → `jarvis-v0.3.0.zip` 다운로드 시작
3. 116KB zip 파일 수신 확인

### 4-G. 보안 회귀 검증 (선택, 권장)
- 시크릿 창에서 `/api/download` 직접 호출 → `401 unauthorized` 응답 확인
- 다른 새 계정으로 가입 → CTA가 `BUY` 상태 확인 (다른 user의 결제로는 다운로드 불가)

---

## 5. Live 모드 전환 (실 카드 결제용 — 출시 시점)

> 위 1~4까지는 **Test 모드**. 실제 돈 받으려면:

1. Stripe 콘솔 우측 상단 **Test mode** 토글 OFF → Live mode
2. 2-A~2-C 동일하게 Live 모드에서 상품 + price + secret key 다시 생성
3. 3-D 동일하게 Live mode에서 webhook endpoint 다시 등록 → 새 `whsec_...`
4. Vercel 환경변수에서 `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID` 모두 Live 값으로 교체
5. Redeploy
6. **본인 카드로 1회 실 결제 → 환불 처리** (콘솔에서 Refund 버튼) → 전 흐름 검증

---

## 트러블슈팅

### CTA 버튼이 계속 "확인 중…" 상태
- `env.js` 파일이 없거나 SUPABASE_URL/ANON_KEY가 비어있음
- 브라우저 개발자도구 Console에서 `window.SUPABASE_URL` 확인
- Network 탭에서 supabase.co로 요청 가는지 확인

### "checkout failed (401)" 에러
- 로그인 세션 만료. 로그아웃 → 다시 로그인
- 또는 service_role key 잘못 입력 → Vercel env 확인

### Webhook 이벤트가 4xx로 실패
- Vercel 환경변수 `STRIPE_WEBHOOK_SECRET` 확인 (Live/Test 모드 헷갈리지 마세요)
- Vercel Function logs (`/api/webhook` 클릭 → Logs 탭)에서 정확한 에러 확인

### 결제는 됐는데 status가 paid로 안 바뀜
- Webhook 이벤트가 실패 중. 위 항목 확인
- 임시 해결: Supabase Table editor에서 직접 `status='paid'`로 변경 → 결제는 정상

### Download 시 "object not found"
- Storage 버킷 이름이 정확히 `releases`인지
- 파일명이 정확히 `jarvis-v0.3.0.zip`인지 (대소문자, 점, 하이픈)

### 다른 도메인에서 OAuth redirect 실패
- Supabase URL Configuration의 Redirect URLs에 해당 도메인 추가 필요

---

## 비용 예측 (Test 1000회 + Live 100회 가정)

| 항목 | 비용 |
|---|---|
| Vercel Hobby (무료) | $0 (월 100GB · 함수 100k req) |
| Supabase Free (무료) | $0 (DB 500MB · Storage 1GB · MAU 50k) |
| Stripe 수수료 | 결제당 2.9% + $0.30 → $6 결제당 약 $0.47 |
| Anthropic API | 자비스 본체 사용량 (사이트와 별개) |

100건 결제 시 매출 $600 → Stripe 수수료 약 $47 → 순수익 약 $553. Vercel/Supabase 무료 한도 충분.
