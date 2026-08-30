import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RegisterExchangeAccountDialog } from "../components/register-exchange-account-dialog";

vi.mock("../hooks", () => ({
  useRegisterExchangeAccount: () => ({
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  }),
}));

describe("RegisterExchangeAccountDialog", () => {
  it("renders trigger button", () => {
    render(<RegisterExchangeAccountDialog />);
    expect(screen.getByRole("button", { name: /계정 추가/i })).toBeInTheDocument();
  });

  it("opens dialog on trigger click", async () => {
    render(<RegisterExchangeAccountDialog />);
    fireEvent.click(screen.getByRole("button", { name: /계정 추가/i }));
    await waitFor(() => {
      expect(screen.getByText("거래소 계정 등록")).toBeInTheDocument();
    });
  });

  it("passphrase 필드가 없다 (C 이식 W3-F — Bybit 단일, OKX 제거)", async () => {
    render(<RegisterExchangeAccountDialog />);
    fireEvent.click(screen.getByRole("button", { name: /계정 추가/i }));
    await waitFor(() => screen.getByText("거래소 계정 등록"));
    // 연결 거래소는 Bybit 하나뿐 — passphrase 입력이 어느 상태에서도 없다.
    expect(screen.queryByText(/Passphrase/i)).not.toBeInTheDocument();
    expect(screen.getByText(/새 계정은 Bybit Demo 환경으로만 등록됩니다/)).toBeInTheDocument();
  });

  it("renders cancel and submit buttons after opening", async () => {
    render(<RegisterExchangeAccountDialog />);
    fireEvent.click(screen.getByRole("button", { name: /계정 추가/i }));
    await waitFor(() => screen.getByText("거래소 계정 등록"));
    expect(screen.getByRole("button", { name: /취소/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^등록$/i })).toBeInTheDocument();
  });
});
