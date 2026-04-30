// Sprint 14 Phase B-3/B-4 — NEXT_PUBLIC_API_URL helper + error body size cap.
//
// 통합 목적:
// - 3 곳 (api-client.ts / test-order-dialog.tsx / tab-webhook.tsx) 의 fallback 일치
// - trailing slash strip (Next.js Vercel 환경 변수 가끔 trailing slash 포함)
// - production 미설정 시 1회 console.error (top-level throw 금지 — Next.js 16 의
//   `process.env.NEXT_PUBLIC_*` build-time inline 정책상 throw 가 prod build 깨뜨릴
//   위험. fallback 유지로 build 통과 + runtime 에서 명시 경고)
// - error response body 8KB cap (apiFetch / TestOrderDialog 양쪽 재사용)

let _hasWarnedApiBaseMissing = false;

export function getApiBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL;
  if (!raw) {
    // production browser 첫 호출 1회만 console.error.
    // SSR / build / dev 에선 silent fallback (build 깨지지 않도록).
    if (
      !_hasWarnedApiBaseMissing &&
      typeof window !== "undefined" &&
      process.env.NODE_ENV === "production"
    ) {
      _hasWarnedApiBaseMissing = true;
      console.error(
        "[api-base] NEXT_PUBLIC_API_URL is not set in production. " +
          "Falling back to http://localhost:8000 — requests will likely fail. " +
          "Set the variable in your build environment (Vercel/Docker/CI).",
      );
    }
    return "http://localhost:8000";
  }
  return raw.replace(/\/+$/, ""); // trailing slash strip
}

export const ERROR_BODY_MAX_BYTES = 8 * 1024; // 8KB cap

/**
 * Response 의 error body 를 안전하게 읽는다.
 * - JSON parse 우선. FastAPI HTTPException 표준 detail 필드는 그대로 보존.
 * - JSON 실패 시 text 로 fallback. 8KB 초과 시 truncate + suffix.
 * - text() 도 실패하면 빈 문자열.
 *
 * 주의: response.clone() 이 가능한 stream 인 경우에만 JSON 시도. 이미 read 된
 * response 는 호출자가 처리.
 */
export async function readErrorBody(res: Response): Promise<unknown> {
  // 1) JSON 시도 (clone 으로 stream 보존)
  try {
    const cloned = res.clone();
    return await cloned.json();
  } catch {
    // not JSON — 아래 text fallback
  }

  // 2) text fallback + size cap
  let text = "";
  try {
    text = await res.text();
  } catch {
    return "";
  }
  if (text.length > ERROR_BODY_MAX_BYTES) {
    return text.slice(0, ERROR_BODY_MAX_BYTES) + "...(truncated)";
  }
  return text;
}
