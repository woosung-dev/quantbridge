// 트레이딩 훅의 미커버 React Query 경계를 고정한다.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type * as ApiModule from "../api";
import { tradingKeys } from "../query-keys";
import type { AccountBalance, KillSwitchEvent, LiquidationInfoResponse } from "../schemas";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof ApiModule>();
  return {
    ...actual,
    getAccountBalance: vi.fn(),
    getLiquidationInfo: vi.fn(),
    listKillSwitchEvents: vi.fn(),
    resolveKillSwitchEvent: vi.fn(),
  };
});

import {
  getAccountBalance,
  getLiquidationInfo,
  listKillSwitchEvents,
  resolveKillSwitchEvent,
} from "../api";
import {
  useAccountBalances,
  useIsOrderDisabledByKs,
  useLiquidationInfo,
  useResolveKillSwitchEvent,
} from "../hooks";

const getAccountBalanceMock = vi.mocked(getAccountBalance);
const getLiquidationInfoMock = vi.mocked(getLiquidationInfo);
const listKillSwitchEventsMock = vi.mocked(listKillSwitchEvents);
const resolveKillSwitchEventMock = vi.mocked(resolveKillSwitchEvent);

const ACCOUNT_ID = "50000000-0000-4000-8000-000000000001";

function makeClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
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

afterEach(() => {
  vi.clearAllMocks();
});

describe("trading core hooks", () => {
  it("계정 잔고 팬아웃이 계정별 API와 인증 토큰을 사용한다", async () => {
    const secondAccountId = "50000000-0000-4000-8000-000000000002";
    getAccountBalanceMock.mockImplementation(async (accountId) => makeBalance(accountId));

    const { result } = renderHook(
      () => useAccountBalances([{ id: ACCOUNT_ID }, { id: secondAccountId }]),
      { wrapper: makeWrapper(makeClient()) },
    );

    await waitFor(() => expect(result.current.every((query) => query.isSuccess)).toBe(true));
    expect(getAccountBalanceMock).toHaveBeenCalledWith(ACCOUNT_ID, "test-token");
    expect(getAccountBalanceMock).toHaveBeenCalledWith(secondAccountId, "test-token");
  });

  it("완비된 청산가 입력만 조회 키와 API 호출에 전달한다", async () => {
    const params = { symbol: "BTCUSDT", side: "buy" as const, entry_price: "100", leverage: 10 };
    const response: LiquidationInfoResponse = {
      ...params,
      liquidation_price: "90",
      maintenance_margin_rate: "0.005",
      distance_pct: "10",
    };
    getLiquidationInfoMock.mockResolvedValue(response);
    const queryClient = makeClient();

    const { result } = renderHook(() => useLiquidationInfo(params), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(response));
    expect(getLiquidationInfoMock).toHaveBeenCalledWith(params, "test-token");
    expect(queryClient.getQueryData(tradingKeys.liquidation("user-1", params))).toEqual(response);
  });

  it("킬 스위치 해제 뒤 사용자별 이벤트 캐시를 무효화한다", async () => {
    const eventId = "60000000-0000-4000-8000-000000000001";
    resolveKillSwitchEventMock.mockResolvedValue(undefined);
    const queryClient = makeClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useResolveKillSwitchEvent(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(eventId)).resolves.toBeUndefined();
    expect(resolveKillSwitchEventMock).toHaveBeenCalledWith(eventId, "test-token");
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
    listKillSwitchEventsMock.mockResolvedValue({ items: [activeEvent] });

    const { result } = renderHook(() => useIsOrderDisabledByKs(), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current).toBe(true));
    expect(listKillSwitchEventsMock).toHaveBeenCalledWith("test-token");
  });
});
