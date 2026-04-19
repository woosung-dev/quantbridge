import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ExchangeAccountsPanel } from "../components/exchange-accounts-panel";

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: async () => "test-token" }),
}));

vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn().mockResolvedValue({ items: [] }),
  ApiError: class ApiError extends Error {},
}));

test("ExchangeAccountsPanel 빈 상태 — copy + CTA 표시", async () => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <ExchangeAccountsPanel />
    </QueryClientProvider>,
  );

  expect(
    await screen.findByText("연결된 거래소 계정이 없습니다."),
  ).toBeInTheDocument();
  expect(
    screen.getByText("계정을 추가하고 자동매매를 시작하세요."),
  ).toBeInTheDocument();
  const cta = screen.getByRole("button", { name: "계정 추가" });
  expect(cta).toHaveAttribute("href", "/trading");
});
