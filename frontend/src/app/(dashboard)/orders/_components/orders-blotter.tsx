"use client";

// 주문 원장(Blotter) — C 디자인 언어 이식 (W3-D). 프로토타입 screen-11-orders 의 시맨틱 CSS·구조를
// 소비하되, 열은 실데이터(Order 스키마)가 받치는 것만 그린다. 취소 API는 완비되어 액션 열을 다시
// 렌더한다. §4.9 미백킹 값(브로커·모의 출처 배지, 세션 ID)은 렌더하지 않는다. 상태 라벨·톤·무데이터 title 은 용어
// SSOT(features/trading/labels.ts)에서만 온다(원시 enum 렌더 금지 — no-raw-enum-labels 가드).

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangleIcon,
  CheckIcon,
  ClockIcon,
  DownloadIcon,
  InboxIcon,
  InfoIcon,
  RefreshCwIcon,
} from "lucide-react";

import { StateBox } from "@/components/state-box";
import { downloadCsv, formatDate, formatTimeSeconds } from "@/features/backtest/utils";
import { ACTIVE_ORDER_STATES, useCancelOrder, useOrders } from "@/features/trading/hooks";
import {
  filledPriceEmptyReason,
  ORDER_CANCEL_ACTION,
  ORDER_EMPTY_REASON,
  ORDER_EMPTY_STATE,
  ORDER_ERROR_NONE_TITLE,
  ORDER_FILTER_HINT,
  ORDER_FILLED_QUANTITY,
  ORDER_FLAG_HINT,
  ORDER_FLAG_LABEL,
  ORDER_LEDGER_COPY,
  ORDER_LIQUIDATION_DELEGATION_NOTE,
  ORDER_NUMBER_NOTE,
  ORDER_POLLING_NOTE,
  ORDER_REALIZED_PNL_SOURCE_HINT,
  ORDER_REALIZED_PNL_SOURCE_LABEL,
  ORDER_SIDE_HEADER_HINT,
  ORDER_SIDE_LABEL,
  ORDER_STATE_FILTER_LABEL,
  ORDER_STATE_LABEL,
  ORDER_TABLE_HEADER,
  ORDER_TRAILING_STOP_TITLE,
  type OrderStateFilter,
} from "@/features/trading/labels";
import type { Order } from "@/features/trading/schemas";
import { CHIP_TONE_CLASS, EMPTY_CELL } from "@/lib/labels";

const FETCH_LIMIT = 200;
const PAGE_SIZE = 10;
// 원장 조회 엔드포인트 — 에러 상태에 실제 경로를 노출한다 (프로토타입 state-code 관례).
const LIST_ENDPOINT = "GET /api/v1/orders";

const STATE_FILTERS: readonly OrderStateFilter[] = ["all", "filled", "open", "closed"];

function matchesFilter(state: Order["state"], f: OrderStateFilter): boolean {
  if (f === "all") return true;
  if (f === "filled") return state === "filled";
  if (f === "open") return state === "pending" || state === "submitted";
  return state === "cancelled" || state === "rejected";
}

// 시각 셀 — 시(초 단위)를 본문에, 날짜를 보조 줄(cell-sub)에 둔다. 프로토타입 21:06:12 / 2026-04-14 관례.
// UTC 고정(formatTimeSeconds/formatDate SSOT) — 로컬 타임존 잔재를 없애 서버·클라이언트 렌더가 일치한다.
function formatOrderTime(iso: string): { time: string; date: string } {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return { time: iso, date: "" };
  return { time: formatTimeSeconds(iso), date: formatDate(iso) };
}

function signedPct(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

// 익절·손절 절대가와 체결가 대비 거리를 함께 인쇄한다. 체결가가 없으면 거리를 만들지 않는다(§4.6).
function buildDistanceSub(
  filledPrice: string,
  takeProfit: string | null,
  stopLoss: string | null,
): string | null {
  const base = Number(filledPrice);
  if (!Number.isFinite(base) || base === 0) return null;
  const parts: string[] = [];
  if (takeProfit != null) {
    const tp = Number(takeProfit);
    if (Number.isFinite(tp)) parts.push(signedPct((tp / base - 1) * 100));
  }
  if (stopLoss != null) {
    const sl = Number(stopLoss);
    if (Number.isFinite(sl)) parts.push(signedPct((sl / base - 1) * 100));
  }
  if (parts.length === 0) return null;
  return `체결가 ${filledPrice} 대비 ${parts.join(" / ")}`;
}

// CSV 헤더는 ORDER_TABLE_HEADER SSOT 에서 온다. 액션 열은 데이터가 아니라 UI 라 제외한다.
const CSV_HEADER = [
  ORDER_TABLE_HEADER.createdAt,
  ORDER_TABLE_HEADER.symbol,
  ORDER_TABLE_HEADER.side,
  ORDER_TABLE_HEADER.quantity,
  ORDER_TABLE_HEADER.filledPrice,
  ORDER_TABLE_HEADER.filledQuantity,
  ORDER_TABLE_HEADER.realizedPnl,
  ORDER_TABLE_HEADER.state,
  ORDER_TABLE_HEADER.takeProfitStopLoss,
  ORDER_TABLE_HEADER.brokerOrderId,
  ORDER_TABLE_HEADER.errorMessage,
] as const;

function tpSlText(o: Order): string {
  const parts: string[] = [];
  if (o.take_profit != null) parts.push(`익절 ${o.take_profit}`);
  if (o.stop_loss != null) parts.push(`손절 ${o.stop_loss}`);
  if (o.trailing_stop != null) parts.push(`추적손절 ${o.trailing_stop}`);
  return parts.join(" · ");
}

function ordersToCsv(orders: readonly Order[]): string {
  const rows = orders.map((o) => [
    formatOrderTime(o.created_at).time,
    o.symbol,
    ORDER_SIDE_LABEL[o.side] + (o.reduce_only ? ` (${ORDER_FLAG_LABEL.reduceOnly})` : ""),
    o.quantity,
    o.filled_price ?? "",
    o.filled_quantity ?? "",
    o.realized_pnl ?? "",
    ORDER_STATE_LABEL[o.state].label,
    tpSlText(o),
    o.exchange_order_id != null ? o.exchange_order_id.slice(-8) : "",
    o.error_message ?? "",
  ]);
  return [CSV_HEADER as readonly string[], ...rows]
    .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))
    .join("\n");
}

interface StateCounts {
  pending: number;
  submitted: number;
  filled: number;
  cancelled: number;
  rejected: number;
}

function buildStateCounts(orders: readonly Order[]): StateCounts {
  const c: StateCounts = { pending: 0, submitted: 0, filled: 0, cancelled: 0, rejected: 0 };
  for (const o of orders) c[o.state] += 1;
  return c;
}

export function OrdersBlotter() {
  const ordersQ = useOrders(FETCH_LIMIT);
  const cancelOrder = useCancelOrder();
  const [filter, setFilter] = useState<OrderStateFilter>("all");
  const [page, setPage] = useState(0);

  const { data, isLoading, isError, error, refetch } = ordersQ;

  const orderItems = data?.items;
  // H-1 정합 — React Query data.items 참조 자체를 memoize 해 아래 파생 useMemo 의 dep 를 안정화한다.
  const allOrders = useMemo<readonly Order[]>(() => {
    const items = orderItems ?? [];
    return [...items].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
  }, [orderItems]);

  const total = data?.total ?? allOrders.length;
  const hasMorePages = total > allOrders.length;

  const counts = useMemo(() => buildStateCounts(allOrders), [allOrders]);
  const openCount = counts.pending + counts.submitted;

  const filterCounts: Record<OrderStateFilter, number> = {
    all: allOrders.length,
    filled: counts.filled,
    open: openCount,
    closed: counts.cancelled + counts.rejected,
  };

  const filtered = useMemo(
    () => allOrders.filter((o) => matchesFilter(o.state, filter)),
    [allOrders, filter],
  );

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const pageStart = safePage * PAGE_SIZE;
  const pageRows = filtered.slice(pageStart, pageStart + PAGE_SIZE);

  const handleFilter = (f: OrderStateFilter) => {
    setFilter(f);
    setPage(0);
  };

  const handleExport = () => {
    const ts = new Date().toISOString().replace(/[^\d]/g, "").slice(0, 14);
    downloadCsv(`orders-${ts}.csv`, ordersToCsv(filtered));
  };

  const fillRatio = allOrders.length > 0 ? (counts.filled / allOrders.length) * 100 : 0;

  // 헤더 라벨은 스칼라로 푼다. ORDER_TABLE_HEADER.state 는 enum 값이 아닌 헤더 문자열이지만,
  // no-raw-enum-labels 가드가 `.state` 로 끝나는 JSX 멤버 체인을 전부 잡으므로 우회한다(backtest-list 관례).
  const {
    createdAt: hCreatedAt,
    symbol: hSymbol,
    side: hSide,
    quantity: hQuantity,
    filledPrice: hFilledPrice,
    filledQuantity: hFilledQuantity,
    realizedPnl: hRealizedPnl,
    state: hState,
    takeProfitStopLoss: hTpSl,
    brokerOrderId: hBrokerOrderId,
    errorMessage: hErrorMessage,
    action: hAction,
  } = ORDER_TABLE_HEADER;

  return (
    <main className="page">
      {/* ===== 헤더 카드 ===== */}
      <section className="card" aria-label="주문 개요">
        <div className="report">
          <div>
            <h1 className="report-title">주문</h1>
            <div className="report-meta">
              <span className="chip">주문 {total}건</span>
              <span className="chip">Bybit</span>
              <span className="chip accent">미체결 {openCount}건</span>
            </div>
            <p className="poll-line">
              <ClockIcon aria-hidden="true" />
              <span>{ORDER_POLLING_NOTE}</span>
              <button className="btn btn-ghost poll-btn" type="button" onClick={() => refetch()}>
                <RefreshCwIcon aria-hidden="true" />
                지금 새로고침
              </button>
            </p>
          </div>
          <div className="report-actions">
            <button
              className="btn btn-ghost"
              type="button"
              onClick={handleExport}
              disabled={filtered.length === 0}
            >
              <DownloadIcon aria-hidden="true" />
              CSV 내보내기
            </button>
            <button className="btn" type="button" onClick={() => refetch()}>
              <RefreshCwIcon aria-hidden="true" />
              새로고침
            </button>
          </div>
        </div>
      </section>

      {/* ===== 01 상태 필터 ===== */}
      <section className="section" aria-label="상태 필터">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">01</span> {ORDER_LEDGER_COPY.filterEyebrow}
          </p>
          <h2 className="section-title">{ORDER_LEDGER_COPY.filterTitle}</h2>
          <p className="section-desc">{ORDER_LEDGER_COPY.filterDesc}</p>
        </header>

        <div className="card">
          <div className="card-body">
            {/* 탭이 아니라 상호배타 토글 — role=group + aria-pressed (프로토타입 §3-6 교정). */}
            <div className="tabs" role="group" aria-label="주문 상태 필터">
              {STATE_FILTERS.map((f) => {
                const active = f === filter;
                return (
                  <button
                    key={f}
                    type="button"
                    className={"tab" + (active ? " active" : "")}
                    aria-pressed={active}
                    data-testid={`order-filter-${f}`}
                    onClick={() => handleFilter(f)}
                  >
                    {ORDER_STATE_FILTER_LABEL[f]} <span className="mono">{filterCounts[f]}</span>
                  </button>
                );
              })}
            </div>
            <p
              className="filter-state"
              role="status"
              aria-live="polite"
              data-testid="order-filter-state"
            >
              지금 보고 있는 상태는 <span className="mono">{ORDER_STATE_FILTER_LABEL[filter]}</span>{" "}
              입니다. 조건에 맞는 <span className="mono">{filtered.length}</span>건 가운데 이
              페이지에 실린 <span className="mono">{pageRows.length}</span>건이 아래 표에 보입니다.
            </p>
            <p className="filter-hint">{ORDER_FILTER_HINT.scope}</p>
            <p className="filter-hint">{ORDER_FILTER_HINT.navCount}</p>
          </div>
        </div>
      </section>

      {/* ===== 02 목록 ===== */}
      <section className="section" aria-label="주문 원장">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">02</span> {ORDER_LEDGER_COPY.listEyebrow}
          </p>
          <h2 className="section-title">
            {ORDER_LEDGER_COPY.cardTitle} {total}건
          </h2>
          <p className="section-desc">{ORDER_LEDGER_COPY.listDescription}</p>
        </header>

        <div className="card">
          <div className="card-head">
            <div>
              <h3 className="card-title">{ORDER_LEDGER_COPY.cardTitle}</h3>
              <p className="card-sub">
                {allOrders.length}건 표시 · 시각 내림차순
                {hasMorePages ? ` · 전체 ${total}건 중` : ""}
              </p>
            </div>
          </div>

          <p className="orders-summary">
            <span className="mono">{total}</span>건 · {hasMorePages ? "이 페이지 기준 " : ""}체결{" "}
            <span className="mono">{counts.filled}</span> · 대기{" "}
            <span className="mono">{counts.pending}</span> · 전송{" "}
            <span className="mono">{counts.submitted}</span> · 취소{" "}
            <span className="mono">{counts.cancelled}</span> · 거부{" "}
            <span className="mono">{counts.rejected}</span>
          </p>

          <div className="fill-ratio">
            <span
              className="meter"
              role="img"
              aria-label={`받아온 ${allOrders.length}건 가운데 체결 ${counts.filled}건, ${fillRatio.toFixed(1)} 퍼센트`}
            >
              <span style={{ width: `${fillRatio}%` }} />
            </span>
            <span className="fill-ratio-label">
              체결 <span className="mono">{counts.filled}</span>건 / 받아온{" "}
              <span className="mono">{allOrders.length}</span>건 ={" "}
              <span className="mono">{fillRatio.toFixed(1)}%</span>
            </span>
          </div>

          {isLoading ? (
            <ListSkeleton />
          ) : isError ? (
            <div className="card-body">
              <StateBox
                tone="failed"
                testId="order-error"
                icon={<AlertTriangleIcon />}
                title="원장을 다시 받아오지 못했습니다."
                body={error ? error.message : "네트워크 또는 서버 상태 일시적 오류일 수 있습니다."}
                code={`${LIST_ENDPOINT} · 500`}
              >
                <button className="btn btn-ghost" type="button" onClick={() => refetch()}>
                  <RefreshCwIcon aria-hidden="true" />
                  다시 시도
                </button>
              </StateBox>
            </div>
          ) : filtered.length === 0 ? (
            <div className="card-body">
              <StateBox
                testId="order-empty"
                icon={<InboxIcon />}
                title={
                  allOrders.length === 0
                    ? ORDER_EMPTY_STATE.headline
                    : "해당 상태의 주문이 없습니다."
                }
                body={
                  allOrders.length === 0
                    ? ORDER_EMPTY_STATE.description
                    : "다른 상태를 선택하거나 트레이딩 코크핏에서 주문을 실행하세요."
                }
              >
                {allOrders.length === 0 ? (
                  <Link className="btn btn-ghost btn-xs" href="/trading">
                    트레이딩 코크핏 열기
                  </Link>
                ) : (
                  <button
                    className="btn btn-ghost btn-xs"
                    type="button"
                    onClick={() => handleFilter("all")}
                  >
                    전체 보기
                  </button>
                )}
              </StateBox>
            </div>
          ) : (
            <>
              <div className="table-wrap">
                <table
                  className="trades orders-table"
                  aria-label={`주문 원장 ${filtered.length}건, 시각 내림차순`}
                >
                  <thead>
                    <tr>
                      <th scope="col">{hCreatedAt}</th>
                      <th scope="col">{hSymbol}</th>
                      <th scope="col" title={ORDER_SIDE_HEADER_HINT}>
                        {hSide}
                      </th>
                      <th scope="col" className="num">
                        {hQuantity}
                      </th>
                      <th scope="col" className="num">
                        {hFilledPrice}
                      </th>
                      <th scope="col" className="num">
                        {hFilledQuantity}
                      </th>
                      <th scope="col" className="num">
                        {hRealizedPnl}
                      </th>
                      <th scope="col" className="col-state">
                        {hState}
                      </th>
                      <th scope="col">{hTpSl}</th>
                      <th scope="col">{hBrokerOrderId}</th>
                      <th scope="col">{hErrorMessage}</th>
                      <th scope="col">{hAction}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pageRows.map((o) => (
                      <OrderRow
                        key={o.id}
                        order={o}
                        onCancel={cancelOrder.mutate}
                        cancellingOrderId={
                          cancelOrder.isPending ? cancelOrder.variables : undefined
                        }
                      />
                    ))}
                  </tbody>
                </table>
              </div>

              <p className="chart-note table-foot-note">
                <InfoIcon aria-hidden="true" />
                <span>{ORDER_LIQUIDATION_DELEGATION_NOTE}</span>
              </p>
              <p className="chart-note table-foot-note">
                <InfoIcon aria-hidden="true" />
                <span>{ORDER_NUMBER_NOTE}</span>
              </p>

              <div className="pager">
                <span>
                  {filtered.length}건 중 {filtered.length === 0 ? 0 : pageStart + 1}번부터{" "}
                  {Math.min(pageStart + PAGE_SIZE, filtered.length)}번까지
                </span>
                <span className="pager-nums">
                  <button
                    className="pg"
                    type="button"
                    aria-label="이전 페이지"
                    disabled={safePage === 0}
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                  >
                    ‹
                  </button>
                  {Array.from({ length: pageCount }).map((_, i) => (
                    <button
                      key={i}
                      className={"pg" + (i === safePage ? " active" : "")}
                      type="button"
                      aria-current={i === safePage ? "page" : undefined}
                      onClick={() => setPage(i)}
                    >
                      {i + 1}
                    </button>
                  ))}
                  <button
                    className="pg"
                    type="button"
                    aria-label="다음 페이지"
                    disabled={safePage >= pageCount - 1}
                    onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                  >
                    ›
                  </button>
                </span>
              </div>
            </>
          )}
        </div>
      </section>
    </main>
  );
}

// 원장 한 행 — 12개 backed 열. 라벨·톤·무데이터 title 은 전부 용어 SSOT 에서 온다.
function OrderRow({
  order: o,
  onCancel,
  cancellingOrderId,
}: {
  order: Order;
  onCancel: (orderId: string) => void;
  cancellingOrderId: string | undefined;
}) {
  const { label, tone, showCheckIcon } = ORDER_STATE_LABEL[o.state];
  const { time, date } = formatOrderTime(o.created_at);
  const isPartialFill = o.filled_quantity != null && Number(o.filled_quantity) < Number(o.quantity);
  const realizedPnl = o.realized_pnl == null ? null : Number(o.realized_pnl);
  const realizedPnlTone =
    realizedPnl != null && Number.isFinite(realizedPnl)
      ? realizedPnl < 0
        ? "neg"
        : realizedPnl > 0
          ? "pos"
          : ""
      : "";
  const pnlSource = o.realized_pnl_synced_at != null ? "confirmed" : "estimated";
  return (
    <tr data-state={o.state} data-testid={`order-row-${o.id}`}>
      <td className="mono-l">
        {time}
        {date ? <span className="cell-sub">{date}</span> : null}
      </td>
      <td className="mono-l">{o.symbol}</td>
      <td className="dir-cell">
        <span className={"order-side " + o.side}>{ORDER_SIDE_LABEL[o.side]}</span>
        {o.reduce_only ? (
          <span className="chip chip-xs" title={ORDER_FLAG_HINT.reduceOnly}>
            {ORDER_FLAG_LABEL.reduceOnly}
          </span>
        ) : null}
      </td>
      <td className="num">{o.quantity}</td>
      {o.filled_price != null ? (
        <td className="num">{o.filled_price}</td>
      ) : (
        <td className="num dim" title={filledPriceEmptyReason(o.state)}>
          {EMPTY_CELL}
        </td>
      )}
      {o.filled_quantity != null ? (
        <td className="num">
          {o.filled_quantity}
          {isPartialFill ? (
            <>
              {" "}
              <span
                className="chip chip-xs"
                title={ORDER_FILLED_QUANTITY.partialTitle(o.quantity, o.filled_quantity)}
              >
                {ORDER_FILLED_QUANTITY.partial}
              </span>
            </>
          ) : null}
        </td>
      ) : (
        <td className="num dim">{EMPTY_CELL}</td>
      )}
      {o.realized_pnl != null ? (
        <td className={`num ${realizedPnlTone}`}>
          {o.realized_pnl}{" "}
          <span className="chip chip-xs" title={ORDER_REALIZED_PNL_SOURCE_HINT[pnlSource]}>
            {ORDER_REALIZED_PNL_SOURCE_LABEL[pnlSource]}
          </span>
        </td>
      ) : (
        <td className="num dim">{EMPTY_CELL}</td>
      )}
      <td className="col-state">
        <span className={CHIP_TONE_CLASS[tone]}>
          {showCheckIcon ? <CheckIcon aria-hidden="true" /> : null}
          {label}
        </span>
      </td>
      <TakeProfitStopLossCell order={o} />
      {o.exchange_order_id != null ? (
        <td className="mono-l">{o.exchange_order_id.slice(-8)}</td>
      ) : (
        <td
          className="mono-l dim"
          title={
            o.state === "rejected"
              ? ORDER_EMPTY_REASON.brokerIdRejected
              : ORDER_EMPTY_REASON.brokerIdNotSent
          }
        >
          {EMPTY_CELL}
        </td>
      )}
      {o.error_message != null ? (
        <td className="col-error">{o.error_message}</td>
      ) : (
        <td className="col-error dim" title={ORDER_ERROR_NONE_TITLE[o.state]}>
          {EMPTY_CELL}
        </td>
      )}
      {ACTIVE_ORDER_STATES.has(o.state) ? (
        <td>
          <button
            className="btn btn-xs btn-danger"
            type="button"
            title={ORDER_CANCEL_ACTION.title[o.state]}
            disabled={cancellingOrderId === o.id}
            onClick={() => onCancel(o.id)}
          >
            {ORDER_CANCEL_ACTION.label}
          </button>
        </td>
      ) : (
        <td className="dim" title={ORDER_CANCEL_ACTION.title[o.state]}>
          {EMPTY_CELL}
        </td>
      )}
    </tr>
  );
}

function TakeProfitStopLossCell({ order: o }: { order: Order }) {
  const hasBound = o.take_profit != null || o.stop_loss != null || o.trailing_stop != null;
  if (!hasBound) {
    const title =
      o.state === "rejected"
        ? ORDER_EMPTY_REASON.takeProfitStopLossRejected
        : ORDER_EMPTY_REASON.takeProfitStopLossNone;
    return (
      <td className="col-tpsl dim" title={title}>
        {EMPTY_CELL}
      </td>
    );
  }

  // 추적손절 단독 — 절대가가 아니라 거리 오프셋이라 체결가 대비 퍼센트를 만들지 않는다.
  if (o.trailing_stop != null && o.take_profit == null && o.stop_loss == null) {
    return (
      <td className="col-tpsl mono-l" title={ORDER_TRAILING_STOP_TITLE}>
        추적손절 {o.trailing_stop}
      </td>
    );
  }

  const parts: string[] = [];
  if (o.take_profit != null) parts.push(`익절 ${o.take_profit}`);
  if (o.stop_loss != null) parts.push(`손절 ${o.stop_loss}`);
  if (o.trailing_stop != null) parts.push(`추적손절 ${o.trailing_stop}`);
  const sub =
    o.filled_price != null ? buildDistanceSub(o.filled_price, o.take_profit, o.stop_loss) : null;

  return (
    <td className="col-tpsl mono-l">
      {parts.join(" · ")}
      {sub != null ? <span className="cell-sub">{sub}</span> : null}
    </td>
  );
}

// 다음 페이지를 불러오는 동안의 스켈레톤 — 프로토타입 aria-busy tbody 관례 (.sk .sk-cell). 12열.
function ListSkeleton() {
  return (
    <div className="table-wrap" data-testid="order-skeleton" aria-hidden="true">
      <table className="trades orders-table">
        <tbody>
          {Array.from({ length: 6 }).map((_, i) => (
            <tr key={i}>
              {Array.from({ length: 12 }).map((__, j) => (
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
