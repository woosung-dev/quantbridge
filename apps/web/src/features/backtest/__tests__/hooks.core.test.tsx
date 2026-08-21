// 백테스트 핵심 React Query 훅 — API 경계·인증 토큰·disabled·polling 불변식 검증.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { authMockState, resetAuthMock } from "@/lib/__mocks__/auth-client";

import type * as ApiModule from "../api";
import {
  backtestKeys,
  useBacktest,
  useBacktestProgress,
  useBacktestTrades,
  useBacktests,
  useCreateBacktestShare,
  useTradeOhlcv,
} from "../hooks";
import type { BacktestListResponse, ShareTokenResponse, TradeOhlcvResponse } from "../schemas";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof ApiModule>();
  return {
    ...actual,
    createBacktestShare: vi.fn(),
    getBacktest: vi.fn(),
    getBacktestProgress: vi.fn(),
    getTradeOhlcv: vi.fn(),
    listBacktestTrades: vi.fn(),
    listBacktests: vi.fn(),
  };
});

import {
  createBacktestShare,
  getBacktest,
  getBacktestProgress,
  getTradeOhlcv,
  listBacktestTrades,
  listBacktests,
} from "../api";

const createBacktestShareMock = vi.mocked(createBacktestShare);
const getBacktestMock = vi.mocked(getBacktest);
const getBacktestProgressMock = vi.mocked(getBacktestProgress);
const getTradeOhlcvMock = vi.mocked(getTradeOhlcv);
const listBacktestTradesMock = vi.mocked(listBacktestTrades);
const listBacktestsMock = vi.mocked(listBacktests);

const USER_ID = "user_core";
const BACKTEST_ID = "11111111-1111-4111-8111-111111111111";
const LIST_QUERY = { limit: 10, offset: 20 };
const TRADES_QUERY = { limit: 50, offset: 0 };

const LIST_RESPONSE: BacktestListResponse = {
  items: [],
  total: 0,
  limit: LIST_QUERY.limit,
  offset: LIST_QUERY.offset,
};

const OHLCV_RESPONSE: TradeOhlcvResponse = {
  backtest_id: BACKTEST_ID,
  trade_index: 7,
  symbol: "BTC/USDT",
  timeframe: "1h",
  entry_time: "2026-08-22T00:00:00+00:00",
  exit_time: null,
  pad_bars: 10,
  stride: 1,
  truncated: false,
  bars: [],
};

const SHARE_RESPONSE: ShareTokenResponse = {
  backtest_id: BACKTEST_ID,
  share_token: "share-token",
  share_url_path: `/backtests/${BACKTEST_ID}/share-token`,
  revoked: false,
};

function makeWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

describe("backtest core hooks", () => {
  beforeEach(() => {
    resetAuthMock();
    authMockState.userId = USER_ID;
    createBacktestShareMock.mockReset();
    getBacktestMock.mockReset();
    getBacktestProgressMock.mockReset();
    getTradeOhlcvMock.mockReset();
    listBacktestTradesMock.mockReset();
    listBacktestsMock.mockReset();
  });

  it("useBacktests는 userId query key와 JWT를 list API에 전달한다", async () => {
    const queryClient = makeQueryClient();
    listBacktestsMock.mockResolvedValue(LIST_RESPONSE);

    const { result } = renderHook(() => useBacktests(LIST_QUERY), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(LIST_RESPONSE));
    expect(listBacktestsMock).toHaveBeenCalledWith(LIST_QUERY, "test-token");
    expect(queryClient.getQueryData(backtestKeys.list(USER_ID, LIST_QUERY))).toEqual(LIST_RESPONSE);
  });

  it("useBacktest는 id가 없으면 API 요청을 시작하지 않는다", async () => {
    const queryClient = makeQueryClient();

    const { result } = renderHook(() => useBacktest(undefined), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.fetchStatus).toBe("idle"));
    expect(getBacktestMock).not.toHaveBeenCalled();
    expect(queryClient.getQueryData(backtestKeys.details(USER_ID))).toBeUndefined();
  });

  it("useBacktestProgress는 API 오류 뒤 polling을 중단한다", async () => {
    const queryClient = makeQueryClient();
    getBacktestProgressMock.mockRejectedValue(new Error("network down"));

    const { result } = renderHook(() => useBacktestProgress(BACKTEST_ID), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(getBacktestProgressMock).toHaveBeenCalledWith(BACKTEST_ID, "test-token");

    const query = queryClient.getQueryCache().find({
      queryKey: backtestKeys.progress(USER_ID, BACKTEST_ID),
    });
    expect(query).toBeDefined();
    if (query === undefined) throw new Error("progress query가 생성되지 않았습니다");

    const refetchInterval = query.options.refetchInterval;
    expect(refetchInterval).toBeTypeOf("function");
    if (typeof refetchInterval === "function") {
      expect(refetchInterval(query)).toBe(false);
    }
  });

  it("useBacktestTrades는 명시적으로 disabled이면 API 요청을 시작하지 않는다", async () => {
    const queryClient = makeQueryClient();

    const { result } = renderHook(
      () => useBacktestTrades(BACKTEST_ID, TRADES_QUERY, { enabled: false }),
      { wrapper: makeWrapper(queryClient) },
    );

    await waitFor(() => expect(result.current.fetchStatus).toBe("idle"));
    expect(listBacktestTradesMock).not.toHaveBeenCalled();
  });

  it("useTradeOhlcv는 getter 경계를 유지하고 결과를 무기한 stale로 둔다", async () => {
    const queryClient = makeQueryClient();
    getTradeOhlcvMock.mockResolvedValue(OHLCV_RESPONSE);

    const { result } = renderHook(() => useTradeOhlcv(BACKTEST_ID, 7), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(OHLCV_RESPONSE));
    expect(getTradeOhlcvMock).toHaveBeenCalledWith(USER_ID, BACKTEST_ID, 7, expect.any(Function));

    const tokenGetter = getTradeOhlcvMock.mock.calls[0]?.[3];
    expect(await tokenGetter?.()).toBe("test-token");
    const query = queryClient.getQueryCache().find({
      queryKey: backtestKeys.tradeOhlcv(USER_ID, BACKTEST_ID, 7),
    });
    expect(query?.options.staleTime).toBe(Infinity);
  });

  it("useCreateBacktestShare는 성공 콜백 전에 JWT로 공유 API를 호출한다", async () => {
    const queryClient = makeQueryClient();
    const onSuccess = vi.fn();
    createBacktestShareMock.mockResolvedValue(SHARE_RESPONSE);

    const { result } = renderHook(() => useCreateBacktestShare({ onSuccess }), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(BACKTEST_ID)).resolves.toEqual(SHARE_RESPONSE);
    expect(createBacktestShareMock).toHaveBeenCalledWith(BACKTEST_ID, "test-token");
    expect(onSuccess).toHaveBeenCalledWith(SHARE_RESPONSE);
  });
});
