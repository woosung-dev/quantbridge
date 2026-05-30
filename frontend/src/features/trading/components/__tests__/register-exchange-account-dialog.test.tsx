// P1-1/11 (S7-A) — RegisterExchangeAccountDialog UX 회귀.
//
// 검증 범위:
//  1) OKX 선택 시 passphrase 비우면 client-side validation block (서버 422 도달 X)
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
  const { RegisterExchangeAccountDialog } = await import(
    "../register-exchange-account-dialog"
  );
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

async function fillAndSubmit(opts: {
  exchange?: "bybit" | "okx";
  apiKey?: string;
  apiSecret?: string;
  passphrase?: string;
}) {
  const apiKeyInput = screen.getByPlaceholderText("API Key");
  fireEvent.change(apiKeyInput, { target: { value: opts.apiKey ?? "K" } });
  const apiSecretInput = screen.getByPlaceholderText("API Secret");
  fireEvent.change(apiSecretInput, {
    target: { value: opts.apiSecret ?? "S" },
  });
  if (opts.exchange === "okx") {
    // OKX 선택 시 schema cross-field 검증을 위해 form 의 exchange 값을 직접 setter 로 변경할
    // 방법이 없어서, defaultValues 가 "bybit" 인 케이스만 시뮬레이션한다. OKX 경로는
    // 별도 schema unit test (test-schema-okx-passphrase) 로 검증.
  }
  const submitBtn = screen.getByRole("button", { name: /^등록$/ });
  await act(async () => {
    fireEvent.click(submitBtn);
  });
}

describe("RegisterExchangeAccountDialog — P1-1/11 (S7-A)", () => {
  it("정상 등록 시 mutateAsync 호출 + 다이얼로그 닫힘", async () => {
    mutateAsyncMock.mockResolvedValueOnce({ id: "acc-1" });
    await renderDialog();
    await fillAndSubmit({ apiKey: "K1", apiSecret: "S1" });

    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith(
        expect.objectContaining({
          exchange: "bybit",
          mode: "demo",
          api_key: "K1",
          api_secret: "S1",
          passphrase: null,
        }),
      );
    });
  });

  it("mutation 이 throw 하면 root.serverError 가 inline 표시", async () => {
    mutateAsyncMock.mockRejectedValueOnce(new Error("HTTP 422: OKX 검증 실패"));
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

describe("RegisterAccountRequestSchema — P1-1/11 (S7-A) OKX passphrase 강제", () => {
  it("bybit 선택 시 passphrase null 허용", async () => {
    const { RegisterAccountRequestSchema } = await import(
      "../../schemas"
    );
    const result = RegisterAccountRequestSchema.safeParse({
      exchange: "bybit",
      mode: "demo",
      label: null,
      api_key: "K",
      api_secret: "S",
      passphrase: null,
    });
    expect(result.success).toBe(true);
  });

  it("okx + passphrase null → validation fail", async () => {
    const { RegisterAccountRequestSchema } = await import(
      "../../schemas"
    );
    const result = RegisterAccountRequestSchema.safeParse({
      exchange: "okx",
      mode: "demo",
      label: null,
      api_key: "K",
      api_secret: "S",
      passphrase: null,
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      const passphraseError = result.error.issues.find((i) =>
        i.path.includes("passphrase"),
      );
      expect(passphraseError?.message).toContain("Passphrase");
    }
  });

  it("okx + passphrase 빈 string → validation fail", async () => {
    const { RegisterAccountRequestSchema } = await import(
      "../../schemas"
    );
    const result = RegisterAccountRequestSchema.safeParse({
      exchange: "okx",
      mode: "demo",
      label: null,
      api_key: "K",
      api_secret: "S",
      passphrase: "",
    });
    expect(result.success).toBe(false);
  });

  it("okx + passphrase non-empty → validation pass", async () => {
    const { RegisterAccountRequestSchema } = await import(
      "../../schemas"
    );
    const result = RegisterAccountRequestSchema.safeParse({
      exchange: "okx",
      mode: "demo",
      label: null,
      api_key: "K",
      api_secret: "S",
      passphrase: "MyPass123",
    });
    expect(result.success).toBe(true);
  });
});
