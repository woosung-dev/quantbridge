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

// 2026-09-06 데이터 경로 조사 3-B — 서버(SSR/RSC) 분기.
//   서버는 `API_URL`(NEXT_PUBLIC_ 아님 → 번들에 인라인되지 않는다)을 먼저 보고 없으면
//   `NEXT_PUBLIC_API_URL` 로 간다. 브라우저는 `NEXT_PUBLIC_API_URL` 만 본다.
//   ★현 배포는 FE 컨테이너→호스트 uvicorn 내부 경로가 없어(`frontend-deploy.md` §2) `API_URL` 을
//   비우고 공개 호스트로 헤어핀한다 — 이 분기가 지금 주는 값은 「서버에서도 경고가 찍힌다」다.
//   종전엔 경고가 `typeof window` 게이트 뒤라 SSR/RSC(prefetch·share·OG·invite) 의 미설정이
//   **무진단**으로 localhost:8000 을 때렸다.
export function getApiBase(): string {
  const isServer = typeof window === "undefined";
  const raw = (isServer ? process.env.API_URL : undefined) || process.env.NEXT_PUBLIC_API_URL;
  if (!raw) {
    // production 첫 호출 1회만 console.error — 서버·브라우저 모두. build / dev 는 조용하다
    // (`NEXT_PUBLIC_*` 빌드타임 인라인 정책상 throw 는 prod build 를 깨뜨리므로 fallback 유지).
    if (!_hasWarnedApiBaseMissing && process.env.NODE_ENV === "production") {
      _hasWarnedApiBaseMissing = true;
      console.error(
        `[api-base] NEXT_PUBLIC_API_URL is not set in production${
          isServer ? " (server: API_URL is also unset)" : ""
        }. Falling back to http://localhost:8000 — requests will likely fail. ` +
          "Set the variable in your build environment (Docker/CI).",
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
    return `${text.slice(0, ERROR_BODY_MAX_BYTES)}...(truncated)`;
  }
  return text;
}
