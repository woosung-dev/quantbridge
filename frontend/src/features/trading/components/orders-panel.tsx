"use client";

import { useOrders } from "../hooks";

export function OrdersPanel() {
  const { data, isLoading, isError } = useOrders(50);

  if (isError) {
    return (
      <section className="p-4 border rounded">
        <p className="text-sm text-[color:var(--destructive)]">
          주문 목록을 불러오지 못했습니다.
        </p>
      </section>
    );
  }
  if (isLoading) return <div className="p-4 border rounded">Loading...</div>;
  if (!data) return null;

  return (
    <section className="p-4 border rounded">
      <h2 className="font-semibold mb-3">Recent Orders ({data.total})</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm min-w-[600px]">
          <thead>
            <tr className="text-left">
              <th>Symbol</th>
              <th>Side</th>
              <th>Qty</th>
              <th>State</th>
              <th>Price</th>
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
                <td className="text-red-600">{o.error_message ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
