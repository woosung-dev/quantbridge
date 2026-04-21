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

test("ExchangeAccountsPanel 빈 상태 — 제목과 '계정 추가' 버튼 표시", async () => {
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
  // 헤더 영역의 '계정 추가' 버튼 (RegisterExchangeAccountDialog)
  const addBtn = screen.getByRole("button", { name: "계정 추가" });
  expect(addBtn).toBeInTheDocument();
  // Dialog 트리거 버튼이므로 href 없음
  expect(addBtn).not.toHaveAttribute("href");
});
