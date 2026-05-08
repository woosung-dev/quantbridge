"use client";

import { ListChecksIcon } from "lucide-react";
import { useIsOrderDisabledByKs, useOrders } from "../hooks";
import { TestOrderDialog } from "./test-order-dialog";
import { TradingEmptyState } from "./trading-empty-state";

/**
 * Sprint 21 BL-093 superset — broker evidence column.
 *
 * exchange_order_id 의 첫 prefix 패턴으로 mock vs real broker 구분:
 *   - null/undefined → "—" (pending, 아직 발송 안 됨)
 *   - "fixture-" prefix → 오렌지 "mock" (Sprint 20 fixture provider hot-fix 산출물)
 *   - 그 외 → 녹색 "broker" + slice(-8) (실제 거래소 ID)
 *
 * codex G.0 round 1 P2: UUID 형식 판정 X (거래소별 id 형식 다름). fixture-* 만
 * 분기하고 나머지는 "broker id present" 로 표시.
 */
function BrokerBadge({ orderId }: { orderId: string | null | undefined }) {
  if (!orderId) {
    return <span className="text-muted-foreground">—</span>;
  }
  const isFixture = orderId.startsWith("fixture-");
  if (isFixture) {
    return (
      <span
        className="text-amber-600 dark:text-amber-400 font-mono text-xs"
        title={`Mock fixture: ${orderId}`}
        data-testid="broker-badge-mock"
      >
        {orderId.slice(-8)} (mock)
      </span>
    );
  }
  return (
    <span
      className="text-emerald-600 dark:text-emerald-400 font-mono text-xs"
      title={`Broker order: ${orderId}`}
      data-testid="broker-badge-real"
    >
      {orderId.slice(-8)} (broker)
    </span>
  );
}

export function OrdersPanel() {
  const { data, isLoading, isError, isFetching } = useOrders(50);
  const ksDisabled = useIsOrderDisabledByKs();
  const isTestOrderEnabled =
    process.env.NEXT_PUBLIC_ENABLE_TEST_ORDER === "true";

  if (isError) {
    return (
      <section className="p-4 border rounded">
        <p className="text-sm text-[color:var(--destructive)]">
          주문 목록을 불러오지 못했습니다.
        </p>
      </section>
    );
  }
  if (isLoading) return <div className="p-4 border rounded">불러오는 중…</div>;
  if (!data) return null;

  return (
    <section className="qb-account-card p-4 border rounded">
      <div className="flex items-center justify-between mb-3 gap-2">
        <h2 className="font-semibold flex items-center gap-2">
          최근 주문 ({data.total})
          {/* Sprint 44 W F3 — refetch / polling 진행 중 subtle dot pulse. 정지 상태는 정적. */}
          {isFetching ? (
            <span
              aria-label="주문 목록 polling 중"
              data-testid="orders-polling-dot"
              className="qb-soft-pulse inline-block size-1.5 rounded-full bg-[color:var(--primary)]"
            />
          ) : null}
        </h2>
        {isTestOrderEnabled ? (
          <div className={ksDisabled ? "pointer-events-none opacity-50" : ""}>
            <TestOrderDialog />
          </div>
        ) : null}
      </div>
      {data.items.length === 0 ? (
        <TradingEmptyState
          icon={ListChecksIcon}
          title="아직 주문이 없습니다."
          description="전략을 실행하면 여기에 표시됩니다."
          ctaLabel="전략 보기"
          ctaHref="/strategies"
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[680px]">
            <thead>
              <tr className="text-left">
                <th>Symbol</th>
                <th>Side</th>
                <th>Qty</th>
                <th>State</th>
                <th>Price</th>
                <th>Broker ID</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((o) => (
                <tr key={o.id} className="border-t">
                  <td>{o.symbol}</td>
                  <td>{o.side}</td>
                  <td>{o.quantity}</td>
                  <td>{o.state}</td>
                  <td>{o.filled_price ?? "—"}</td>
                  <td>
                    <BrokerBadge orderId={o.exchange_order_id} />
                  </td>
                  <td className="text-red-600">{o.error_message ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
