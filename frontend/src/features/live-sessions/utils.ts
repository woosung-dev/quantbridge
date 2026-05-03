// Sprint 26 — Live Sessions pure helpers (테스트 가능 단위).

import type { EquityPoint } from "./types";

// ── Refetch interval — active session 일 때만 빠르게 폴링 ────────────────
//
// LESSON-004 H-1: useEffect dep 에 RQ data 사용 금지 — refetchInterval callback
// 안에서 q.state.data 사용은 RQ 가 제공하는 stable closure 이므로 OK.
// 본 helper 는 hooks.ts 에서 callback 안에서 호출.

export const LIVE_SESSION_STATE_REFETCH_ACTIVE_MS = 5_000;
export const LIVE_SESSION_STATE_REFETCH_IDLE_MS = 30_000;
export const LIVE_SESSION_LIST_REFETCH_MS = 30_000;
export const MAX_LIVE_SESSIONS_PER_USER = 5;

/**
 * Sprint 26 — pure helper for unit testing.
 * is_active=true → 5s refetch, false → 30s.
 */
export function computeLiveSessionStateRefetchInterval(isActive: boolean): number {
  return isActive
    ? LIVE_SESSION_STATE_REFETCH_ACTIVE_MS
    : LIVE_SESSION_STATE_REFETCH_IDLE_MS;
}

// ── PnL series — closed_trades 누적 → equity curve ────────────────────────

type ClosedTrade = {
  exit_time: string; // ISO 8601 UTC
  pnl: number | string;
};

/**
 * 누적 PnL series 생성 — chart datapoint.
 *
 * @param closedTrades  exit_time ASC 정렬된 closed trades.
 *                       pnl 은 number 또는 string (Decimal 직렬화).
 * @returns timestamp 별 cumulative_pnl. 빈 배열 → 빈 결과.
 */
export function buildPnlSeries(
  closedTrades: ReadonlyArray<ClosedTrade>,
): EquityPoint[] {
  let cumulative = 0;
  const result: EquityPoint[] = [];
  for (const trade of closedTrades) {
    const pnlNum =
      typeof trade.pnl === "string" ? Number.parseFloat(trade.pnl) : trade.pnl;
    if (Number.isFinite(pnlNum)) {
      cumulative += pnlNum;
    }
    result.push({
      timestamp: trade.exit_time,
      cumulative_pnl: cumulative,
    });
  }
  return result;
}
