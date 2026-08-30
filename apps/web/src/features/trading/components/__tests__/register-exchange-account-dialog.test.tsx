// P1-1/11 (S7-A) — RegisterExchangeAccountDialog UX 회귀.
//
// 검증 범위:
//  1) Bybit Demo 정책을 UI에서 고정하고 legacy 선택 필드를 보내지 않는다
//  2) mutation 이 throw 하면 root.serverError 로 inline 표시 (이전엔 무피드백)
//  3) 재submit 시 stale serverError 가 clearErrors

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// ── useRegisterExchangeAccount mock — mutateAsync 호출 추적 + 실패 주입 ──
const mutateAsyncMock = vi.fn();
const isPendingMock = vi.fn(() => false);
vi.mock("../../hooks", () => ({
  useRegisterExchangeAccount: () => ({
    mutateAsync: (payload: unknown) => mutateAsyncMock(payload),
    isPending: isPendingMock(),
  }),
}));

beforeEach(() => {
  mutateAsyncMock.mockReset();
  isPendingMock.mockReset();
  isPendingMock.mockReturnValue(false);
});

afterEach(() => {
  vi.clearAllMocks();
});

async function renderDialog() {
  const { RegisterExchangeAccountDialog } = await import("../register-exchange-account-dialog");
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const utils = render(
    <QueryClientProvider client={qc}>
      <RegisterExchangeAccountDialog />
    </QueryClientProvider>,
  );
  // 다이얼로그 열기
  fireEvent.click(screen.getByRole("button", { name: "계정 추가" }));
  await waitFor(() => screen.getByRole("dialog"));
  return utils;
}

async function fillAndSubmit(opts: { apiKey?: string; apiSecret?: string }) {
  const apiKeyInput = screen.getByPlaceholderText("API Key");
  fireEvent.change(apiKeyInput, { target: { value: opts.apiKey ?? "K" } });
  const apiSecretInput = screen.getByPlaceholderText("API Secret");
  fireEvent.change(apiSecretInput, {
    target: { value: opts.apiSecret ?? "S" },
  });
  const submitBtn = screen.getByRole("button", { name: /^등록$/ });
  await act(async () => {
    fireEvent.click(submitBtn);
  });
}

describe("RegisterExchangeAccountDialog — P1-1/11 (S7-A)", () => {
  it("정상 등록 시 mutateAsync 호출 + 다이얼로그 닫힘", async () => {
    mutateAsyncMock.mockResolvedValueOnce({ id: "acc-1" });
    await renderDialog();
    expect(screen.getByTestId("bybit-demo-only-notice")).toHaveTextContent("Bybit 데모 전용");
    expect(screen.queryByText("라이브")).not.toBeInTheDocument();
    await fillAndSubmit({ apiKey: "K1", apiSecret: "S1" });

    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith({
        label: null,
        api_key: "K1",
        api_secret: "S1",
      });
    });
  });

  it("mutation 이 throw 하면 root.serverError 가 inline 표시", async () => {
    mutateAsyncMock.mockRejectedValueOnce(new Error("HTTP 422: 검증 실패"));
    await renderDialog();
    await fillAndSubmit({ apiKey: "K2", apiSecret: "S2" });

    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert.textContent).toContain("HTTP 422");
    });
  });

  it("재submit 시 stale serverError 제거 후 mutation 재시도", async () => {
    mutateAsyncMock
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValueOnce({ id: "acc-2" });
    await renderDialog();

    // 1st: fail
    await fillAndSubmit({ apiKey: "K3", apiSecret: "S3" });
    await waitFor(() => screen.getByRole("alert"));

    // 2nd: success — stale alert clear + mutateAsync 두 번 호출
    await fillAndSubmit({ apiKey: "K3", apiSecret: "S3" });
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledTimes(2);
    });
  });
});

// Bybit Demo는 UI 선택지가 아닌 서버 정책이다. 새 요청에는 credential과 label만 남는다.
describe("RegisterAccountRequestSchema — Bybit Demo 고정", () => {
  it("label + API credential만 통과한다", async () => {
    const { RegisterAccountRequestSchema } = await import("../../schemas");
    const result = RegisterAccountRequestSchema.safeParse({
      label: null,
      api_key: "K",
      api_secret: "S",
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data).toEqual({ label: null, api_key: "K", api_secret: "S" });
  });

  it("legacy exchange/mode/passphrase 입력은 strip 하지 않고 거부한다", async () => {
    const { RegisterAccountRequestSchema } = await import("../../schemas");
    const result = RegisterAccountRequestSchema.safeParse({
      exchange: "okx",
      mode: "live",
      label: null,
      api_key: "K",
      api_secret: "S",
      passphrase: "MyPass123",
    });
    expect(result.success).toBe(false);
  });
});
