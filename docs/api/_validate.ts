/**
 * 공통 검증 유틸 — 입력 검증 + size limit + rate limiting.
 */
import type { VercelRequest, VercelResponse } from "@vercel/node";

// ─────────────── Body size limit ───────────────
const MAX_BODY_BYTES = 256 * 1024; // 256 KB (LLM 메시지 + tools 충분히 수용)

export function validateBodySize(req: VercelRequest, res: VercelResponse): boolean {
  const cl = req.headers["content-length"];
  const size = cl ? parseInt(cl as string, 10) : 0;
  if (size > MAX_BODY_BYTES) {
    res.status(413).json({
      error: "payload_too_large",
      max_bytes: MAX_BODY_BYTES,
      received: size,
    });
    return false;
  }
  return true;
}

// ─────────────── 필수 필드 + 타입 검증 ───────────────
export type FieldSpec = {
  type: "string" | "number" | "boolean" | "object" | "array";
  required?: boolean;
  maxLength?: number;
  pattern?: RegExp;
};

export function validateBody(
  body: any,
  schema: Record<string, FieldSpec>
): { ok: true } | { ok: false; error: string; field?: string } {
  if (typeof body !== "object" || body === null) {
    return { ok: false, error: "body must be JSON object" };
  }
  for (const [key, spec] of Object.entries(schema)) {
    const v = body[key];
    if (v === undefined || v === null) {
      if (spec.required) {
        return { ok: false, error: "missing_required", field: key };
      }
      continue;
    }
    const actual = Array.isArray(v) ? "array" : typeof v;
    if (actual !== spec.type) {
      return {
        ok: false,
        error: `wrong_type: ${key} expected ${spec.type}, got ${actual}`,
        field: key,
      };
    }
    if (spec.type === "string") {
      if (spec.maxLength && v.length > spec.maxLength) {
        return {
          ok: false,
          error: `too_long: ${key} > ${spec.maxLength}`,
          field: key,
        };
      }
      if (spec.pattern && !spec.pattern.test(v)) {
        return { ok: false, error: `pattern_mismatch: ${key}`, field: key };
      }
    }
  }
  return { ok: true };
}

// ─────────────── Rate limit (메모리 토큰 버킷) ───────────────
// 주의: Vercel functions는 cold start 시 메모리 초기화. 단일 인스턴스 단기 보호용.
// 본격 rate limit은 Upstash Redis or Supabase row count 권장 (v0.5.x).
type Bucket = { tokens: number; lastRefill: number };
const _buckets = new Map<string, Bucket>();
const BUCKET_CAPACITY = 60;       // 분당 60 호출
const REFILL_PER_SEC = 1;         // 초당 1 토큰 (= 분당 60)
const MAX_BUCKETS = 10000;        // 메모리 보호 (LRU 풍 cleanup)

export function rateLimit(key: string): { ok: true } | { ok: false; retryAfter: number } {
  const now = Date.now();
  let b = _buckets.get(key);
  if (!b) {
    if (_buckets.size >= MAX_BUCKETS) {
      // 가장 오래된 절반 제거
      const entries = Array.from(_buckets.entries()).sort(
        (a, c) => a[1].lastRefill - c[1].lastRefill
      );
      for (let i = 0; i < entries.length / 2; i++) {
        _buckets.delete(entries[i][0]);
      }
    }
    b = { tokens: BUCKET_CAPACITY, lastRefill: now };
    _buckets.set(key, b);
  }

  // refill
  const elapsedSec = (now - b.lastRefill) / 1000;
  if (elapsedSec > 0) {
    b.tokens = Math.min(BUCKET_CAPACITY, b.tokens + elapsedSec * REFILL_PER_SEC);
    b.lastRefill = now;
  }

  if (b.tokens < 1) {
    const retryAfter = Math.ceil((1 - b.tokens) / REFILL_PER_SEC);
    return { ok: false, retryAfter };
  }
  b.tokens -= 1;
  return { ok: true };
}

/**
 * IP + userId 조합 키. userId 없으면 IP만.
 */
export function rateLimitKey(req: VercelRequest, userId?: string): string {
  const ip =
    (req.headers["x-forwarded-for"] as string)?.split(",")[0].trim() ||
    (req.headers["x-real-ip"] as string) ||
    "unknown";
  return userId ? `u:${userId}` : `ip:${ip}`;
}
