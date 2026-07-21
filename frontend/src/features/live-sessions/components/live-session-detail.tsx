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

import { useMemo } from "react";

import { labelOf } from "@/lib/labels";

import { useLiveSessionEvents, useLiveSessionState } from "../hooks";
import {
  LIVE_SIGNAL_DIRECTION_LABEL,
  LIVE_SIGNAL_EVENT_STATUS_LABEL,
} from "../labels";
import type { LiveSession } from "../schemas";
// Sprint 27 BL-140 — buildActivityTimeline 은 utils.ts (테스트 가능 단위).
// Sprint 28 Slice 3 (BL-140b) — buildActivityTimelineWithEquity 추가 (real cumulative PnL).
import {
  buildActivityTimeline,
  buildActivityTimelineWithEquity,
  formatDateTime,
  formatRealizedPnl,
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
  // useMemo — RQ structural sharing 이 items/equity_curve 하위 참조 identity 를
  // 보존하므로 dep 안전. 폴링 리렌더마다 새 배열이 생성되면 TradingChart data
  // effect(setData + fitContent)가 재실행되어 사용자 줌/팬이 리셋되는 것을 차단.
  const eventItems = events?.items;
  const equityCurve = state?.equity_curve;
  const hasEquity = Boolean(equityCurve && equityCurve.length > 0);
  const timelineData = useMemo(() => {
    if (!eventItems || eventItems.length === 0) return [];
    return hasEquity && equityCurve
      ? buildActivityTimelineWithEquity(eventItems, equityCurve)
      : buildActivityTimeline(eventItems);
  }, [eventItems, equityCurve, hasEquity]);

  return (
    <div className="space-y-4" data-testid={`live-session-detail-${session.id}`}>
      <div className="rounded-md border p-4">
        <h3 className="font-medium">{session.symbol}</h3>
        <p className="text-xs text-muted-foreground">
          {session.interval} · 마지막 평가 {formatDateTime(session.last_evaluated_bar_time)}
        </p>
        <dl className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">종료 거래</dt>
            <dd className="font-mono">
              {stateLoading ? "…" : state?.total_closed_trades ?? 0}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">실현 손익</dt>
            <dd className="font-mono">
              {stateLoading ? (
                "…"
              ) : (
                <PnlValue raw={state?.total_realized_pnl ?? "0"} />
              )}
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
                      {formatDateTime(ev.bar_time)}
                    </td>
                    <td className="py-1">{ev.action}</td>
                    <td className="py-1">
                      {labelOf(
                        LIVE_SIGNAL_DIRECTION_LABEL,
                        ev.direction,
                        "live-signal-direction",
                      )}
                    </td>
                    <td className="py-1 font-mono">{ev.qty}</td>
                    <td className="py-1">
                      <span
                        className={
                          ev.status === "dispatched"
                            ? "text-success"
                            : ev.status === "failed"
                              ? "text-destructive"
                              : "text-muted-foreground"
                        }
                      >
                        {labelOf(
                          LIVE_SIGNAL_EVENT_STATUS_LABEL,
                          ev.status,
                          "liveEvent.status",
                        )}
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

// 실현손익 값 — 부호 + tone 색조 (profit=success / loss=destructive / flat=muted).
function PnlValue({ raw }: { raw: string }) {
  const { text, tone } = formatRealizedPnl(raw);
  const toneClass =
    tone === "profit"
      ? "text-[color:var(--success)]"
      : tone === "loss"
        ? "text-[color:var(--destructive)]"
        : "text-[color:var(--foreground)]";
  return <span className={toneClass}>{text}</span>;
}
