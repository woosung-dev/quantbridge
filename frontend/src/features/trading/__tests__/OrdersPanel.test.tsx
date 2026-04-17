import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { OrdersPanel } from "../components/orders-panel";

// Clerk useAuth mock — hooks.ts 에서 getToken 호출.
vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: async () => "test-token" }),
}));

// apiFetch mock — listOrders가 내부적으로 호출하므로 이 레이어에서 고정.
vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn().mockResolvedValue({
    items: [
      {
        id: "a0000000-0000-4000-a000-000000000001",
        symbol: "BTC/USDT",
        side: "buy",
        state: "filled",
        quantity: "0.01",
        filled_price: "50000",
        exchange_order_id: "fixture-1",
        error_message: null,
        created_at: "2026-04-16T10:00:00Z",
      },
    ],
    total: 1,
  }),
  ApiError: class ApiError extends Error {},
}));

test("OrdersPanel 최근 주문 50건 렌더", async () => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <OrdersPanel />
    </QueryClientProvider>,
  );
  expect(await screen.findByText("BTC/USDT")).toBeInTheDocument();
  expect(screen.getByText(/filled/i)).toBeInTheDocument();
});
