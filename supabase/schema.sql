-- ────────────────────────────────────────────────────────────────────────
-- 자비스 판매 사이트 — Supabase 스키마
--
-- 사용법:
--   1. Supabase 콘솔 → SQL editor → New query
--   2. 이 파일 전체 붙여넣기 → Run
--   3. Storage → New bucket "releases" (private) → jarvis-v0.3.0.zip 업로드
--
-- 멱등 (재실행 안전) — 이미 존재하는 객체는 skip 또는 replace
-- ────────────────────────────────────────────────────────────────────────

-- ── profiles: auth.users mirror ──────────────────────────────────────────
create table if not exists public.profiles (
  id uuid primary key references auth.users on delete cascade,
  email text,
  created_at timestamptz default now()
);

alter table public.profiles enable row level security;

drop policy if exists "own_profile_select" on public.profiles;
create policy "own_profile_select" on public.profiles
  for select using (auth.uid() = id);


-- ── purchases: 결제 이력 ─────────────────────────────────────────────────
create table if not exists public.purchases (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade not null,
  stripe_session_id text unique,
  stripe_payment_intent text,
  amount_cents int not null,
  currency text default 'usd',
  status text default 'pending',  -- pending | paid | failed | refunded
  product text default 'jarvis-v0.3',
  created_at timestamptz default now(),
  paid_at timestamptz
);

create index if not exists purchases_user_status_idx
  on public.purchases (user_id, status);

alter table public.purchases enable row level security;

-- 본인 결제 이력만 조회 가능
drop policy if exists "own_purchase_select" on public.purchases;
create policy "own_purchase_select" on public.purchases
  for select using (auth.uid() = user_id);

-- 명시적 거부: anon/authenticated는 INSERT/UPDATE/DELETE 불가
-- (service_role은 RLS 우회하므로 서버 함수에서만 가능)
drop policy if exists "no_purchase_insert" on public.purchases;
create policy "no_purchase_insert" on public.purchases
  for insert with check (false);

drop policy if exists "no_purchase_update" on public.purchases;
create policy "no_purchase_update" on public.purchases
  for update using (false);

drop policy if exists "no_purchase_delete" on public.purchases;
create policy "no_purchase_delete" on public.purchases
  for delete using (false);


-- ── auth.users insert 시 profiles 자동 생성 ────────────────────────────
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();


-- ── usage: API 호출 사용량 로그 (v0.5.0) ───────────────────────────────
-- 매 LLM/Vision 호출마다 1 row 기록. 사용자별 모니터링 + 차후 정책 트리거.
create table if not exists public.usage (
  id bigserial primary key,
  user_id uuid references auth.users on delete cascade not null,
  model text not null,                      -- 'claude-opus-4-7', 'claude-haiku-4-5-...' 등
  endpoint text not null,                   -- 'llm' | 'llm_stream' | 'vision'
  input_tokens int default 0,
  output_tokens int default 0,
  cache_read_tokens int default 0,
  cache_create_tokens int default 0,
  cost_cents numeric(10, 4) default 0,      -- 추정 비용 (cents, 4 decimal for fractional)
  duration_ms int,
  status int default 200,                   -- HTTP-like status
  meta jsonb,                               -- 자유 필드 (request_id, error_code 등)
  created_at timestamptz default now()
);

create index if not exists usage_user_created_idx
  on public.usage (user_id, created_at desc);

create index if not exists usage_created_idx
  on public.usage (created_at desc);

alter table public.usage enable row level security;

drop policy if exists "own_usage_select" on public.usage;
create policy "own_usage_select" on public.usage
  for select using (auth.uid() = user_id);

-- 명시적 거부: anon/authenticated는 INSERT/UPDATE/DELETE 불가 (service_role만)
drop policy if exists "no_usage_insert" on public.usage;
create policy "no_usage_insert" on public.usage
  for insert with check (false);

drop policy if exists "no_usage_update" on public.usage;
create policy "no_usage_update" on public.usage
  for update using (false);


-- ── 검증 쿼리 (실행 후 확인) ───────────────────────────────────────────
-- select * from public.purchases;       -- 비어있어야 정상
-- select * from public.profiles;        -- 가입 사용자가 있다면 mirror
-- select count(*) from auth.users;      -- 가입 수
-- select sum(cost_cents)/100 as usd, count(*) as calls
--   from public.usage where created_at > now() - interval '7 days';  -- 주간 집계
