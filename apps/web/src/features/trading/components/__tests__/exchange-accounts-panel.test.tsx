import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const useExchangeAccountsMock = vi.fn();

vi.mock("../../hooks", () => ({
  useDeleteExchangeAccount: () => ({ mutate: vi.fn(), isPending: false }),
  useExchangeAccounts: () => useExchangeAccountsMock(),
}));
vi.mock("../register-exchange-account-dialog", () => ({
  RegisterExchangeAccountDialog: () => <button type="button">계정 추가</button>,
}));
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

import { ExchangeAccountsPanel } from "../exchange-accounts-panel";

describe("ExchangeAccountsPanel", () => {
  it("legacy 계정은 보존해 표시하되 운영 차단과 삭제 전용 상태를 알린다", () => {
    useExchangeAccountsMock.mockReturnValue({
      data: [
        {
          id: "bybit-demo",
          exchange: "bybit",
          mode: "demo",
          label: "운영 계정",
          api_key_masked: "****",
          exchange_uid: null,
          read_only: null,
          created_at: "2026-08-30T00:00:00Z",
        },
        {
          id: "legacy-live",
          exchange: "bybit",
          mode: "live",
          label: "기존 라이브",
          api_key_masked: "****",
          exchange_uid: null,
          read_only: null,
          created_at: "2026-08-30T00:00:00Z",
        },
      ],
      isError: false,
      isLoading: false,
      refetch: vi.fn(),
    });

    render(<ExchangeAccountsPanel />);

    expect(screen.getByText("운영 차단")).toBeInTheDocument();
    expect(screen.getByText("기존 계정은 보존되며 삭제만 할 수 있습니다.")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "계정 삭제" })).toHaveLength(2);
  });
});
