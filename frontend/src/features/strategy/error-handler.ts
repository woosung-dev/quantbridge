"use client";

// Sprint 7c: Strategy 공통 mutation 에러 핸들러 — 401/429/5xx 표준 분기.
// 422/409 등 4xx 비즈니스 오류는 호출부에서 field mapping(RHF setError) 또는 분기 처리.

import { toast } from "sonner";

import type { ApiError } from "@/lib/api-client";

/**
 * Strategy 공통 mutation 에러 핸들러.
 * 401 → Clerk session 만료로 간주하여 sign-in으로 redirect.
 * 429 → rate limit 안내.
 * 5xx → 일반 서버 오류 안내.
 * 4xx (422/409 등) → 호출부에서 개별 field mapping 또는 분기 처리 (본 함수는 generic toast).
 */
export function handleMutationError(
  err: unknown,
  ctx: { redirectOn401?: boolean } = { redirectOn401: true },
): void {
  const e = err as Partial<ApiError>;
  if (e?.status === 401 && ctx.redirectOn401) {
    if (typeof window !== "undefined") {
      window.location.href =
        "/sign-in?redirect_url=" + encodeURIComponent(window.location.pathname);
    }
    return;
  }
  if (e?.status === 429) {
    toast.error("요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.");
    return;
  }
  if ((e?.status ?? 500) >= 500) {
    toast.error("서버 오류. 잠시 후 다시 시도해 주세요.");
    return;
  }
  toast.error(`실패: ${e?.message ?? "알 수 없는 오류"}`);
}
