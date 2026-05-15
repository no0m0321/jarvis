import type { VercelRequest, VercelResponse } from "@vercel/node";
import { createClient } from "@supabase/supabase-js";
import { applyCors } from "../_cors";
import { validateBody, validateBodySize, rateLimit, rateLimitKey } from "../_validate";
import { fetchAnthropicWithRetry, logClaudeUsage, normalizeAnthropicBody } from "../_anthropic";

export const config = { api: { bodyParser: true, responseLimit: false } };

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
    .select("id")
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

  const body = normalizeAnthropicBody(req.body, true);
  let upstream: Response;
  try {
    upstream = await fetchAnthropicWithRetry(body);
  } catch (err) {
    await logClaudeUsage(supabaseAdmin, user.id, body.model, "llm_stream", 502, null, Date.now() - t0, {
      error: err instanceof Error ? err.message : String(err),
      retryable: true,
    });
    res.status(502).json({ error: "upstream_failed", detail: err instanceof Error ? err.message : String(err) });
    return;
  }

  if (!upstream.ok || !upstream.body) {
    const errText = await upstream.text();
    await logClaudeUsage(supabaseAdmin, user.id, body.model, "llm_stream", upstream.status, null, Date.now() - t0, {
      error: errText.slice(0, 500),
    });
    res.status(upstream.status).send(errText);
    return;
  }

  res.setHeader("Content-Type", "text/event-stream; charset=utf-8");
  res.setHeader("Cache-Control", "no-cache, no-transform");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");
  res.flushHeaders?.();

  const reader = upstream.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let accumulatedUsage: any = null;
  let finalStatus = 200;
  let eventCount = 0;

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      res.write(chunk);
      eventCount += 1;

      buffer += chunk;
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";
      for (const ev of events) {
        for (const line of ev.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6).trim();
          if (!data || data === "[DONE]") continue;
          try {
            const obj = JSON.parse(data);
            if (obj.type === "message_start" && obj.message?.usage) accumulatedUsage = { ...obj.message.usage };
            if (obj.type === "message_delta" && obj.usage) accumulatedUsage = { ...(accumulatedUsage || {}), ...obj.usage };
            if (obj.type === "error") finalStatus = 500;
          } catch {}
        }
      }
    }
  } catch (err) {
    finalStatus = 499;
    console.error("[llm/stream] stream error:", err);
  } finally {
    res.end();
    await logClaudeUsage(supabaseAdmin, user.id, body.model, "llm_stream", finalStatus, accumulatedUsage, Date.now() - t0, {
      events: eventCount,
      cached_system: Boolean(body.system),
    });
  }
}
