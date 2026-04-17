'use client';
import { useQuery } from '@tanstack/react-query';
import { fetchExchangeAccounts } from './api';

export function ExchangeAccountsPanel() {
  const { data } = useQuery({
    queryKey: ['trading', 'accounts'],
    queryFn: fetchExchangeAccounts,
  });
  if (!data) return null;

  return (
    <section className="p-4 border rounded">
      <h2 className="font-semibold mb-3">Exchange Accounts</h2>
      <table className="w-full text-sm">
        <thead>
          <tr><th>Exchange</th><th>Mode</th><th>Label</th><th>API Key</th></tr>
        </thead>
        <tbody>
          {data.map((a) => (
            <tr key={a.id} className="border-t">
              <td>{a.exchange}</td>
              <td>{a.mode}</td>
              <td>{a.label ?? '—'}</td>
              <td className="font-mono">{a.api_key_masked}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
