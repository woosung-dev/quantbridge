"use client";

// Sprint 7c: Strategy 공통 mutation 에러 핸들러 — 401/429/5xx 표준 분기.
// 422/409 등 4xx 비즈니스 오류는 호출부에서 field mapping(RHF setError) 또는 분기 처리.

import { toast } from "sonner";

import type { ApiError } from "@/lib/api-client";

/**
 * Strategy 공통 mutation 에러 핸들러.
 * 401 → `lib/api-client.ts` 가 이미 재발급 1회 재시도와 세션 없음 → /sign-in 리다이렉트를 끝낸 뒤다.
 *        여기까지 왔다면 리다이렉트 중이거나 새 토큰으로도 401 인 설정 문제라 안내만 한다.
 * 429 → rate limit 안내.
 * 5xx → 일반 서버 오류 안내.
 * 4xx (422/409 등) → 호출부에서 개별 field mapping 또는 분기 처리 (본 함수는 generic toast).
 */
export function handleMutationError(err: unknown): void {
  const e = err as Partial<ApiError>;
  if (e?.status === 401) {
    toast.error("인증에 실패했습니다. 다시 로그인해 주세요.");
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
