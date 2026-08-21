// 라이브 세션 훅의 미커버 React Query 경계를 고정한다.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type * as ApiModule from "../api";
import { liveSessionKeys } from "../query-keys";
import type {
  AccountPositions,
  LiveSession,
  LiveSessionPositions,
  RegisterLiveSessionRequest,
} from "../schemas";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof ApiModule>();
  return {
    ...actual,
    getAccountPositions: vi.fn(),
    getLiveSessionPositions: vi.fn(),
    registerLiveSession: vi.fn(),
  };
});

import { getAccountPositions, getLiveSessionPositions, registerLiveSession } from "../api";
import { useAccountPositions, useLiveSessionPositions, useRegisterLiveSession } from "../hooks";

const getAccountPositionsMock = vi.mocked(getAccountPositions);
const getLiveSessionPositionsMock = vi.mocked(getLiveSessionPositions);
const registerLiveSessionMock = vi.mocked(registerLiveSession);

const USER_ID = "10000000-0000-4000-8000-000000000001";
const SESSION_ID = "20000000-0000-4000-8000-000000000001";
const ACCOUNT_ID = "30000000-0000-4000-8000-000000000001";
const STRATEGY_ID = "40000000-0000-4000-8000-000000000001";

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

function makeAccountPositions(accountId: string): AccountPositions {
  return {
    account_id: accountId,
    supported: true,
    reason: null,
    fetched_at: "2026-08-22T00:00:00Z",
    rows: [],
    settle_coin: "USDT",
    truncated: false,
  };
}

function makeSession(): LiveSession {
  return {
    id: SESSION_ID,
    user_id: USER_ID,
    strategy_id: STRATEGY_ID,
    exchange_account_id: ACCOUNT_ID,
    symbol: "BTCUSDT",
    interval: "1h",
    is_active: true,
    last_evaluated_bar_time: null,
    created_at: "2026-08-22T00:00:00Z",
    deactivated_at: null,
  };
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("live session core hooks", () => {
  it("세션 포지션 조회에 세션 ID와 인증 토큰을 전달한다", async () => {
    const response: LiveSessionPositions = {
      session_id: SESSION_ID,
      symbol: "BTCUSDT",
      market_type: "futures",
      supported: true,
      reason: null,
      fetched_at: "2026-08-22T00:00:00Z",
      positions: [],
      local_open_trades_snapshot: [],
      diff: { verdict: "match", local_source: "none" },
    };
    getLiveSessionPositionsMock.mockResolvedValue(response);
    const queryClient = makeClient();

    const { result } = renderHook(() => useLiveSessionPositions(SESSION_ID), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(response));
    expect(getLiveSessionPositionsMock).toHaveBeenCalledWith(SESSION_ID, "test-token");
    expect(queryClient.getQueryData(liveSessionKeys.positions("user-1", SESSION_ID))).toEqual(
      response,
    );
  });

  it("계정별 포지션 팬아웃이 각 계정과 같은 인증 토큰을 사용한다", async () => {
    const secondAccountId = "30000000-0000-4000-8000-000000000002";
    getAccountPositionsMock.mockImplementation(async (accountId) =>
      makeAccountPositions(accountId),
    );

    const { result } = renderHook(
      () => useAccountPositions([{ id: ACCOUNT_ID }, { id: secondAccountId }]),
      { wrapper: makeWrapper(makeClient()) },
    );

    await waitFor(() => expect(result.current.every((query) => query.isSuccess)).toBe(true));
    expect(getAccountPositionsMock).toHaveBeenCalledWith(ACCOUNT_ID, "test-token");
    expect(getAccountPositionsMock).toHaveBeenCalledWith(secondAccountId, "test-token");
  });

  it("세션 등록 뒤 사용자별 목록 캐시를 무효화한다", async () => {
    const request: RegisterLiveSessionRequest = {
      strategy_id: STRATEGY_ID,
      exchange_account_id: ACCOUNT_ID,
      symbol: "BTCUSDT",
      interval: "1h",
    };
    registerLiveSessionMock.mockResolvedValue(makeSession());
    const queryClient = makeClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useRegisterLiveSession(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(request)).resolves.toEqual(makeSession());
    expect(registerLiveSessionMock).toHaveBeenCalledWith(request, "test-token");
    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: liveSessionKeys.list("user-1") }),
    );
  });
});
