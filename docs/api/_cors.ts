/**
 * CORS 화이트리스트 헬퍼.
 *
 * 허용된 origin만 응답에 Access-Control-Allow-Origin 설정.
 * 다른 origin에서 호출되면 헤더 미설정 → 브라우저가 차단.
 *
 * 환경변수 ALLOWED_ORIGINS (콤마 구분) 또는 기본 화이트리스트 사용.
 */
import type { VercelRequest, VercelResponse } from "@vercel/node";

const DEFAULT_ALLOWED = [
  // production — APP_URL 자동 추가됨 (아래)
  // localhost dev
  "http://localhost:3000",
  "http://127.0.0.1:3000",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
];

function buildAllowList(): Set<string> {
  const set = new Set<string>(DEFAULT_ALLOWED);
  if (process.env.APP_URL) {
    set.add(process.env.APP_URL.replace(/\/$/, ""));
  }
  if (process.env.ALLOWED_ORIGINS) {
    for (const o of process.env.ALLOWED_ORIGINS.split(",")) {
      const trimmed = o.trim().replace(/\/$/, "");
      if (trimmed) set.add(trimmed);
    }
  }
  return set;
}

const ALLOWED = buildAllowList();

/**
 * 요청 origin을 화이트리스트와 비교하고, 일치하면 응답 헤더에 set.
 * preflight (OPTIONS)인 경우 204로 즉시 응답하고 true 반환 (호출자가 return 처리).
 */
export function applyCors(req: VercelRequest, res: VercelResponse): boolean {
  const origin = (req.headers.origin as string | undefined) || "";
  const cleaned = origin.replace(/\/$/, "");

  // origin이 화이트리스트에 있으면만 허용 (없으면 헤더 미설정 → 브라우저 차단)
  if (cleaned && ALLOWED.has(cleaned)) {
    res.setHeader("Access-Control-Allow-Origin", cleaned);
    res.setHeader("Vary", "Origin");
    res.setHeader("Access-Control-Allow-Credentials", "true");
  }
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader(
    "Access-Control-Allow-Headers",
    "Authorization, Content-Type, stripe-signature"
  );
  res.setHeader("Access-Control-Max-Age", "86400");

  // preflight
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return true;
  }
  return false;
}
