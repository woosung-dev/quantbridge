// Sprint 26 — Live Sessions pure helpers (테스트 가능 단위).
// Sprint 27 BL-140 — buildActivityTimeline (recent events cumulative).

import type { LiveSignalEvent } from "./schemas";
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

// ── Activity Timeline — events windowed cumulative entry/close (Sprint 27 BL-140) ─

export type ActivityTimelinePoint = {
  label: string;
  entries_in_window: number;
  closes_in_window: number;
};

/**
 * Sprint 27 BL-140 — events 윈도우 내 cumulative entry/close 카운트.
 *
 * codex G.2 P1 #4 — BE repository 가 created_at.desc() 응답이라 bar_time desc
 *   보장 X. client-side 명시 정렬 (bar_time asc → 같은 bar 면 sequence_no asc) 의무.
 * codex G.2 P1 #5 — 진정한 cumulative 아니라 "최근 N events 누적" (window=100,
 *   events.items 응답 limit). label 명시 의무 (UI에서 처리).
 *
 * @param events  events.items (limit=100, BE created_at desc 응답).
 * @returns chronological 순서로 정렬된 cumulative datapoint.
 */
export function buildActivityTimeline(
  events: ReadonlyArray<LiveSignalEvent>,
): ActivityTimelinePoint[] {
  const sorted = events.slice().sort((a, b) => {
    const ta = Date.parse(a.bar_time);
    const tb = Date.parse(b.bar_time);
    if (ta !== tb) return ta - tb;
    return a.sequence_no - b.sequence_no;
  });
  let entries = 0;
  let closes = 0;
  return sorted.map((ev) => {
    if (ev.action === "entry") entries += 1;
    else if (ev.action === "close") closes += 1;
    return {
      // codex G.2 P2 #3 — toLocaleString() (장시간 세션 X축 중복 방어).
      label: new Date(ev.bar_time).toLocaleString(),
      entries_in_window: entries,
      closes_in_window: closes,
    };
  });
}

// Sprint 28 Slice 3 (BL-140b) — entry/close + real cumulative equity 통합.
import type { EquityCurvePoint } from "./schemas";

export type ActivityTimelineWithEquityPoint = ActivityTimelinePoint & {
  cumulative_pnl: number; // BE 의 string Decimal → FE number (chart 렌더용, precision 충분)
};

/**
 * Sprint 28 BL-140b — buildActivityTimeline + equity_curve 병합.
 *
 * BE 의 equity_curve (LiveSignalState.equity_curve) 를 entry/close timeline 과 정렬 병합.
 * 같은 timestamp 의 event 가 있으면 equity 도 함께 표시. equity 만 있는 datapoint 는
 * entry/close 직전 값 carry-forward (line chart 연속성).
 *
 * @param events  events.items (limit=100, BE created_at desc 응답).
 * @param equityCurve  state.equity_curve (BE 누적 PnL timeseries, ASC sorted).
 * @returns dual-axis chart 용 datapoint.
 */
export function buildActivityTimelineWithEquity(
  events: ReadonlyArray<LiveSignalEvent>,
  equityCurve: ReadonlyArray<EquityCurvePoint>,
): ActivityTimelineWithEquityPoint[] {
  const baseTimeline = buildActivityTimeline(events);

  // equity_curve 의 timestamp_ms → cumulative_pnl 매핑
  const sortedEquity = equityCurve
    .slice()
    .sort((a, b) => a.timestamp_ms - b.timestamp_ms);

  // 원본 event 의 bar_time 재계산 (label 은 toLocaleString 이라 원본 보존 필요).
  // sortedEvents 는 baseTimeline 과 동일 순서 보장 (buildActivityTimeline 안 동일 sort 적용).
  const sortedEvents = events.slice().sort((a, b) => {
    const ta = Date.parse(a.bar_time);
    const tb = Date.parse(b.bar_time);
    if (ta !== tb) return ta - tb;
    return a.sequence_no - b.sequence_no;
  });

  // 각 event 의 bar_time ms 와 가장 가까운 (≤) equity_curve point 찾기
  return baseTimeline.map((point, idx) => {
    const ev = sortedEvents[idx];
    if (!ev) {
      return { ...point, cumulative_pnl: 0 };
    }
    const eventTimestampMs = Date.parse(ev.bar_time);

    // bar_time 이전의 마지막 equity (carry-forward)
    let cumulativePnl = 0;
    for (const eq of sortedEquity) {
      if (eq.timestamp_ms <= eventTimestampMs) {
        cumulativePnl = parseFloat(eq.cumulative_pnl);
      } else {
        break;
      }
    }

    return {
      ...point,
      cumulative_pnl: cumulativePnl,
    };
  });
}
