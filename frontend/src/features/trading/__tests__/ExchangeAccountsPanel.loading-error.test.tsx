// Sprint 14 Phase B-2 — ExchangeAccountsPanel 의 loading skeleton + error retry 분기.
// 기존 `if (!data) return null` (빈 화면) → skeleton + retry 버튼으로 명시화.
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

const refetchMock = vi.fn();
let mockState: {
  data: unknown;
  isLoading: boolean;
  isError: boolean;
} = { data: undefined, isLoading: true, isError: false };

vi.mock("../hooks", () => ({
  useExchangeAccounts: () => ({
    data: mockState.data,
    isLoading: mockState.isLoading,
    isError: mockState.isError,
    refetch: refetchMock,
  }),
  useDeleteExchangeAccount: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

vi.mock("../components/register-exchange-account-dialog", () => ({
  RegisterExchangeAccountDialog: () => null,
}));

vi.mock("../components/trading-empty-state", () => ({
  TradingEmptyState: () => null,
}));

import { ExchangeAccountsPanel } from "../components/exchange-accounts-panel";

function renderPanel() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <ExchangeAccountsPanel />
    </QueryClientProvider>,
  );
}

describe("ExchangeAccountsPanel loading/error UX (Phase B-2)", () => {
  it("isLoading=true → skeleton placeholder 렌더 + 표/이모티 부재", () => {
    mockState = { data: undefined, isLoading: true, isError: false };
    renderPanel();
    expect(
      screen.getByLabelText("거래소 계정 불러오는 중"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Exchange Accounts")).toBeNull();
  });

  it("isError=true → 안내 메시지 + 다시 시도 버튼 → refetch 호출", () => {
    mockState = { data: undefined, isLoading: false, isError: true };
    renderPanel();
    expect(
      screen.getByText("거래소 계정 목록을 불러오지 못했습니다."),
    ).toBeInTheDocument();
    const retryBtn = screen.getByRole("button", { name: "다시 시도" });
    expect(retryBtn).toBeInTheDocument();
    fireEvent.click(retryBtn);
    expect(refetchMock).toHaveBeenCalledTimes(1);
  });
});
