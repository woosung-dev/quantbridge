"use client";

// Sprint 26 — Live Session detail panel.
// Sprint 27 BL-140 — Activity Timeline line chart (events 누적 시각화).
//   진정한 equity curve (cumulative realized_pnl) 는 events 에 pnl 필드 없으므로
//   BL-140b (BE state.realized_pnl_history JSONB 추가) 별도 sprint 로 분리.
//
// 표시:
//  - Session 정보 (symbol/interval/last_evaluated_bar_time)
//  - Open trades snapshot + 누적 통계 (closed_trades, realized_pnl)
//  - Activity Timeline line chart (cumulative entry / close count)
//  - Recent events log (action / direction / status / order_id)

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useLiveSessionEvents, useLiveSessionState } from "../hooks";
import type { LiveSession, LiveSignalEvent } from "../schemas";

type Props = {
  session: LiveSession;
};

// Sprint 27 BL-140 — events 시간 순서로 windowed entry/close 카운트 추출.
// codex G.2 P1 #4: BE repository 가 created_at.desc() 순 (bar_time desc 보장 X)
//   → client-side 명시 정렬 (bar_time asc, sequence_no asc) 필수.
// codex G.2 P1 #5: window=100 (events.items 응답 limit) → 진정한 cumulative
//   아님. UI 라벨에 "최근 N events 누적" 명시.
function buildActivityTimeline(
  events: ReadonlyArray<LiveSignalEvent>,
): Array<{ label: string; entries_in_window: number; closes_in_window: number }> {
  // chronological 정렬 (bar_time asc → 같은 bar 면 sequence_no asc).
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
      // codex G.2 P2 #3 — toLocaleString() 으로 날짜 포함 (장시간 세션 X축 중복 방어).
      label: new Date(ev.bar_time).toLocaleString(),
      entries_in_window: entries,
      closes_in_window: closes,
    };
  });
}

export function LiveSessionDetail({ session }: Props) {
  // LESSON-004 H-1: dep array 우회 위해 primitive (session.id, session.is_active) 직접 전달
  const { data: state, isLoading: stateLoading } = useLiveSessionState(
    session.id,
    session.is_active,
  );
  const { data: events, isLoading: eventsLoading } = useLiveSessionEvents(
    session.id,
  );

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
          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={buildActivityTimeline(events.items)}
                margin={{ top: 5, right: 16, bottom: 5, left: -16 }}
              >
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="entries_in_window"
                  name="Entries (window)"
                  stroke="#22c55e"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="closes_in_window"
                  name="Closes (window)"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
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
