import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { OrdersPanel } from "../components/orders-panel";

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: async () => "test-token" }),
}));

vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  ApiError: class ApiError extends Error {},
}));

test("OrdersPanel 빈 상태 — copy + CTA 표시", async () => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <OrdersPanel />
    </QueryClientProvider>,
  );

  expect(
    await screen.findByText("아직 주문이 없습니다."),
  ).toBeInTheDocument();
  expect(
    screen.getByText("전략을 실행하면 여기에 표시됩니다."),
  ).toBeInTheDocument();
  const cta = screen.getByRole("button", { name: "전략 보기" });
  expect(cta).toHaveAttribute("href", "/strategies");
});
