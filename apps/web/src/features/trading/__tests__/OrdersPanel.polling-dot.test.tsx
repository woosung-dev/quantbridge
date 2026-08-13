// Sprint 44 W F3 — OrdersPanel heading 옆 polling indicator dot 노출 검증
// (data 도착 직후 isFetching=false 라도 OK — 본 테스트는 dot 미노출 케이스만 단순 검증)
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, vi } from "vitest";

import { OrdersPanel } from "../components/orders-panel";

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: async () => "test-token" }),
}));

const apiFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api-client", () => ({
  apiFetch: apiFetchMock,
  ApiError: class ApiError extends Error {},
}));

afterEach(() => {
  apiFetchMock.mockReset();
});

test("OrdersPanel: 응답 도착 후 polling indicator dot 미노출 (idle 상태)", async () => {
  apiFetchMock.mockResolvedValue({
    items: [
      {
        id: "a0000000-0000-4000-a000-000000000001",
        symbol: "BTC/USDT",
        side: "buy",
        state: "filled",
        quantity: "0.01",
        filled_price: "50000",
        error_message: null,
        created_at: "2026-04-16T10:00:00Z",
        exchange_order_id: null,
      },
    ],
    total: 1,
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <OrdersPanel />
    </QueryClientProvider>,
  );

  // 데이터 도착 후 fetching 끝나면 dot 사라짐 (refetch 진행 중에만 노출)
  expect(await screen.findByText("BTC/USDT")).toBeInTheDocument();
  await waitFor(() => {
    expect(screen.queryByTestId("orders-polling-dot")).not.toBeInTheDocument();
  });
});
