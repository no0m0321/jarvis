/**
 * POST /api/llm/stream
 *
 * Anthropic Messages 스트리밍 프록시 (SSE).
 * stream=true 강제. 응답은 그대로 SSE로 클라이언트에 전달.
 *
 * Headers:
 *   Authorization: Bearer <supabase-jwt>
 *
 * Body: Anthropic Messages API와 동일 (stream은 자동 true)
 *
 * Response: text/event-stream (SSE) — Anthropic 이벤트 그대로
 *
 * usage 기록: stream 종료 시 message_delta 이벤트의 누적 usage 사용
 */
import type { VercelRequest, VercelResponse } from "@vercel/node";
import { createClient } from "@supabase/supabase-js";
import { applyCors } from "../_cors";

export const config = {
  api: { bodyParser: true, responseLimit: false },
};

const supabaseAdmin = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } }
);

const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY!;
const ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages";
const ANTHROPIC_VERSION = "2023-06-01";
const ANTHROPIC_BETA = "prompt-caching-2024-07-31";

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
  const usd =
    (inT * p.input +
      outT * p.output +
      cacheR * p.cacheRead +
      cacheC * p.cacheCreate) /
    1_000_000;
  return Math.round(usd * 100 * 10000) / 10000;
}

async function logUsage(
  userId: string,
  model: string,
  status: number,
  usage: any,
  durationMs: number,
  meta?: Record<string, unknown>
): Promise<void> {
  try {
    await supabaseAdmin.from("usage").insert({
      user_id: userId,
      model,
      endpoint: "llm_stream",
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
    console.error("[llm/stream] usage log failed:", err);
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

  const t0 = Date.now();

  // Auth
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
    res.status(401).json({ error: "unauthorized" });
    return;
  }
  const user = userData.user;

  // Paid 검증
  const { data: purchase } = await supabaseAdmin
    .from("purchases")
    .select("id")
    .eq("user_id", user.id)
    .eq("status", "paid")
    .limit(1)
    .maybeSingle();
  if (!purchase) {
    res.status(403).json({ error: "not_purchased" });
    return;
  }

  // Body — stream 강제
  const body = { ...(req.body || {}), stream: true };
  if (!body.model || !body.messages) {
    res.status(400).json({ error: "missing_fields" });
    return;
  }

  // Anthropic 호출
  let upstream: Response;
  try {
    upstream = await fetch(ANTHROPIC_API_URL, {
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
    await logUsage(user.id, body.model, 502, null, Date.now() - t0, {
      error: err instanceof Error ? err.message : String(err),
    });
    res.status(502).json({ error: "upstream_failed" });
    return;
  }

  if (!upstream.ok || !upstream.body) {
    const errText = await upstream.text();
    await logUsage(user.id, body.model, upstream.status, null, Date.now() - t0, {
      error: errText.slice(0, 500),
    });
    res.status(upstream.status).send(errText);
    return;
  }

  // SSE 헤더 설정
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache, no-transform");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");
  res.flushHeaders?.();

  // Anthropic 스트림을 그대로 전달 + 누적 usage 추출
  const reader = upstream.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let accumulatedUsage: any = null;
  let finalStatus = 200;

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      // 그대로 클라이언트에 전송
      res.write(chunk);

      // SSE 파싱해서 usage 추출 (message_start, message_delta)
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
            // message_start: 초기 usage (input_tokens 위주)
            if (obj.type === "message_start" && obj.message?.usage) {
              accumulatedUsage = { ...obj.message.usage };
            }
            // message_delta: output_tokens 누적
            if (obj.type === "message_delta" && obj.usage) {
              accumulatedUsage = { ...(accumulatedUsage || {}), ...obj.usage };
            }
            if (obj.type === "error") {
              finalStatus = 500;
            }
          } catch {
            // ignore parse error
          }
        }
      }
    }
  } catch (err) {
    console.error("[llm/stream] stream error:", err);
  } finally {
    res.end();
    await logUsage(user.id, body.model, finalStatus, accumulatedUsage, Date.now() - t0);
  }
}
