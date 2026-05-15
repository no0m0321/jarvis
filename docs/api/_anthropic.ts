import type { SupabaseClient } from "@supabase/supabase-js";

export const ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages";
export const ANTHROPIC_VERSION = process.env.ANTHROPIC_VERSION || "2023-06-01";
export const ANTHROPIC_BETA = process.env.ANTHROPIC_BETA || "prompt-caching-2024-07-31";
export const DEFAULT_MODEL = process.env.JARVIS_DEFAULT_MODEL || "claude-sonnet-4-6";
export const PREMIUM_MODEL = process.env.JARVIS_PREMIUM_MODEL || "claude-opus-4-7";
export const FAST_MODEL = process.env.JARVIS_FAST_MODEL || "claude-haiku-4-5-20251001";

export const MODEL_ALIASES: Record<string, string> = {
  auto: "auto",
  balanced: DEFAULT_MODEL,
  default: DEFAULT_MODEL,
  premium: PREMIUM_MODEL,
  pro: PREMIUM_MODEL,
  fast: FAST_MODEL,
  quick: FAST_MODEL,
  sonnet: DEFAULT_MODEL,
  sonnet4: DEFAULT_MODEL,
  "sonnet-4": DEFAULT_MODEL,
  opus: PREMIUM_MODEL,
  opus4: PREMIUM_MODEL,
  "opus-4": PREMIUM_MODEL,
  haiku: FAST_MODEL,
  haiku4: FAST_MODEL,
  "haiku-4": FAST_MODEL,
};

export const PRICING: Record<string, { input: number; output: number; cacheRead: number; cacheCreate: number }> = {
  [PREMIUM_MODEL]: { input: 15.00, output: 75.00, cacheRead: 1.50, cacheCreate: 18.75 },
  [DEFAULT_MODEL]: { input: 3.00, output: 15.00, cacheRead: 0.30, cacheCreate: 3.75 },
  [FAST_MODEL]: { input: 0.80, output: 4.00, cacheRead: 0.08, cacheCreate: 1.00 },
};

export type AnthropicUsage = {
  input_tokens?: number;
  output_tokens?: number;
  cache_read_input_tokens?: number;
  cache_creation_input_tokens?: number;
};

function estimateTextSize(body: any): number {
  let total = typeof body?.system === "string" ? body.system.length : JSON.stringify(body?.system || "").length;
  for (const message of body?.messages || []) {
    const content = message?.content;
    if (typeof content === "string") total += content.length;
    else if (Array.isArray(content)) total += content.map((block: any) => String(block?.text || block?.content || "")).join("\n").length;
    else total += String(content || "").length;
  }
  return total;
}

function hasComplexIntent(body: any): boolean {
  const joined = JSON.stringify(body?.messages || []).toLowerCase();
  return [
    "코드", "디버그", "설계", "기획", "분석", "대규모", "상용", "배포",
    "refactor", "architecture", "debug", "analyze", "production", "premium", "deploy",
  ].some((keyword) => joined.includes(keyword));
}

export function resolveModel(model: unknown, body?: any): string {
  const raw = String(model || "auto").trim();
  const key = raw.toLowerCase();
  const mapped = MODEL_ALIASES[key] || raw;
  if (mapped !== "auto") return mapped;
  if (process.env.JARVIS_AUTO_MODEL === "0") return DEFAULT_MODEL;
  const size = estimateTextSize(body || {});
  const fastChars = Number(process.env.JARVIS_FAST_ROUTE_CHARS || 1200);
  const premiumChars = Number(process.env.JARVIS_PREMIUM_ROUTE_CHARS || 14000);
  if (size <= fastChars && !hasComplexIntent(body || {})) return FAST_MODEL;
  if ((size >= premiumChars || hasComplexIntent(body || {})) && process.env.JARVIS_ALLOW_PREMIUM_ROUTING !== "0") return PREMIUM_MODEL;
  return DEFAULT_MODEL;
}

export function estimateCostCents(model: string, usage: AnthropicUsage | null | undefined): number {
  const p = PRICING[model] || PRICING[DEFAULT_MODEL] || { input: 3, output: 15, cacheRead: 0.3, cacheCreate: 3.75 };
  const inT = usage?.input_tokens ?? 0;
  const outT = usage?.output_tokens ?? 0;
  const cacheR = usage?.cache_read_input_tokens ?? 0;
  const cacheC = usage?.cache_creation_input_tokens ?? 0;
  const usd = (inT * p.input + outT * p.output + cacheR * p.cacheRead + cacheC * p.cacheCreate) / 1_000_000;
  return Math.round(usd * 100 * 10000) / 10000;
}

function clampNumber(value: unknown, fallback: number, min: number, max: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(min, Math.min(max, n));
}

function cacheSystem(system: unknown): unknown {
  if (!system) return undefined;
  if (process.env.JARVIS_DISABLE_PROMPT_CACHE === "1") return system;
  if (typeof system === "string") {
    return [{ type: "text", text: system, cache_control: { type: "ephemeral" } }];
  }
  if (Array.isArray(system)) {
    const cloned = system.map((block: any) => ({ ...block }));
    const idx = [...cloned].reverse().findIndex((block: any) => block?.type === "text");
    if (idx >= 0) {
      const realIdx = cloned.length - 1 - idx;
      cloned[realIdx] = { ...cloned[realIdx], cache_control: cloned[realIdx].cache_control || { type: "ephemeral" } };
    }
    return cloned;
  }
  return system;
}

function normalizeMessages(messages: unknown): any[] {
  if (!Array.isArray(messages)) return [];
  return messages.map((message: any) => {
    const role = ["user", "assistant"].includes(message?.role) ? message.role : "user";
    const content = message?.content;
    if (typeof content === "string") return { role, content };
    if (Array.isArray(content)) return { role, content: content.map((block: any) => block?.type === "text" ? { type: "text", text: String(block?.text || "") } : block) };
    return { role, content: String(content || "") };
  });
}

export function normalizeAnthropicBody(raw: any, stream: boolean): any {
  const body = { ...(raw || {}) };
  body.messages = normalizeMessages(body.messages);
  body.model = resolveModel(body.model, body);
  body.stream = stream;
  body.max_tokens = clampNumber(body.max_tokens, 2048, 64, Number(process.env.JARVIS_MAX_TOKENS || 8192));
  if (body.temperature !== undefined) body.temperature = clampNumber(body.temperature, 0.4, 0, 1);
  if (body.top_p !== undefined) body.top_p = clampNumber(body.top_p, 0.95, 0.01, 1);
  if (body.system) body.system = cacheSystem(body.system);
  delete body.user_id;
  return body;
}

export function anthropicHeaders(): Record<string, string> {
  return {
    "x-api-key": process.env.ANTHROPIC_API_KEY || "",
    "anthropic-version": ANTHROPIC_VERSION,
    "anthropic-beta": ANTHROPIC_BETA,
    "Content-Type": "application/json",
  };
}

export async function fetchAnthropicWithRetry(body: any): Promise<Response> {
  const attempts = Math.max(1, Number(process.env.JARVIS_ANTHROPIC_RETRIES || 3));
  const timeoutMs = Math.max(5000, Number(process.env.JARVIS_ANTHROPIC_TIMEOUT_MS || 60000));
  let lastErr: unknown = null;
  for (let i = 0; i < attempts; i++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(ANTHROPIC_API_URL, {
        method: "POST",
        headers: anthropicHeaders(),
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (![408, 409, 425, 429, 500, 502, 503, 504].includes(res.status) || i === attempts - 1) return res;
      await new Promise((r) => setTimeout(r, 320 * Math.pow(2, i) + Math.floor(Math.random() * 220)));
    } catch (err) {
      clearTimeout(timer);
      lastErr = err;
      if (i === attempts - 1) throw err;
      await new Promise((r) => setTimeout(r, 320 * Math.pow(2, i) + Math.floor(Math.random() * 220)));
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error(String(lastErr || "anthropic_request_failed"));
}

export async function logClaudeUsage(
  supabaseAdmin: SupabaseClient,
  userId: string,
  model: string,
  endpoint: string,
  status: number,
  usage: AnthropicUsage | null | undefined,
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
    console.error(`[${endpoint}] usage log failed:`, err);
  }
}
