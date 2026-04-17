'use client';
import { useQuery } from '@tanstack/react-query';
import { fetchOrders } from './api';

export function OrdersPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ['trading', 'orders'],
    queryFn: () => fetchOrders(50),
    refetchInterval: 5000,
  });

  if (isLoading) return <div>Loading...</div>;
  if (!data) return null;

  return (
    <section className="p-4 border rounded">
      <h2 className="font-semibold mb-3">Recent Orders ({data.total})</h2>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left">
            <th>Symbol</th><th>Side</th><th>Qty</th><th>State</th><th>Price</th><th>Error</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((o) => (
            <tr key={o.id} className="border-t">
              <td>{o.symbol}</td>
              <td>{o.side}</td>
              <td>{o.quantity}</td>
              <td>{o.state}</td>
              <td>{o.filled_price ?? '—'}</td>
              <td className="text-red-600">{o.error_message ?? ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
