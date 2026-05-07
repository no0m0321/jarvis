/**
 * POST /api/checkout
 *
 * 자비스 구매 — Stripe Checkout Session 생성.
 *
 * Headers:
 *   Authorization: Bearer <supabase-jwt>
 *
 * Response:
 *   200 { url: string }       — Stripe Checkout URL (브라우저가 redirect)
 *   401 { error: 'unauthorized' }
 *   409 { error: 'already_purchased' }
 *   500 { error: string }
 */
import type { VercelRequest, VercelResponse } from "@vercel/node";
import Stripe from "stripe";
import { createClient } from "@supabase/supabase-js";
import { applyCors } from "./_cors";
import { validateBodySize, rateLimit, rateLimitKey } from "./_validate";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: "2025-02-24.acacia",
});

const supabaseAdmin = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } }
);

const PRICE_ID = process.env.STRIPE_PRICE_ID!;
const APP_URL = process.env.APP_URL || "http://localhost:3000";

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

  // Rate limit (IP 기준, auth 전 단계라서 user는 모름)
  const rl = rateLimit(rateLimitKey(req));
  if (!rl.ok) {
    res.setHeader("Retry-After", String(rl.retryAfter));
    res.status(429).json({ error: "rate_limit_exceeded", retry_after: rl.retryAfter });
    return;
  }

  // ── 1. Auth (JWT 검증) ─────────────────────────────────────
  const authHeader = req.headers.authorization || "";
  const token = authHeader.replace(/^Bearer\s+/i, "").trim();
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

  // ── 2. 이미 결제 완료한 사용자 차단 ────────────────────────
  const { data: existing } = await supabaseAdmin
    .from("purchases")
    .select("id, status")
    .eq("user_id", user.id)
    .eq("status", "paid")
    .limit(1)
    .maybeSingle();

  if (existing) {
    res.status(409).json({ error: "already_purchased", already: true });
    return;
  }

  // ── 3. Stripe Checkout Session 생성 ─────────────────────────
  let session: Stripe.Checkout.Session;
  try {
    session = await stripe.checkout.sessions.create({
      mode: "payment",
      payment_method_types: ["card"],
      line_items: [{ price: PRICE_ID, quantity: 1 }],
      customer_email: user.email ?? undefined,
      client_reference_id: user.id,
      metadata: { user_id: user.id, product: "jarvis-v0.3" },
      success_url: `${APP_URL}/success.html?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${APP_URL}/?canceled=1`,
      allow_promotion_codes: true,
    });
  } catch (err) {
    console.error("[checkout] Stripe error:", err);
    res
      .status(500)
      .json({ error: err instanceof Error ? err.message : "stripe_error" });
    return;
  }

  // ── 4. pending purchase 레코드 ──────────────────────────────
  const { error: insertErr } = await supabaseAdmin.from("purchases").insert({
    user_id: user.id,
    stripe_session_id: session.id,
    amount_cents: session.amount_total ?? 600,
    currency: session.currency ?? "usd",
    status: "pending",
    product: "jarvis-v0.3",
  });

  if (insertErr) {
    console.error("[checkout] DB insert error:", insertErr);
    // session은 이미 만들어졌으니 url은 반환 — webhook이 결국 update
  }

  res.status(200).json({ url: session.url });
}
