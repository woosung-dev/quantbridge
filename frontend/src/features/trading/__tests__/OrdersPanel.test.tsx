import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { OrdersPanel } from '../OrdersPanel';

// fetch mock
global.fetch = vi.fn().mockResolvedValue({
  ok: true,
  json: async () => ({
    items: [
      {
        id: 'a0000000-0000-4000-a000-000000000001',
        symbol: 'BTC/USDT',
        side: 'buy',
        state: 'filled',
        quantity: '0.01',
        filled_price: '50000',
        exchange_order_id: 'fixture-1',
        error_message: null,
        created_at: '2026-04-16T10:00:00Z',
      },
    ],
    total: 1,
  }),
});

test('OrdersPanel 최근 주문 50건 렌더', async () => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <OrdersPanel />
    </QueryClientProvider>,
  );
  expect(await screen.findByText('BTC/USDT')).toBeInTheDocument();
  expect(screen.getByText(/filled/i)).toBeInTheDocument();
});
