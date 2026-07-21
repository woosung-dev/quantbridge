"use client";

// 주문 원장 패널 — C 디자인 언어 이식 (S8). 프로토타입 screen-01 §05 의 공용 .card/.trades
// 시맨틱 CSS 를 소비한다. 주문 방향(side)·상태(state)는 원시 enum 을 그대로 인쇄하지 않고
// features/trading/labels.ts 의 용어 SSOT(ORDER_SIDE_LABEL / ORDER_STATE_LABEL)를 거친다
// (S4 인계 — 원시 enum JSX 자식 렌더 금지). 4상태(로딩/에러/빈/채움)를 실제로 렌더한다.

import Link from "next/link";
import {
  AlertTriangleIcon,
  CheckIcon,
  InboxIcon,
  RefreshCwIcon,
} from "lucide-react";

import { StateBox } from "@/components/state-box";
import { CHIP_TONE_CLASS, EMPTY_CELL, statusLabelOf } from "@/lib/labels";

import { useIsOrderDisabledByKs, useOrders } from "../hooks";
import { ORDER_SIDE_LABEL, ORDER_STATE_LABEL } from "../labels";
import { TestOrderDialog } from "./test-order-dialog";

// 주문 목록 조회 엔드포인트 — 에러 상태에 실제 경로를 노출한다 (프로토타입 state-code 관례).
const ORDERS_ENDPOINT = "GET /api/v1/orders";

/**
 * Sprint 21 BL-093 superset — broker evidence column.
 *   - null/undefined → EMPTY_CELL (아직 발송 안 됨)
 *   - "fixture-" prefix → warn 톤 "mock" (fixture provider 산출물)
 *   - 그 외 → bull 톤 "broker" + slice(-8) (실제 거래소 ID)
 * codex G.0 P2: UUID 형식 판정 X. fixture-* 만 분기하고 나머지는 "broker id present".
 */
function BrokerBadge({ orderId }: { orderId: string | null | undefined }) {
  if (!orderId) {
    return <span className="dim">{EMPTY_CELL}</span>;
  }
  const isFixture = orderId.startsWith("fixture-");
  if (isFixture) {
    return (
      <span
        className="mono evi-mock"
        title={`Mock fixture: ${orderId}`}
        data-testid="broker-badge-mock"
      >
        {orderId.slice(-8)} (mock)
      </span>
    );
  }
  return (
    <span
      className="mono evi-broker"
      title={`Broker order: ${orderId}`}
      data-testid="broker-badge-real"
    >
      {orderId.slice(-8)} (broker)
    </span>
  );
}

export function OrdersPanel() {
  const { data, isLoading, isError, isFetching, refetch } = useOrders(50);
  const ksDisabled = useIsOrderDisabledByKs();
  const isTestOrderEnabled =
    process.env.NEXT_PUBLIC_ENABLE_TEST_ORDER === "true";

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h3 className="card-title">
            주문 원장{data ? ` (${data.total})` : ""}
            {/* Sprint 44 W F3 — refetch / polling 진행 중 subtle dot pulse. 정지 상태는 정적. */}
            {isFetching ? (
              <span
                aria-label="주문 목록 polling 중"
                data-testid="orders-polling-dot"
                className="polling-dot"
              />
            ) : null}
          </h3>
          <p className="card-sub">
            라이브·데모 세션이 실행한 주문을 최신순으로 최대 50건 담습니다.
          </p>
        </div>
        {isTestOrderEnabled ? (
          <div
            className={
              "chart-head-actions" +
              (ksDisabled ? " pointer-events-none opacity-50" : "")
            }
          >
            <TestOrderDialog />
          </div>
        ) : null}
      </div>

      {isLoading ? (
        <OrdersSkeleton />
      ) : isError ? (
        <div className="card-body">
          <StateBox
            tone="failed"
            testId="orders-error"
            icon={<AlertTriangleIcon />}
            title="주문 목록을 불러오지 못했습니다."
            body="네트워크 또는 서버 상태 일시적 오류일 수 있습니다. 주문을 내기 전에 상태를 확인하세요."
            code={ORDERS_ENDPOINT}
          >
            <button className="btn btn-ghost" type="button" onClick={() => refetch()}>
              <RefreshCwIcon aria-hidden="true" />
              다시 시도
            </button>
          </StateBox>
        </div>
      ) : !data || data.items.length === 0 ? (
        <div className="card-body">
          <StateBox
            testId="orders-empty"
            icon={<InboxIcon />}
            title="아직 주문이 없습니다."
            body="전략을 실행하면 여기에 표시됩니다."
          >
            <Link className="btn btn-primary btn-xs" href="/strategies">
              전략 보기
            </Link>
          </StateBox>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="trades" aria-label={`주문 원장 ${data.items.length}건`}>
            <thead>
              <tr>
                <th scope="col">심볼</th>
                <th scope="col">주문 방향</th>
                <th scope="col" className="num">
                  수량
                </th>
                <th scope="col" className="col-status">
                  상태
                </th>
                <th scope="col" className="num">
                  체결가
                </th>
                {/* Wave 2 — bracket TP/SL + 청산가(graceful) */}
                <th scope="col">익절·손절</th>
                <th scope="col" className="num">
                  청산가
                </th>
                <th scope="col">거래소 주문번호</th>
                <th scope="col">오류</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((o) => {
                // 라벨·톤은 S4 용어 SSOT 에서만 온다 (원시 enum 렌더 금지).
                const { label, tone, showCheckIcon } = statusLabelOf(
                  ORDER_STATE_LABEL,
                  o.state,
                  "order.state",
                );
                return (
                  <tr key={o.id}>
                    <td className="mono-l">{o.symbol}</td>
                    <td>{ORDER_SIDE_LABEL[o.side]}</td>
                    <td className="num">{o.quantity}</td>
                    <td className="col-status">
                      <span className={CHIP_TONE_CLASS[tone]}>
                        {showCheckIcon ? <CheckIcon aria-hidden="true" /> : null}
                        {label}
                      </span>
                    </td>
                    <td className="num">{o.filled_price ?? EMPTY_CELL}</td>
                    <td data-testid="tpsl-cell" className="mono-l">
                      {/* STEP B — 트레일링 의도(Order.trailing_stop)도 표출. 체결 후
                          place_trailing_stop 가 거래소에 부착(별도 주문 아님). */}
                      {o.take_profit || o.stop_loss || o.trailing_stop
                        ? `${o.take_profit ?? EMPTY_CELL} / ${o.stop_loss ?? EMPTY_CELL}${
                            o.trailing_stop ? ` / trail ${o.trailing_stop}` : ""
                          }`
                        : EMPTY_CELL}
                    </td>
                    {/* 청산가 graceful-empty (의도적). 주문 목록은 "열린 포지션" 상태를
                        노출하지 않는다 — filled 주문이 곧 열린 포지션을 의미하지 않으며(이미
                        청산/반대매매됐을 수 있음), positions API 도 부재. 과거 주문에 라이브
                        위험 수준처럼 보이는 청산가를 찍으면 오해 유발(Surface Trust 위반). */}
                    <td data-testid="liquidation-cell" className="num dim">
                      {EMPTY_CELL}
                    </td>
                    <td>
                      <BrokerBadge orderId={o.exchange_order_id} />
                    </td>
                    <td className="ord-error">{o.error_message ?? ""}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// 폴링 중 스켈레톤 — S5 backtest-list ListSkeleton 관례(.sk .sk-cell).
function OrdersSkeleton() {
  return (
    <div className="table-wrap" data-testid="orders-skeleton" aria-hidden="true">
      <table className="trades">
        <tbody>
          {Array.from({ length: 5 }).map((_, i) => (
            <tr key={i}>
              {Array.from({ length: 9 }).map((__, j) => (
                <td key={j}>
                  <span className="sk sk-cell" />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
