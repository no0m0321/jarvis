/**
 * GET /api/whoami
 *
 * JWT 검증 + 결제 상태 빠른 조회 — Jarvis CLI가 로그인 직후 호출.
 *
 * Headers:
 *   Authorization: Bearer <supabase-jwt>
 *
 * Response:
 *   200 { email, user_id, paid, since? }
 *   401 { error: 'unauthorized' }
 */
import type { VercelRequest, VercelResponse } from "@vercel/node";
import { createClient } from "@supabase/supabase-js";
import { applyCors } from "./_cors";

const supabaseAdmin = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } }
);

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (applyCors(req, res)) return;
  if (req.method !== "GET") {
    res.status(405).json({ error: "method_not_allowed" });
    return;
  }

  const token = (req.headers.authorization || "")
    .replace(/^Bearer\s+/i, "")
    .trim();
  if (!token) {
    res.status(401).json({ error: "unauthorized" });
    return;
  }

  const { data: userData, error } = await supabaseAdmin.auth.getUser(token);
  if (error || !userData?.user) {
    res.status(401).json({ error: "unauthorized" });
    return;
  }
  const user = userData.user;

  const { data: purchase } = await supabaseAdmin
    .from("purchases")
    .select("paid_at, product, status")
    .eq("user_id", user.id)
    .eq("status", "paid")
    .limit(1)
    .maybeSingle();

  res.status(200).json({
    email: user.email,
    user_id: user.id,
    paid: !!purchase,
    since: purchase?.paid_at ?? null,
    product: purchase?.product ?? null,
  });
}
