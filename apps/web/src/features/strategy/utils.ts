// Sprint 7c: Strategy 도메인 유틸 — parse_status 메타 + debounce 훅 + 409 에러 판별 타입 가드.

import { useEffect, useState } from "react";

import type { ApiError } from "@/lib/api-client";

import type { ParseStatus } from "./schemas";

/**
 * parse_status별 표시 메타데이터 (라벨, tone).
 * `tone`은 globals.css의 `[data-tone="*"]` CSS 규칙과 매칭되며,
 * T3 Step 3.6에서 `<Badge data-tone={meta.tone}>` 형태로 소비됨.
 * shadcn Badge `variant`와는 별개 — DESIGN.md 색상 토큰 직접 매핑.
 */
export const PARSE_STATUS_META: Record<
  ParseStatus,
  { label: string; tone: "success" | "warning" | "destructive" }
> = {
  ok: { label: "파싱 성공", tone: "success" },
  unsupported: { label: "미지원", tone: "warning" },
  error: { label: "파싱 실패", tone: "destructive" },
};

/**
 * 값 변경 후 delayMs 이후의 최신 값을 반환하는 debounce 훅.
 * 검색어 입력·Monaco editor onChange 등 과도한 API 호출 방지용.
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}

/**
 * ISO datetime 을 `YYYY-MM-DD HH:mm` (UTC) 로 표기한다. 값이 없거나 파싱 불가면
 * 무데이터 셀 표기(EMPTY_CELL "—")를 돌려준다. 목록의 마지막 수정 시각에 쓴다.
 * backtest/utils.formatDateTime 과 같은 규약(도메인 경계 유지 위해 별도 보유).
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const yyyy = d.getUTCFullYear();
  const mo = String(d.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(d.getUTCDate()).padStart(2, "0");
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${yyyy}-${mo}-${dd} ${hh}:${mm}`;
}

/**
 * DELETE 시도 시 Backend가 409 conflict(`strategy_has_backtests`)로 응답한 경우를 식별.
 * 호출부에서 `true`일 때 "archive fallback" 모달로 전환하기 위한 타입 가드.
 */
export function isStrategyHasBacktestsError(err: unknown): boolean {
  const e = err as Partial<ApiError>;
  return e?.status === 409 && e?.code === "strategy_has_backtests";
}
