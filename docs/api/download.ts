/**
 * GET /api/download
 *
 * 결제 완료한 사용자에게 Supabase Storage signed URL 발급.
 *
 * Headers:
 *   Authorization: Bearer <supabase-jwt>
 *
 * Query (optional):
 *   ?session_id=cs_xxx     — 특정 결제 건에 묶어 검증 (없으면 사용자의 paid 레코드 1개)
 *
 * Response:
 *   200 { url, expires_in }   — 24h signed URL
 *   401 { error: 'unauthorized' }
 *   403 { error: 'not_purchased' }
 */
import type { VercelRequest, VercelResponse } from "@vercel/node";
import { createClient } from "@supabase/supabase-js";
import { applyCors } from "./_cors";
import { rateLimit, rateLimitKey } from "./_validate";

const supabaseAdmin = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } }
);

const BUCKET = "releases";
const OBJECT = "jarvis-v0.3.0.zip";
const TTL_SECONDS = 60 * 60 * 24; // 24h

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (applyCors(req, res)) return;
  if (req.method !== "GET") {
    res.status(405).json({ error: "method_not_allowed" });
    return;
  }

  const ipRl = rateLimit(rateLimitKey(req));
  if (!ipRl.ok) {
    res.setHeader("Retry-After", String(ipRl.retryAfter));
    res.status(429).json({ error: "rate_limit_exceeded", retry_after: ipRl.retryAfter });
    return;
  }

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
    res.status(401).json({ error: "unauthorized" });
    return;
  }
  const user = userData.user;

  // ── 2. paid 결제 검증 ─────────────────────────────────
  let query = supabaseAdmin
    .from("purchases")
    .select("id, status, stripe_session_id")
    .eq("user_id", user.id)
    .eq("status", "paid")
    .limit(1);

  const sessionId = req.query.session_id;
  if (typeof sessionId === "string" && sessionId) {
    query = query.eq("stripe_session_id", sessionId);
  }

  const { data: purchase, error: purchaseErr } = await query.maybeSingle();

  if (purchaseErr) {
    console.error("[download] DB error:", purchaseErr);
    res.status(500).json({ error: "db_error" });
    return;
  }
  if (!purchase) {
    res.status(403).json({ error: "not_purchased" });
    return;
  }

  // ── 3. signed URL 발급 ─────────────────────────────────
  const { data, error } = await supabaseAdmin.storage
    .from(BUCKET)
    .createSignedUrl(OBJECT, TTL_SECONDS);

  if (error || !data?.signedUrl) {
    console.error("[download] signed URL error:", error);
    res
      .status(500)
      .json({ error: error?.message || "signed_url_failed" });
    return;
  }

  res.status(200).json({
    url: data.signedUrl,
    expires_in: TTL_SECONDS,
    object: OBJECT,
  });
}
