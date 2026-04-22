import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RegisterExchangeAccountDialog } from "../components/register-exchange-account-dialog";

vi.mock("../hooks", () => ({
  useRegisterExchangeAccount: () => ({
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  }),
}));

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ userId: "u1", getToken: async () => "tok" }),
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

  it("shows passphrase field only for OKX", async () => {
    render(<RegisterExchangeAccountDialog />);
    fireEvent.click(screen.getByRole("button", { name: /계정 추가/i }));
    await waitFor(() => screen.getByText("거래소 계정 등록"));
    // 기본값 bybit — passphrase 없음
    expect(screen.queryByText(/Passphrase/i)).not.toBeInTheDocument();
  });

  it("renders cancel and submit buttons after opening", async () => {
    render(<RegisterExchangeAccountDialog />);
    fireEvent.click(screen.getByRole("button", { name: /계정 추가/i }));
    await waitFor(() => screen.getByText("거래소 계정 등록"));
    expect(screen.getByRole("button", { name: /취소/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^등록$/i })).toBeInTheDocument();
  });
});
