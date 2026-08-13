// 청산 결과를 다이얼로그 안에 그린다. 판정은 `close-outcome.ts` 가 하고 여기는 표현만 한다.
//
// ★왜 다이얼로그를 열어 두는가. CLI 는 잔량이 남거나 확인에 실패하면 rc 4 로 끝난다 —
//   운영자가 반드시 마주치는 신호다. 화면이 그 자리에서 조용히 닫히면 같은 사건이 rc 0
//   처럼 보인다. 그래서 접수 이후에도 사람이 `확인` 을 누를 때까지 남는다.
// ★접수된 뒤에는 청산 버튼을 감춘다 — 주문은 이미 나갔고 재제출은 오답이다.
"use client";

import { AlertTriangleIcon, HelpCircleIcon } from "lucide-react";

import type { CloseOutcome } from "../close-outcome";
import type { RestingEntryOrder } from "../schemas";

/** CLI 가 `order_link_id` 부재를 찍는 문자와 같다 (`live_session_admin.py:415`). */
const NO_LINK = "-";
const NO_VALUE = "?";

/**
 * 주문 한 건.
 *
 * ★CLI 와 **같은 다섯 필드**를 같은 순서로 낸다. 두 표면이 다른 말을 하면 운영자가
 * 대조할 때 어느 쪽을 믿을지 알 수 없다.
 */
function RestingEntryRow({ order }: { order: RestingEntryOrder }) {
  return (
    <li className="flex flex-col gap-0.5 py-1.5" data-testid="close-resting-entry">
      <span className="flex flex-wrap items-center gap-x-3 gap-y-0.5">
        <strong>{order.side}</strong>
        <span className="mono">수량 {order.qty ?? NO_VALUE}</span>
        <span className="mono">트리거 {order.trigger_price ?? NO_VALUE}</span>
      </span>
      <span className="mono break-words opacity-80">
        {order.order_id} · link {order.order_link_id ?? NO_LINK}
      </span>
    </li>
  );
}

function RestingEntryList({ orders }: { orders: readonly RestingEntryOrder[] }) {
  if (orders.length === 0) return null;
  return (
    <ul className="mt-2 w-full divide-y divide-current/10 text-xs" data-testid="close-resting-list">
      {orders.map((order) => (
        <RestingEntryRow key={order.order_id} order={order} />
      ))}
    </ul>
  );
}

/**
 * 접수된 청산에 붙는 원장 안내.
 *
 * ★CLI 는 이 안내를 rc 4 분기보다 **먼저** 찍는다(`live_session_admin.py:404-408`).
 * 잔량이 남은 회차야말로 체결 검증이 가장 필요한데 경고 뒤에 두면 그 상황에서만
 * 눈에 안 들어온다. 화면도 같은 순서를 지킨다.
 */
function LedgerNote() {
  return (
    <p className="text-xs opacity-80" data-testid="close-ledger-note">
      청산 주문은 원장에 남았습니다. 체결은 비동기이므로 결과는 주문 원장에서 확인하세요.
    </p>
  );
}

export function CloseOutcomePanel({ outcome }: { outcome: CloseOutcome | null }) {
  if (outcome === null || outcome.kind === "clean") return null;

  if (outcome.kind === "blocked_resting") {
    return (
      <div className="notice-inline" role="alert" data-testid="close-outcome-blocked">
        <AlertTriangleIcon aria-hidden="true" />
        <div className="flex w-full flex-col">
          <span>{outcome.message}</span>
          <span className="text-xs opacity-80">
            청산 주문은 내지 않았습니다. 아래 진입 주문을 먼저 처리하세요.
          </span>
          <RestingEntryList orders={outcome.orders} />
        </div>
      </div>
    );
  }

  if (outcome.kind === "accepted_with_resting") {
    return (
      <div className="notice-inline" role="alert" data-testid="close-outcome-resting">
        <AlertTriangleIcon aria-hidden="true" />
        <div className="flex w-full flex-col gap-1">
          <LedgerNote />
          <span>미체결 진입 주문 {outcome.orders.length}건이 남아 있습니다.</span>
          <RestingEntryList orders={outcome.orders} />
        </div>
      </div>
    );
  }

  if (outcome.kind === "accepted_unknown") {
    // ★빈 목록으로 이 상태를 표현하지 않는 것이 이 패널의 존재 이유다. 「잔량 없음」과
    //   「거래소에 못 물어봤다」는 운영자가 취할 행동이 다르다.
    return (
      <div className="notice-inline" role="alert" data-testid="close-outcome-unknown">
        <HelpCircleIcon aria-hidden="true" />
        <div className="flex w-full flex-col gap-1">
          <LedgerNote />
          <span>미체결 진입 주문이 남아 있는지 확인하지 못했습니다.</span>
          <span className="text-xs opacity-80">
            거래소 조회에 실패했습니다. 잔량이 없다는 뜻이 아니므로 거래소에서 직접
            확인하세요.
          </span>
        </div>
      </div>
    );
  }

  return (
    <p className="notice-inline" role="alert" data-testid="close-outcome-failed">
      {outcome.message}
    </p>
  );
}
