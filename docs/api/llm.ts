/**
 * POST /api/llm
 *
 * Anthropic Messages API 프록시.
 * 사용자가 본인 ANTHROPIC_API_KEY를 가지지 않고도 자비스를 쓰게 함.
 *
 * Headers:
 *   Authorization: Bearer <supabase-jwt>
 *   Content-Type: application/json
 *
 * Body: Anthropic Messages API와 동일 (model, messages, system, tools, max_tokens, ...)
 *   - 단, stream=true는 /api/llm/stream에서 처리 (이 endpoint는 비스트리밍만)
 *
 * Response:
 *   200 — Anthropic 응답 그대로 (Message object)
 *   401 — 인증 실패
 *   403 — paid 결제 안 함
 *   429 — rate limit (장차)
 *   5xx — Anthropic 또는 자체 에러
 *
 * 부수효과:
 *   - usage 테이블에 호출 1건 기록 (모델/토큰/비용)
 */
import type { VercelRequest, VercelResponse } from "@vercel/node";
import { createClient } from "@supabase/supabase-js";
import { applyCors } from "./_cors";
import { validateBody, validateBodySize, rateLimit, rateLimitKey } from "./_validate";

const supabaseAdmin = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } }
);

const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY!;
const ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages";
const ANTHROPIC_VERSION = "2023-06-01";
const ANTHROPIC_BETA = "prompt-caching-2024-07-31"; // 캐시 사용

// 모델별 가격 (per million tokens, USD) — 2026 기준 추정
const PRICING: Record<string, { input: number; output: number; cacheRead: number; cacheCreate: number }> = {
  "claude-opus-4-7":           { input: 15.00, output: 75.00, cacheRead: 1.50, cacheCreate: 18.75 },
  "claude-sonnet-4-6":         { input:  3.00, output: 15.00, cacheRead: 0.30, cacheCreate:  3.75 },
  "claude-haiku-4-5-20251001": { input:  0.80, output:  4.00, cacheRead: 0.08, cacheCreate:  1.00 },
};

function estimateCostCents(model: string, usage: any): number {
  const p = PRICING[model] || PRICING["claude-opus-4-7"];
  const inT = usage?.input_tokens ?? 0;
  const outT = usage?.output_tokens ?? 0;
  const cacheR = usage?.cache_read_input_tokens ?? 0;
  const cacheC = usage?.cache_creation_input_tokens ?? 0;
  // dollars * 100 = cents
  const usd =
    (inT * p.input +
      outT * p.output +
      cacheR * p.cacheRead +
      cacheC * p.cacheCreate) /
    1_000_000;
  return Math.round(usd * 100 * 10000) / 10000; // 4 decimal cents
}

async function logUsage(
  userId: string,
  model: string,
  endpoint: string,
  status: number,
  usage: any,
  durationMs: number,
  meta?: Record<string, unknown>
): Promise<void> {
  try {
    await supabaseAdmin.from("usage").insert({
      user_id: userId,
      model,
      endpoint,
      input_tokens: usage?.input_tokens ?? 0,
      output_tokens: usage?.output_tokens ?? 0,
      cache_read_tokens: usage?.cache_read_input_tokens ?? 0,
      cache_create_tokens: usage?.cache_creation_input_tokens ?? 0,
      cost_cents: estimateCostCents(model, usage),
      duration_ms: durationMs,
      status,
      meta: meta ?? null,
    });
  } catch (err) {
    console.error("[llm] usage log failed:", err);
  }
}

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (applyCors(req, res)) return;
  if (req.method !== "POST") {
    res.status(405).json({ error: "method_not_allowed" });
    return;
  }
  if (!validateBodySize(req, res)) return;

  const t0 = Date.now();

  // ── 1. Auth ─────────────────────────────────────────────
  const token = (req.headers.authorization || "")
    .replace(/^Bearer\s+/i, "")
    .trim();
  if (!token) {
    res.status(401).json({ error: "unauthorized" });
    return;
  }

  const { data: userData, error: userErr } = await supabaseAdmin.auth.getUser(
    token
  );
  if (userErr || !userData?.user) {
    res.status(401).json({ error: "unauthorized", detail: userErr?.message });
    return;
  }
  const user = userData.user;

  // ── 2. paid 결제 검증 ──────────────────────────────────
  const { data: purchase } = await supabaseAdmin
    .from("purchases")
    .select("id, status")
    .eq("user_id", user.id)
    .eq("status", "paid")
    .limit(1)
    .maybeSingle();

  if (!purchase) {
    res.status(403).json({ error: "not_purchased" });
    return;
  }

  // ── 2.5. User-level rate limit (paid 사용자별) ──────────
  const userRl = rateLimit(rateLimitKey(req, user.id));
  if (!userRl.ok) {
    res.setHeader("Retry-After", String(userRl.retryAfter));
    res.status(429).json({ error: "rate_limit_exceeded", retry_after: userRl.retryAfter });
    return;
  }

  // ── 3. Body 검증 ─────────────────────────────────────────
  const body = req.body || {};
  const validation = validateBody(body, {
    model: { type: "string", required: true, maxLength: 100, pattern: /^[a-zA-Z0-9._-]+$/ },
    messages: { type: "array", required: true },
    system: { type: "string", maxLength: 64 * 1024 },
    max_tokens: { type: "number" },
    stream: { type: "boolean" },
  });
  if (!validation.ok) {
    res.status(400).json({ error: validation.error, field: validation.field });
    return;
  }
  if (body.stream === true) {
    res.status(400).json({ error: "use_stream_endpoint", hint: "POST /api/llm/stream" });
    return;
  }

  // ── 4. Anthropic 호출 (프록시) ─────────────────────────
  let anthRes: Response;
  try {
    anthRes = await fetch(ANTHROPIC_API_URL, {
      method: "POST",
      headers: {
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
        "anthropic-beta": ANTHROPIC_BETA,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
  } catch (err) {
    const dt = Date.now() - t0;
    console.error("[llm] fetch error:", err);
    await logUsage(user.id, body.model, "llm", 500, null, dt, {
      error: err instanceof Error ? err.message : String(err),
    });
    res.status(502).json({
      error: "upstream_failed",
      detail: err instanceof Error ? err.message : String(err),
    });
    return;
  }

  const text = await anthRes.text();
  let json: any = null;
  try {
    json = JSON.parse(text);
  } catch {
    // 파싱 실패시 그대로 전달
  }

  const dt = Date.now() - t0;

  // ── 5. usage 기록 + 응답 전달 ────────────────────────────
  if (anthRes.ok && json) {
    await logUsage(user.id, body.model, "llm", anthRes.status, json.usage, dt, {
      model_returned: json.model,
      stop_reason: json.stop_reason,
    });
  } else {
    await logUsage(user.id, body.model, "llm", anthRes.status, null, dt, {
      error: json?.error?.message || text.slice(0, 500),
    });
  }

  res
    .status(anthRes.status)
    .setHeader("Content-Type", "application/json")
    .send(json ?? text);
}
