import type { VercelRequest, VercelResponse } from "@vercel/node";
import { createClient } from "@supabase/supabase-js";
import { applyCors } from "./_cors";
import { validateBody, validateBodySize, rateLimit, rateLimitKey } from "./_validate";
import { fetchAnthropicWithRetry, logClaudeUsage, normalizeAnthropicBody } from "./_anthropic";

const supabaseAdmin = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } }
);

async function authenticate(req: VercelRequest, res: VercelResponse) {
  const token = (req.headers.authorization || "").replace(/^Bearer\s+/i, "").trim();
  if (!token) {
    res.status(401).json({ error: "unauthorized" });
    return null;
  }
  const { data: userData, error: userErr } = await supabaseAdmin.auth.getUser(token);
  if (userErr || !userData?.user) {
    res.status(401).json({ error: "unauthorized", detail: userErr?.message });
    return null;
  }
  return userData.user;
}

async function assertPaid(userId: string, res: VercelResponse): Promise<boolean> {
  const { data: purchase } = await supabaseAdmin
    .from("purchases")
    .select("id, status")
    .eq("user_id", userId)
    .eq("status", "paid")
    .limit(1)
    .maybeSingle();
  if (!purchase) {
    res.status(403).json({ error: "not_purchased" });
    return false;
  }
  return true;
}

export default async function handler(req: VercelRequest, res: VercelResponse): Promise<void> {
  if (applyCors(req, res)) return;
  if (req.method !== "POST") {
    res.status(405).json({ error: "method_not_allowed" });
    return;
  }
  if (!validateBodySize(req, res)) return;

  const t0 = Date.now();
  const user = await authenticate(req, res);
  if (!user) return;
  if (!(await assertPaid(user.id, res))) return;

  const userRl = rateLimit(rateLimitKey(req, user.id));
  if (!userRl.ok) {
    res.setHeader("Retry-After", String(userRl.retryAfter));
    res.status(429).json({ error: "rate_limit_exceeded", retry_after: userRl.retryAfter });
    return;
  }

  const validation = validateBody(req.body || {}, {
    model: { type: "string", required: false, maxLength: 100, pattern: /^[a-zA-Z0-9._-]+$/ },
    messages: { type: "array", required: true },
    max_tokens: { type: "number" },
    stream: { type: "boolean" },
  });
  if (!validation.ok) {
    res.status(400).json({ error: validation.error, field: validation.field });
    return;
  }
  if (req.body?.stream === true) {
    res.status(400).json({ error: "use_stream_endpoint", hint: "POST /api/llm/stream" });
    return;
  }

  const body = normalizeAnthropicBody(req.body, false);
  let anthRes: Response;
  try {
    anthRes = await fetchAnthropicWithRetry(body);
  } catch (err) {
    const dt = Date.now() - t0;
    await logClaudeUsage(supabaseAdmin, user.id, body.model, "llm", 502, null, dt, {
      error: err instanceof Error ? err.message : String(err),
      retryable: true,
    });
    res.status(502).json({ error: "upstream_failed", detail: err instanceof Error ? err.message : String(err) });
    return;
  }

  const text = await anthRes.text();
  let json: any = null;
  try { json = JSON.parse(text); } catch {}
  const dt = Date.now() - t0;

  if (anthRes.ok && json) {
    await logClaudeUsage(supabaseAdmin, user.id, body.model, "llm", anthRes.status, json.usage, dt, {
      model_returned: json.model,
      stop_reason: json.stop_reason,
      cached_system: Boolean(body.system),
    });
  } else {
    await logClaudeUsage(supabaseAdmin, user.id, body.model, "llm", anthRes.status, null, dt, {
      error: json?.error?.message || text.slice(0, 500),
    });
  }

  res.status(anthRes.status).setHeader("Content-Type", "application/json").send(json ?? text);
}
