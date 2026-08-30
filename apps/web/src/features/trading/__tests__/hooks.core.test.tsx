// 트레이딩 훅의 정상 React Query 경계와 API 요청 계약을 고정한다.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ZodError } from "zod/v4";

import { ApiError } from "@/lib/api-client";
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
  ACTIVE_ORDER_STATES,
  computeOrdersRefetchInterval,
  ORDERS_REFETCH_INTERVAL_ACTIVE_MS,
  ORDERS_REFETCH_INTERVAL_IDLE_MS,
  useAccountBalances,
  useDeleteExchangeAccount,
  useExchangeAccounts,
  useIsOrderDisabledByKs,
  useLiquidationInfo,
  useOrders,
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

afterEach(() => {
  apiFetchMock.mockReset();
  vi.unstubAllGlobals();
});

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
      label: "Demo account",
      api_key: "api-key",
      api_secret: "api-secret",
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

  it("활성 주문이 하나라도 있으면 빠른 폴링을, 없으면 느린 폴링을 선택한다", () => {
    expect(ACTIVE_ORDER_STATES.has("pending")).toBe(true);
    expect(computeOrdersRefetchInterval([{ state: "submitted" }])).toBe(
      ORDERS_REFETCH_INTERVAL_ACTIVE_MS,
    );
    expect(computeOrdersRefetchInterval([{ state: "filled" }])).toBe(
      ORDERS_REFETCH_INTERVAL_IDLE_MS,
    );
    expect(computeOrdersRefetchInterval([])).toBe(ORDERS_REFETCH_INTERVAL_IDLE_MS);
  });

  it("주문 목록은 states가 없을 때 undefined 쿼리를 붙이지 않고 limit=0을 보존한다", async () => {
    const { apiFetch: actualApiFetch } =
      await vi.importActual<typeof import("@/lib/api-client")>("@/lib/api-client");
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [], total: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    apiFetchMock.mockImplementation(actualApiFetch);
    const { result } = renderHook(() => useOrders(0, { notifyTransitions: false }), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.data).toEqual({ items: [], total: 0 }));
    const call = fetchMock.mock.calls[0];
    expect(call).toBeDefined();
    if (!call) throw new Error("fetch must be called");
    const [url] = call;
    expect(String(url)).toContain("limit=0");
    expect(String(url)).toContain("offset=0");
    expect(String(url)).not.toContain("state=undefined");
    expect(String(url)).not.toContain("undefined");
  });

  it("음수 limit도 주문 목록 요청의 경계값으로 보존한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 0 });
    const { result } = renderHook(() => useOrders(-1, { notifyTransitions: false }), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.data).toEqual({ items: [], total: 0 }));
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/orders", {
      method: "GET",
      token: "test-token",
      params: { limit: -1, offset: 0 },
    });
  });

  it("주문 목록은 ApiError의 status와 code를 같은 객체로 전파한다", async () => {
    const error = new ApiError(429, "rate_limited", "orders temporarily limited");
    apiFetchMock.mockRejectedValueOnce(error);
    const { result } = renderHook(() => useOrders(50, { notifyTransitions: false }), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(error);
    expect(error).toMatchObject({ status: 429, code: "rate_limited" });
  });

  it("주문 목록은 계약을 어긴 item을 조용히 통과시키지 않는다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [{ id: "not-a-complete-order" }], total: 1 });
    const { result } = renderHook(() => useOrders(50, { notifyTransitions: false }), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(ZodError);
  });

  it("거래소 계정 목록은 빈 배열을 성공 응답으로 보존한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [] });
    const { result } = renderHook(() => useExchangeAccounts(), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.data).toEqual([]));
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/exchange-accounts", {
      method: "GET",
      token: "test-token",
    });
  });

  it("leverage=0인 청산가 입력은 조회를 발사하지 않는다", () => {
    const { result } = renderHook(
      () =>
        useLiquidationInfo({
          symbol: "BTCUSDT",
          side: "buy",
          entry_price: "100",
          leverage: 0,
        }),
      { wrapper: makeWrapper(makeClient()) },
    );

    expect(result.current.fetchStatus).toBe("idle");
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("음수 leverage 청산가 입력은 조회를 발사하지 않는다", () => {
    const { result } = renderHook(
      () =>
        useLiquidationInfo({
          symbol: "BTCUSDT",
          side: "sell",
          entry_price: "100",
          leverage: -1,
        }),
      { wrapper: makeWrapper(makeClient()) },
    );

    expect(result.current.fetchStatus).toBe("idle");
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("해결된 킬 스위치 이벤트만 있으면 주문을 비활성화하지 않는다", async () => {
    const resolvedEvent: KillSwitchEvent = {
      id: "70000000-0000-4000-8000-000000000002",
      trigger_type: "daily_loss",
      trigger_value: "101",
      threshold: "100",
      triggered_at: "2026-08-22T00:00:00Z",
      resolved_at: "2026-08-22T00:01:00Z",
    };
    apiFetchMock.mockResolvedValueOnce({ items: [resolvedEvent] });
    const { result } = renderHook(() => useIsOrderDisabledByKs(), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current).toBe(false));
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("apiFetch는 undefined 쿼리를 생략하고 204 빈 응답을 void로 반환한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    const { apiFetch: actualApiFetch } =
      await vi.importActual<typeof import("@/lib/api-client")>("@/lib/api-client");

    await expect(
      actualApiFetch<void>(`/api/v1/exchange-accounts/${ACCOUNT_ID}`, {
        method: "DELETE",
        params: { limit: 0, offset: -1, cursor: undefined },
      }),
    ).resolves.toBeUndefined();

    const call = fetchMock.mock.calls[0];
    expect(call).toBeDefined();
    if (!call) throw new Error("fetch must be called");
    const [url] = call;
    expect(String(url)).toContain("limit=0");
    expect(String(url)).toContain("offset=-1");
    expect(String(url)).not.toContain("cursor=undefined");
  });
});
