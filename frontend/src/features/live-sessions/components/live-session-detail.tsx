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

// BL-458 — 주문 블로터가 행 단위로 쓰는 출처 어휘 SSOT 를 그대로 재사용한다.
// `live-sessions/labels.ts` 로 복사하면 블로터 칩과 이 칩이 다른 말을 하게 된다.
import {
  ORDER_REALIZED_PNL_SOURCE_HINT,
  ORDER_REALIZED_PNL_SOURCE_LABEL,
  ORDER_STATE_LABEL,
} from "@/features/trading/labels";
import { labelOf, statusLabelOf } from "@/lib/labels";

import { useLiveSessionEvents, useLiveSessionState } from "../hooks";
import { LIVE_SIGNAL_DIRECTION_LABEL, LIVE_SIGNAL_EVENT_STATUS_LABEL } from "../labels";
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
import { OutcomeParityPanel } from "./outcome-parity-panel";
import { SessionEndedReason } from "./session-ended-reason";

type Props = {
  session: LiveSession;
};

const UNAVAILABLE = "—";

const ENTRY_SKIP_REASON_LABEL: Record<string, string> = {
  margin_insufficient: "증거금 부족",
  non_finite_qty: "수량 계산 불가",
  pyramiding_cap: "추가 진입 한도",
  session_closed: "거래 시간대 밖",
};

export function LiveSessionDetail({ session }: Props) {
  // LESSON-004 H-1: dep array 우회 위해 primitive (session.id, session.is_active) 직접 전달
  const { data: state, isLoading: stateLoading } = useLiveSessionState(
    session.id,
    session.is_active,
  );
  const { data: events, isLoading: eventsLoading } = useLiveSessionEvents(
    session.id,
    session.is_active,
  );

  const entrySkipCounts = new Map<string, number>();
  const entrySkips = state?.last_strategy_state_report?.last_bar_entry_skips;
  if (Array.isArray(entrySkips)) {
    for (const entrySkip of entrySkips) {
      if (
        entrySkip !== null &&
        typeof entrySkip === "object" &&
        "reason" in entrySkip &&
        typeof entrySkip.reason === "string"
      ) {
        entrySkipCounts.set(entrySkip.reason, (entrySkipCounts.get(entrySkip.reason) ?? 0) + 1);
      }
    }
  }
  const hasMarginInsufficient = entrySkipCounts.has("margin_insufficient");
  // 열린 record 스키마라 원소가 `null` 이나 숫자일 수 있다. 길이만 세면
  // `[null]` 이 "강제 청산 1건" 으로 위장된다. 진입 스킵과 같은 강도로 검증한다.
  const liquidations = state?.last_strategy_state_report?.last_bar_liquidations;
  const liquidationCount = Array.isArray(liquidations)
    ? liquidations.filter(
        (item) =>
          item !== null &&
          typeof item === "object" &&
          "direction" in item &&
          typeof item.direction === "string",
      ).length
    : 0;
  const pendingConditionalEntries: Array<{
    direction: string;
    stopPrice: string;
    targetPosition: string;
  }> = [];
  const pendingOrders = state?.last_strategy_state_report?.pending_orders;
  if (Array.isArray(pendingOrders)) {
    for (const pendingOrder of pendingOrders) {
      // 열린 record 스키마라 원소가 `null` 이나 숫자일 수 있다. 방향·트리거·목표 포지션을
      // 모두 검증하지 않으면 `[null]` 이 대기 조건부 진입으로 위장된다.
      if (
        pendingOrder !== null &&
        typeof pendingOrder === "object" &&
        "direction" in pendingOrder &&
        typeof pendingOrder.direction === "string" &&
        "stop_price" in pendingOrder &&
        typeof pendingOrder.stop_price === "string" &&
        "target_position" in pendingOrder &&
        typeof pendingOrder.target_position === "string"
      ) {
        pendingConditionalEntries.push({
          direction: pendingOrder.direction,
          stopPrice: pendingOrder.stop_price,
          targetPosition: pendingOrder.target_position,
        });
      }
    }
  }

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
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-medium">{session.symbol}</h3>
          {!session.is_active ? (
            <>
              <span
                className="rounded-sm bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
                data-testid="live-session-ended-badge"
              >
                종료된 세션
              </span>
              {/* BL-484 — 배지 옆에 사유. 사유가 없는 과거 행에서는 아예 안 그린다. */}
              <SessionEndedReason
                reason={session.deactivated_reason}
                testId="live-session-ended-reason"
              />
            </>
          ) : null}
        </div>
        <p className="text-muted-foreground text-xs">
          {session.interval} · 마지막 평가 {formatDateTime(session.last_evaluated_bar_time)}
        </p>
        <dl className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">종료 거래</dt>
            <dd className="font-mono">{stateLoading ? "…" : (state?.total_closed_trades ?? 0)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">실현 손익</dt>
            <dd className="font-mono">
              {stateLoading ? "…" : <PnlValue raw={state?.total_realized_pnl ?? "0"} />}
            </dd>
            {/* BL-458 — 이 숫자의 신뢰 등급. 어휘는 주문 블로터 칩과 동일한 SSOT 를
                쓴다(복사하면 두 화면이 다른 말을 하게 된다). 소계가 없으면(구 응답)
                아무것도 그리지 않는다 — 부재를 0 으로 위장하지 않는다. */}
            {!stateLoading &&
            state?.confirmed_realized_pnl !== undefined &&
            state.estimated_realized_pnl !== undefined ? (
              <dd className="mt-1 flex flex-wrap gap-1">
                <span className="chip chip-xs" title={ORDER_REALIZED_PNL_SOURCE_HINT.confirmed}>
                  {ORDER_REALIZED_PNL_SOURCE_LABEL.confirmed}{" "}
                  <PnlValue raw={state.confirmed_realized_pnl} />
                </span>
                <span className="chip chip-xs" title={ORDER_REALIZED_PNL_SOURCE_HINT.estimated}>
                  {ORDER_REALIZED_PNL_SOURCE_LABEL.estimated}{" "}
                  <PnlValue raw={state.estimated_realized_pnl} />
                </span>
              </dd>
            ) : null}
          </div>
          <div>
            <dt className="text-muted-foreground">기준 자본</dt>
            {/* 부재는 자리표로 둔다 — 모르는 값에 단위를 붙이면 0 을 아는 척하는 것과 같다.
                형제 `실현 손익` 칩과 같은 <dd> 를 쓴다 (<dl> 자식은 dt/dd 만 허용). */}
            <dd className="font-mono" data-testid="live-session-equity-baseline">
              {session.equity_baseline_usdt ? `${session.equity_baseline_usdt} USDT` : UNAVAILABLE}
            </dd>
            <dd className="text-muted-foreground mt-1 text-xs">
              세션 시작 시점의 거래소 잔고 스냅샷입니다. 주문 수량이 이 값을 기준으로 계산되며 이후
              입출금과 손익은 반영되지 않습니다.
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">진입 스킵</dt>
            <dd className="font-mono" data-testid="live-session-entry-skips">
              {stateLoading
                ? "…"
                : entrySkipCounts.size === 0
                  ? UNAVAILABLE
                  : Array.from(
                      entrySkipCounts,
                      ([reason, count]) =>
                        `${ENTRY_SKIP_REASON_LABEL[reason] ?? reason} ${count}건`,
                    ).join(", ")}
            </dd>
            {hasMarginInsufficient ? (
              <dd className="text-muted-foreground mt-1 text-xs">
                증거금 판정은 수수료·슬리피지를 차감하기 전 자본으로 합니다.
              </dd>
            ) : null}
          </div>
          <div>
            <dt className="text-muted-foreground">강제 청산(시뮬)</dt>
            <dd className="font-mono" data-testid="live-session-liquidations">
              {stateLoading ? "…" : liquidationCount === 0 ? UNAVAILABLE : `${liquidationCount}건`}
            </dd>
            {liquidationCount > 0 ? (
              <dd className="text-muted-foreground mt-1 text-xs">
                증거금 부족 시 시뮬레이터가 청산으로 판정해 청산 주문을 냅니다. 격리 증거금 기준이며
                거래소의 실제 청산과 다를 수 있습니다.
              </dd>
            ) : null}
          </div>
        </dl>
      </div>

      <OutcomeParityPanel sessionId={session.id} />

      {pendingConditionalEntries.length > 0 ? (
        <div className="rounded-md border p-4" data-testid="live-session-pending-orders">
          <h4 className="mb-2 text-sm font-medium">전략이 의도한 조건부 진입</h4>
          {/* ★이 목록의 출처는 엔진 desired set(`last_strategy_state_report.pending_orders`)
              이고 reconcile **이전**에 저장된다. 즉 거래소 등재 여부를 말해주지 않는다 —
              목표 수량이 거래소 눈금 미만이거나 트리거가 이미 돌파됐으면 계획기가 발주를
              걷어내는데 이 목록은 그대로 남는다. "대기 중" 이라고 쓰면 안 나간 주문을
              나간 것처럼 보이게 하는 "되는 척" 이 된다. 등재 확정은 주문 원장이 SSOT. */}
          <p className="text-muted-foreground mb-2 text-xs">
            전략 엔진이 다음 bar 에 걸려고 하는 조건부 진입입니다. 거래소 등재 여부는 주문 원장에서
            확인하세요. 목표 수량이 거래소 최소 눈금 미만이거나 트리거가 이미 돌파된 경우 발주되지
            않습니다.
          </p>
          <ul className="space-y-1 text-sm">
            {pendingConditionalEntries.map((order, index) => (
              <li key={`${order.direction}-${order.stopPrice}-${index}`} className="font-mono">
                {labelOf(LIVE_SIGNAL_DIRECTION_LABEL, order.direction, "live-signal-direction")} ·
                트리거 {order.stopPrice} · 목표 포지션 {order.targetPosition}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* Sprint 27 BL-140 — Activity Timeline (recent N events cumulative chart) */}
      <div className="rounded-md border p-4">
        <div className="mb-3 flex items-center justify-between">
          <h4 className="text-sm font-medium">Activity Timeline</h4>
          <p className="text-muted-foreground text-xs">
            최근 events 누적 entry / close (전체 누적 = BL-140b 후속)
          </p>
        </div>
        {eventsLoading ? (
          <p className="text-muted-foreground text-sm">Loading…</p>
        ) : !events || events.items.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            아직 평가된 signal 이 없습니다. 다음 bar 평가를 기다려주세요.
          </p>
        ) : (
          <ActivityTimelineChart data={timelineData} showEquity={hasEquity} />
        )}
      </div>

      <div className="rounded-md border p-4">
        <h4 className="mb-2 text-sm font-medium">Recent Events</h4>
        {eventsLoading ? (
          <p className="text-muted-foreground text-sm">Loading…</p>
        ) : !events || events.items.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            아직 평가된 signal 이 없습니다. 다음 bar 평가를 기다려주세요.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[480px] text-sm">
              <thead>
                <tr className="text-muted-foreground text-left">
                  <th className="py-1">Bar</th>
                  <th className="py-1">Action</th>
                  <th className="py-1">Direction</th>
                  <th className="py-1">Qty</th>
                  <th className="py-1">Status</th>
                </tr>
              </thead>
              <tbody>
                {events.items.slice(0, 20).map((ev) => {
                  const orderResult = ev.order_state
                    ? statusLabelOf(ORDER_STATE_LABEL, ev.order_state, "liveEvent.order_state")
                    : null;
                  const hasRejectedOrder =
                    ev.order_state === "rejected" || ev.order_state === "cancelled";
                  const statusClass = hasRejectedOrder
                    ? "text-destructive"
                    : ev.status === "dispatched"
                      ? "text-success"
                      : ev.status === "failed"
                        ? "text-destructive"
                        : "text-muted-foreground";

                  return (
                    <tr key={ev.id} className="border-t">
                      <td className="py-1 font-mono">{formatDateTime(ev.bar_time)}</td>
                      <td className="py-1">{ev.action}</td>
                      <td className="py-1">
                        {labelOf(LIVE_SIGNAL_DIRECTION_LABEL, ev.direction, "live-signal-direction")}
                      </td>
                      <td className="py-1 font-mono">{ev.qty}</td>
                      <td className="py-1">
                        <span className={statusClass}>
                          {labelOf(LIVE_SIGNAL_EVENT_STATUS_LABEL, ev.status, "liveEvent.status")}
                          {orderResult ? ` (주문 ${orderResult.label})` : ""}
                        </span>
                      </td>
                    </tr>
                  );
                })}
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
