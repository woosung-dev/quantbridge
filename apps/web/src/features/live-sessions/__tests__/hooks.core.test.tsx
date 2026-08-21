// 라이브 세션 훅의 정상 React Query 경계와 API 요청 계약을 고정한다.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ZodError } from "zod/v4";

import { ApiError } from "@/lib/api-client";
import type {
  ExchangePosition,
  LiveSession,
  LiveSessionPositions,
  LiveSignalState,
  RegisterLiveSessionRequest,
} from "../schemas";
import { liveSessionKeys } from "../query-keys";

const apiFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiFetchMock };
});

import {
  closePositionMutationKey,
  combineLiveSessionPositions,
  useAccountPositions,
  useClosePosition,
  useDeactivateLiveSession,
  useLiveSessionEvents,
  useLiveSessionOutcomeParity,
  useLiveSessionPositions,
  useLiveSessions,
  useLiveSessionsAggregate,
  useLiveSessionsPositions,
  useLiveSessionState,
  useRegisterLiveSession,
} from "../hooks";

const USER_ID = "10000000-0000-4000-8000-000000000001";
const SESSION_ID = "20000000-0000-4000-8000-000000000001";
const ACCOUNT_ID = "30000000-0000-4000-8000-000000000001";
const STRATEGY_ID = "40000000-0000-4000-8000-000000000001";

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

function makeSession(overrides: Partial<LiveSession> = {}): LiveSession {
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
    ...overrides,
  };
}

function makeState(sessionId: string, overrides: Partial<LiveSignalState> = {}): LiveSignalState {
  return {
    session_id: sessionId,
    evaluated: true,
    schema_version: 1,
    last_strategy_state_report: {},
    total_closed_trades: 2,
    total_realized_pnl: "1.50",
    confirmed_realized_pnl: "1.00",
    estimated_realized_pnl: "0.50",
    equity_curve: [],
    updated_at: "2026-08-22T00:00:00Z",
    ...overrides,
  };
}

function makeExchangePosition(overrides: Partial<ExchangePosition> = {}): ExchangePosition {
  return {
    side: "Buy",
    size: "0.1",
    entry_price: "100",
    mark_price: "110",
    unrealized_pnl: "1",
    take_profit_prices: [],
    stop_loss_prices: [],
    has_trailing_stop: false,
    liquidation_price: null,
    leverage: "2",
    ...overrides,
  };
}

function makeSessionPositions(
  sessionId: string,
  overrides: Partial<LiveSessionPositions> = {},
): LiveSessionPositions {
  return {
    session_id: sessionId,
    symbol: "BTCUSDT",
    market_type: "futures",
    supported: true,
    reason: null,
    fetched_at: "2026-08-22T00:00:00Z",
    positions: [makeExchangePosition()],
    local_open_trades_snapshot: [],
    diff: { verdict: "match", local_source: "none" },
    ...overrides,
  };
}

afterEach(() => {
  apiFetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("live session core hooks", () => {
  it("세션 포지션 조회가 경로·토큰을 한 번 전달하고 파싱된 응답을 캐시한다", async () => {
    const response = makeSessionPositions(SESSION_ID);
    apiFetchMock.mockResolvedValueOnce(response);
    const queryClient = makeClient();
    const { result } = renderHook(() => useLiveSessionPositions(SESSION_ID), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(response));
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION_ID}/positions`, {
      method: "GET",
      token: "test-token",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
    expect(queryClient.getQueryData(liveSessionKeys.positions("user-1", SESSION_ID))).toEqual(
      response,
    );
  });

  it("계정별 포지션 팬아웃이 각 계정 경로를 한 번씩 호출한다", async () => {
    const secondAccountId = "30000000-0000-4000-8000-000000000002";
    apiFetchMock.mockImplementation(async (path: string) => ({
      account_id: path.includes(secondAccountId) ? secondAccountId : ACCOUNT_ID,
      supported: true,
      reason: null,
      fetched_at: "2026-08-22T00:00:00Z",
      rows: [],
      settle_coin: "USDT",
      truncated: false,
    }));
    const { result } = renderHook(
      () => useAccountPositions([{ id: ACCOUNT_ID }, { id: secondAccountId }]),
      { wrapper: makeWrapper(makeClient()) },
    );

    await waitFor(() => expect(result.current.every((query) => query.isSuccess)).toBe(true));
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/exchange-accounts/${ACCOUNT_ID}/positions`, {
      method: "GET",
      token: "test-token",
    });
    expect(apiFetchMock).toHaveBeenCalledWith(
      `/api/v1/exchange-accounts/${secondAccountId}/positions`,
      {
        method: "GET",
        token: "test-token",
      },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(2);
  });

  it("세션 등록이 POST body를 그대로 보내고 목록 캐시를 무효화한다", async () => {
    const request: RegisterLiveSessionRequest = {
      strategy_id: STRATEGY_ID,
      exchange_account_id: ACCOUNT_ID,
      symbol: "BTCUSDT",
      interval: "1h",
    };
    const response = makeSession();
    apiFetchMock.mockResolvedValueOnce(response);
    const queryClient = makeClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useRegisterLiveSession(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(request)).resolves.toEqual(response);
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/live-sessions", {
      method: "POST",
      token: "test-token",
      body: request,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: liveSessionKeys.list("user-1") }),
    );
  });

  it("세션 state 팬아웃이 각 state 경로의 손익을 합산한다", async () => {
    const secondSessionId = "20000000-0000-4000-8000-000000000002";
    const sessions = [makeSession(), makeSession({ id: secondSessionId, strategy_id: USER_ID })];
    apiFetchMock.mockImplementation(async (path: string) =>
      path.includes(secondSessionId)
        ? makeState(secondSessionId, {
            total_realized_pnl: "2.50",
            total_closed_trades: 3,
            confirmed_realized_pnl: "2.00",
            estimated_realized_pnl: "0.50",
          })
        : makeState(SESSION_ID),
    );
    const { result } = renderHook(() => useLiveSessionsAggregate(sessions), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.populatedSessions).toBe(2));
    expect(result.current).toMatchObject({
      totalRealizedPnl: 4,
      totalClosedTrades: 5,
      confirmedRealizedPnl: 3,
      estimatedRealizedPnl: 1,
    });
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION_ID}/state`, {
      method: "GET",
      token: "test-token",
    });
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${secondSessionId}/state`, {
      method: "GET",
      token: "test-token",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(2);
  });

  it("단일 세션 state의 누적 곡선을 epoch seconds로 반환한다", async () => {
    apiFetchMock.mockResolvedValueOnce(
      makeState(SESSION_ID, {
        equity_curve: [
          { timestamp_ms: 1_700_000_000_000, cumulative_pnl: "1.25" },
          { timestamp_ms: 1_700_000_001_000, cumulative_pnl: "2.50" },
        ],
      }),
    );
    const { result } = renderHook(() => useLiveSessionsAggregate([makeSession()]), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.mergedEquityCurve).toHaveLength(2));
    expect(result.current.mergedEquityCurve).toEqual([
      { time: 1_700_000_000, value: 1.25 },
      { time: 1_700_000_001, value: 2.5 },
    ]);
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION_ID}/state`, {
      method: "GET",
      token: "test-token",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("세션별 포지션 팬아웃이 거래소 포지션을 세션 행으로 펼친다", async () => {
    const response = makeSessionPositions(SESSION_ID);
    apiFetchMock.mockResolvedValueOnce(response);
    const { result } = renderHook(() => useLiveSessionsPositions([makeSession()]), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.rows).toHaveLength(1));
    expect(result.current.rows[0]).toMatchObject({
      sessionId: SESSION_ID,
      sessionLabel: STRATEGY_ID.slice(0, 8),
      symbol: "BTCUSDT",
      position: response.positions[0],
    });
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION_ID}/positions`, {
      method: "GET",
      token: "test-token",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("여러 세션 포지션 팬아웃은 같은 심볼도 세션별로 보존한다", async () => {
    const secondSessionId = "20000000-0000-4000-8000-000000000002";
    const sessions = [makeSession(), makeSession({ id: secondSessionId, strategy_id: USER_ID })];
    apiFetchMock.mockImplementation(async (path: string) =>
      path.includes(secondSessionId)
        ? makeSessionPositions(secondSessionId, {
            fetched_at: "2026-08-22T00:01:00Z",
            positions: [makeExchangePosition({ size: "0.2" })],
          })
        : makeSessionPositions(SESSION_ID),
    );
    const { result } = renderHook(() => useLiveSessionsPositions(sessions), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.rows).toHaveLength(2));
    expect(result.current.rows.map((row) => row.sessionId)).toEqual([SESSION_ID, secondSessionId]);
    expect(result.current.latestFetchedAt).toBe("2026-08-22T00:01:00Z");
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION_ID}/positions`, {
      method: "GET",
      token: "test-token",
    });
    expect(apiFetchMock).toHaveBeenCalledWith(
      `/api/v1/live-sessions/${secondSessionId}/positions`,
      {
        method: "GET",
        token: "test-token",
      },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(2);
  });

  it("한 세션의 복수 거래소 포지션도 빠짐없이 세션 행으로 펼친다", async () => {
    apiFetchMock.mockResolvedValueOnce(
      makeSessionPositions(SESSION_ID, {
        positions: [makeExchangePosition({ size: "0.1" }), makeExchangePosition({ size: "0.2" })],
      }),
    );
    const { result } = renderHook(() => useLiveSessionsPositions([makeSession()]), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.rows).toHaveLength(2));
    expect(result.current.rows.map((row) => row.position.size)).toEqual(["0.1", "0.2"]);
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION_ID}/positions`, {
      method: "GET",
      token: "test-token",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("포지션이 없는 정상 세션도 빈 결과로 반환한다", async () => {
    apiFetchMock.mockResolvedValueOnce(makeSessionPositions(SESSION_ID, { positions: [] }));
    const { result } = renderHook(() => useLiveSessionsPositions([makeSession()]), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current).toMatchObject({
      rows: [],
      unsupported: [],
      divergences: [],
      isEmpty: true,
    });
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION_ID}/positions`, {
      method: "GET",
      token: "test-token",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("세션 중단이 DELETE 요청 뒤 사용자 목록 캐시를 무효화한다", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);
    const queryClient = makeClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useDeactivateLiveSession(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(SESSION_ID)).resolves.toBeUndefined();
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION_ID}`, {
      method: "DELETE",
      token: "test-token",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: liveSessionKeys.list("user-1") }),
    );
  });

  it("포지션 조회는 ApiError의 status와 code를 같은 객체로 전파한다", async () => {
    const error = new ApiError(403, "session_forbidden", "session access denied");
    apiFetchMock.mockRejectedValueOnce(error);
    const { result } = renderHook(() => useLiveSessionPositions(SESSION_ID), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(error);
    expect(error).toMatchObject({ status: 403, code: "session_forbidden" });
  });

  it("포지션 조회는 계약을 어긴 응답을 조용히 통과시키지 않는다", async () => {
    apiFetchMock.mockResolvedValueOnce({ session_id: SESSION_ID });
    const { result } = renderHook(() => useLiveSessionPositions(SESSION_ID), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(ZodError);
  });

  it("빈 라이브 세션 목록과 total=0을 그대로 반환한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 0 });
    const { result } = renderHook(() => useLiveSessions(), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.data).toEqual({ items: [], total: 0 }));
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/live-sessions", {
      method: "GET",
      token: "test-token",
    });
  });

  it("비활성 세션 포함 목록은 include_inactive 쿼리를 사용한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 0 });
    const { result } = renderHook(() => useLiveSessions(true), {
      wrapper: makeWrapper(makeClient()),
    });

    await waitFor(() => expect(result.current.data).toEqual({ items: [], total: 0 }));
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/live-sessions?include_inactive=true", {
      method: "GET",
      token: "test-token",
    });
  });

  it("세션 ID가 없으면 state 조회를 발사하지 않는다", () => {
    const { result } = renderHook(() => useLiveSessionState(null, true), {
      wrapper: makeWrapper(makeClient()),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("세션 ID가 없으면 outcome parity 조회를 발사하지 않는다", () => {
    const { result } = renderHook(() => useLiveSessionOutcomeParity(null), {
      wrapper: makeWrapper(makeClient()),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("세션 ID가 없으면 이벤트 조회를 발사하지 않는다", () => {
    const { result } = renderHook(() => useLiveSessionEvents(null, true), {
      wrapper: makeWrapper(makeClient()),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("지원하지 않는 포지션 응답은 별도 목록으로 남기고 빈 상태로 오인하지 않는다", () => {
    const aggregate = combineLiveSessionPositions(
      [makeSession()],
      [
        {
          data: makeSessionPositions(SESSION_ID, {
            supported: false,
            reason: "settings_unset",
            positions: [],
          }),
          isLoading: false,
          isError: false,
          isPending: false,
          refetch: async () => ({}),
        } as never,
      ],
    );

    expect(aggregate).toMatchObject({
      rows: [],
      unsupported: [{ sessionId: SESSION_ID, reason: "settings_unset" }],
      isEmpty: false,
    });
  });

  it("거래소 포지션 없는 local_only는 숫자 스냅샷을 정규화해 발산으로 남긴다", () => {
    const aggregate = combineLiveSessionPositions(
      [makeSession()],
      [
        {
          data: makeSessionPositions(SESSION_ID, {
            positions: [],
            local_open_trades_snapshot: [
              { id: "trade-1", direction: -1, qty: Number.POSITIVE_INFINITY },
            ],
            diff: { verdict: "local_only", local_source: "strategy_state_report" },
          }),
          isLoading: false,
          isError: false,
          isPending: false,
          refetch: async () => ({}),
        } as never,
      ],
    );

    expect(aggregate.divergences).toMatchObject([
      {
        sessionId: SESSION_ID,
        localOpenTrades: [{ id: "trade-1", direction: "-1", qty: null }],
      },
    ]);
    expect(aggregate.isEmpty).toBe(false);
  });

  it("빈 포지션 팬아웃의 refetch는 빈 결과를 반환한다", async () => {
    const aggregate = combineLiveSessionPositions([], []);

    expect(aggregate.isEmpty).toBe(true);
    await expect(aggregate.refetch()).resolves.toEqual([]);
  });

  it("청산 대상이 없으면 mutation은 요청 없이 실패한다", async () => {
    const { result } = renderHook(() => useClosePosition(), {
      wrapper: makeWrapper(makeClient()),
    });

    await expect(result.current.mutateAsync()).rejects.toThrow("close position target is required");
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("청산 mutation key는 세션과 심볼 경계를 보존한다", () => {
    expect(closePositionMutationKey({ sessionId: SESSION_ID, symbol: "BTCUSDT" })).toEqual([
      "close-position",
      SESSION_ID,
      "BTCUSDT",
    ]);
  });
});
