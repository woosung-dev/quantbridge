"use client";

// Sprint 26 — Live Session detail panel.
// Sprint 27 BL-140 — Activity Timeline line chart (events 누적 시각화).
//   진정한 equity curve (cumulative realized_pnl) 는 events 에 pnl 필드 없으므로
//   BL-140b (BE state.realized_pnl_history JSONB 추가) 별도 sprint 로 분리.
// Sprint 33-A (BL-150 partial) — recharts → lightweight-charts (ActivityTimelineChart).
//   walk-forward / monte-carlo 차트는 Sprint 34 defer (lightweight-charts native 미지원).
//
// 표시:
//  - Session 정보 (symbol/interval/last_evaluated_bar_time)
//  - Open trades snapshot + 누적 통계 (closed_trades, realized_pnl)
//  - Activity Timeline line chart (cumulative entry / close count + optional PnL)
//  - Recent events log (action / direction / status / order_id)

import { useLiveSessionEvents, useLiveSessionState } from "../hooks";
import type { LiveSession } from "../schemas";
// Sprint 27 BL-140 — buildActivityTimeline 은 utils.ts (테스트 가능 단위).
// Sprint 28 Slice 3 (BL-140b) — buildActivityTimelineWithEquity 추가 (real cumulative PnL).
import {
  buildActivityTimeline,
  buildActivityTimelineWithEquity,
} from "../utils";
import { ActivityTimelineChart } from "./activity-timeline-chart";

type Props = {
  session: LiveSession;
};

export function LiveSessionDetail({ session }: Props) {
  // LESSON-004 H-1: dep array 우회 위해 primitive (session.id, session.is_active) 직접 전달
  const { data: state, isLoading: stateLoading } = useLiveSessionState(
    session.id,
    session.is_active,
  );
  const { data: events, isLoading: eventsLoading } = useLiveSessionEvents(
    session.id,
  );

  // Sprint 33-A: chart data 사전 계산 (lightweight-charts 호환).
  // React Compiler 가 자동 memoize — 수동 useMemo 사용 시 inferred-dep 충돌 발생.
  const hasEquity = Boolean(
    state?.equity_curve && state.equity_curve.length > 0,
  );
  const timelineData =
    !events || events.items.length === 0
      ? []
      : hasEquity && state?.equity_curve
        ? buildActivityTimelineWithEquity(events.items, state.equity_curve)
        : buildActivityTimeline(events.items);

  return (
    <div className="space-y-4" data-testid={`live-session-detail-${session.id}`}>
      <div className="rounded-md border p-4">
        <h3 className="font-medium">{session.symbol}</h3>
        <p className="text-xs text-muted-foreground">
          {session.interval} · last evaluated:{" "}
          {session.last_evaluated_bar_time
            ? new Date(session.last_evaluated_bar_time).toLocaleString()
            : "—"}
        </p>
        <dl className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">Closed Trades</dt>
            <dd className="font-mono">
              {stateLoading ? "…" : state?.total_closed_trades ?? 0}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Realized PnL</dt>
            <dd className="font-mono">
              {stateLoading ? "…" : (state?.total_realized_pnl ?? "0")}
            </dd>
          </div>
        </dl>
      </div>

      {/* Sprint 27 BL-140 — Activity Timeline (recent N events cumulative chart) */}
      <div className="rounded-md border p-4">
        <div className="mb-3 flex items-center justify-between">
          <h4 className="text-sm font-medium">Activity Timeline</h4>
          <p className="text-xs text-muted-foreground">
            최근 events 누적 entry / close (전체 누적 = BL-140b 후속)
          </p>
        </div>
        {eventsLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : !events || events.items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            아직 평가된 signal 이 없습니다. 다음 bar 평가를 기다려주세요.
          </p>
        ) : (
          <ActivityTimelineChart data={timelineData} showEquity={hasEquity} />
        )}
      </div>

      <div className="rounded-md border p-4">
        <h4 className="mb-2 text-sm font-medium">Recent Events</h4>
        {eventsLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : !events || events.items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            아직 평가된 signal 이 없습니다. 다음 bar 평가를 기다려주세요.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-[480px] w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground">
                  <th className="py-1">Bar</th>
                  <th className="py-1">Action</th>
                  <th className="py-1">Direction</th>
                  <th className="py-1">Qty</th>
                  <th className="py-1">Status</th>
                </tr>
              </thead>
              <tbody>
                {events.items.slice(0, 20).map((ev) => (
                  <tr key={ev.id} className="border-t">
                    <td className="py-1 font-mono">
                      {new Date(ev.bar_time).toLocaleTimeString()}
                    </td>
                    <td className="py-1">{ev.action}</td>
                    <td className="py-1">{ev.direction}</td>
                    <td className="py-1 font-mono">{ev.qty}</td>
                    <td className="py-1">
                      <span
                        className={
                          ev.status === "dispatched"
                            ? "text-green-600"
                            : ev.status === "failed"
                              ? "text-destructive"
                              : "text-muted-foreground"
                        }
                      >
                        {ev.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
