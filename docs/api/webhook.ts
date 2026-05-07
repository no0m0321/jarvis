/**
 * POST /api/webhook
 *
 * Stripe webhook 수신.
 * `checkout.session.completed` 이벤트 → purchases.status = 'paid' 업데이트.
 *
 * 보안:
 *   - HMAC signature 검증 (STRIPE_WEBHOOK_SECRET)
 *   - raw body 읽기 위해 bodyParser disable
 *   - service_role key 사용 (RLS bypass)
 *
 * Idempotency:
 *   - 동일 session.id에 대한 재시도가 와도 status가 이미 'paid'면 update 결과 동일
 */
import type { VercelRequest, VercelResponse } from "@vercel/node";
import Stripe from "stripe";
import { createClient } from "@supabase/supabase-js";

export const config = {
  api: { bodyParser: false },
};

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: "2025-02-24.acacia",
});

const supabaseAdmin = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } }
);

const WEBHOOK_SECRET = process.env.STRIPE_WEBHOOK_SECRET!;

async function readRawBody(req: VercelRequest): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (chunk: Buffer) => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== "POST") {
    res.status(405).json({ error: "method_not_allowed" });
    return;
  }

  const sig = req.headers["stripe-signature"];
  if (!sig || typeof sig !== "string") {
    res.status(400).json({ error: "missing_signature" });
    return;
  }

  let event: Stripe.Event;
  try {
    const rawBody = await readRawBody(req);
    event = stripe.webhooks.constructEvent(rawBody, sig, WEBHOOK_SECRET);
  } catch (err) {
    console.error("[webhook] signature verification failed:", err);
    res.status(400).json({
      error: "signature_failed",
      detail: err instanceof Error ? err.message : String(err),
    });
    return;
  }

  // ── 이벤트 처리 ─────────────────────────────────────────
  try {
    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as Stripe.Checkout.Session;
        const userId =
          session.client_reference_id || (session.metadata?.user_id ?? null);

        if (!userId) {
          console.warn(
            "[webhook] checkout.session.completed without user_id:",
            session.id
          );
        }

        const { error } = await supabaseAdmin
          .from("purchases")
          .update({
            status: "paid",
            paid_at: new Date().toISOString(),
            stripe_payment_intent:
              typeof session.payment_intent === "string"
                ? session.payment_intent
                : null,
          })
          .eq("stripe_session_id", session.id);

        if (error) {
          console.error("[webhook] DB update failed:", error);
          res.status(500).json({ error: "db_update_failed" });
          return;
        }

        console.log(
          `[webhook] paid OK · session=${session.id} user=${userId}`
        );
        break;
      }

      case "checkout.session.expired":
      case "checkout.session.async_payment_failed": {
        const session = event.data.object as Stripe.Checkout.Session;
        await supabaseAdmin
          .from("purchases")
          .update({ status: "failed" })
          .eq("stripe_session_id", session.id)
          .eq("status", "pending"); // pending인 것만 fail로
        break;
      }

      default:
        // 처리 안 하는 이벤트는 200 OK 반환 (Stripe 재시도 막음)
        break;
    }
  } catch (err) {
    console.error("[webhook] handler error:", err);
    res
      .status(500)
      .json({ error: err instanceof Error ? err.message : "handler_error" });
    return;
  }

  res.status(200).json({ received: true });
}
