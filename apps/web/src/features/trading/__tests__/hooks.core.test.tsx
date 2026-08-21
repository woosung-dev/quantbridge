// 트레이딩 훅의 정상 React Query 경계와 API 요청 계약을 고정한다.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  AccountBalance,
  ExchangeAccount,
  KillSwitchEvent,
  LiquidationInfoResponse,
  RegisterAccountRequest,
} from "../schemas";
import { tradingKeys } from "../query-keys";

const apiFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiFetchMock };
});

import {
  useAccountBalances,
  useDeleteExchangeAccount,
  useIsOrderDisabledByKs,
  useLiquidationInfo,
  useRegisterExchangeAccount,
  useResolveKillSwitchEvent,
} from "../hooks";

const ACCOUNT_ID = "50000000-0000-4000-8000-000000000001";

function makeClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function makeWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function makeBalance(accountId: string): AccountBalance {
  return {
    account_id: accountId,
    asset: "USDT",
    supported: true,
    reason: null,
    total: "100.00",
    free: "80.00",
    fetched_at: "2026-08-22T00:00:00Z",
  };
}

function makeAccount(overrides: Partial<ExchangeAccount> = {}): ExchangeAccount {
  return {
    id: ACCOUNT_ID,
    exchange: "bybit",
    mode: "demo",
    label: "Demo account",
    api_key_masked: "abcd••••wxyz",
    exchange_uid: null,
    read_only: false,
    created_at: "2026-08-22T00:00:00Z",
    ...overrides,
  };
}

afterEach(() => apiFetchMock.mockReset());

describe("trading core hooks", () => {
  it("계정 잔고 팬아웃이 계정별 경로와 인증 토큰을 사용한다", async () => {
    const secondAccountId = "50000000-0000-4000-8000-000000000002";
    apiFetchMock.mockImplementation(async (path: string) =>
      makeBalance(path.includes(secondAccountId) ? secondAccountId : ACCOUNT_ID),
    );
    const { result } = renderHook(
      () => useAccountBalances([{ id: ACCOUNT_ID }, { id: secondAccountId }]),
      { wrapper: makeWrapper(makeClient()) },
    );

    await waitFor(() => expect(result.current.every((query) => query.isSuccess)).toBe(true));
    expect(result.current.map((query) => query.data?.account_id)).toEqual([
      ACCOUNT_ID,
      secondAccountId,
    ]);
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/exchange-accounts/${ACCOUNT_ID}/balance`, {
      method: "GET",
      token: "test-token",
    });
    expect(apiFetchMock).toHaveBeenCalledWith(
      `/api/v1/exchange-accounts/${secondAccountId}/balance`,
      {
        method: "GET",
        token: "test-token",
      },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(2);
  });

  it("완비된 청산가 입력이 POST body와 사용자별 조회 키로 흐른다", async () => {
    const params = { symbol: "BTCUSDT", side: "buy" as const, entry_price: "100", leverage: 10 };
    const response: LiquidationInfoResponse = {
      ...params,
      liquidation_price: "90",
      maintenance_margin_rate: "0.005",
      distance_pct: "10",
    };
    apiFetchMock.mockResolvedValueOnce(response);
    const queryClient = makeClient();
    const { result } = renderHook(() => useLiquidationInfo(params), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(response));
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/liquidation/preview", {
      method: "POST",
      token: "test-token",
      body: params,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
    expect(queryClient.getQueryData(tradingKeys.liquidation("user-1", params))).toEqual(response);
  });

  it("킬 스위치 해제가 기본 note를 POST하고 사용자별 이벤트 캐시를 무효화한다", async () => {
    const eventId = "60000000-0000-4000-8000-000000000001";
    apiFetchMock.mockResolvedValueOnce(undefined);
    const queryClient = makeClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useResolveKillSwitchEvent(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(eventId)).resolves.toBeUndefined();
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/kill-switch/events/${eventId}/resolve`, {
      method: "POST",
      token: "test-token",
      body: { note: "manual unlock from dashboard" },
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: tradingKeys.killSwitch("user-1") }),
    );
  });

  it("미해결 킬 스위치 이벤트가 있으면 주문을 비활성화한다", async () => {
    const activeEvent: KillSwitchEvent = {
      id: "70000000-0000-4000-8000-000000000001",
      trigger_type: "daily_loss",
      trigger_value: "101",
      threshold: "100",
      triggered_at: "2026-08-22T00:00:00Z",
      resolved_at: null,
    };
    apiFetchMock.mockResolvedValueOnce({ items: [activeEvent] });
    const { result } = renderHook(() => useIsOrderDisabledByKs(), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current).toBe(true));
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/kill-switch/events", {
      method: "GET",
      token: "test-token",
      params: { limit: 20 },
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("거래소 계정 등록이 요청 body를 POST하고 계정 목록 캐시를 무효화한다", async () => {
    const request: RegisterAccountRequest = {
      exchange: "bybit",
      mode: "demo",
      label: "Demo account",
      api_key: "api-key",
      api_secret: "api-secret",
      passphrase: null,
    };
    const response = makeAccount();
    apiFetchMock.mockResolvedValueOnce(response);
    const queryClient = makeClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useRegisterExchangeAccount(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(request)).resolves.toEqual(response);
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/exchange-accounts", {
      method: "POST",
      token: "test-token",
      body: request,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: tradingKeys.exchangeAccounts("user-1"),
      }),
    );
  });

  it("거래소 계정 삭제가 DELETE 요청 뒤 계정 목록 캐시를 무효화한다", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);
    const queryClient = makeClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useDeleteExchangeAccount(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(ACCOUNT_ID)).resolves.toBeUndefined();
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/exchange-accounts/${ACCOUNT_ID}`, {
      method: "DELETE",
      token: "test-token",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: tradingKeys.exchangeAccounts("user-1"),
      }),
    );
  });
});
