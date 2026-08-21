// [BL-786] 목록 서버 prefetch가 클라이언트 queryKey와 실제로 같은지 고정한다.
// React Query는 mock하지 않는다. 페이지가 dehydrate한 상태를 새 QueryClient에 hydrate한 뒤
// 실제 캐시 키를 읽어, SSR 캐시를 클라이언트가 재사용할 수 있는지를 검증한다.

import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  hydrate,
  HydrationBoundary,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import type { DehydratedState } from "@tanstack/react-query";

vi.mock("@/lib/auth-server", () => ({
  getServerAuth: vi.fn(),
}));

vi.mock("@/features/backtest/api", () => ({
  listBacktests: vi.fn(),
}));

vi.mock("@/features/strategy/api", () => ({
  listStrategies: vi.fn(),
}));

vi.mock("@/features/backtest/components/backtest-list", () => ({
  BacktestList: () => <div data-testid="backtest-list-marker" />,
}));

vi.mock("@/features/strategy/components/strategy-list", () => ({
  StrategyList: () => <div data-testid="strategy-list-marker" />,
}));

import BacktestsPage from "../backtests/page";
import StrategiesPage from "../strategies/page";
import { listBacktests } from "@/features/backtest/api";
import {
  BACKTEST_PAGE_SIZE,
  buildBacktestListQuery,
  resolveBacktestSort,
} from "@/features/backtest/list-query";
import { backtestKeys } from "@/features/backtest/query-keys";
import type { BacktestListResponse } from "@/features/backtest/schemas";
import { listStrategies } from "@/features/strategy/api";
import { strategyKeys } from "@/features/strategy/query-keys";
import type { StrategyListResponse } from "@/features/strategy/schemas";
import { resolveStrategySort } from "@/features/strategy/sort";
import { getServerAuth } from "@/lib/auth-server";

type SearchParams = Record<string, string | string[] | undefined>;

const EMPTY_BACKTESTS: BacktestListResponse = {
  items: [],
  total: 0,
  limit: 20,
  offset: 0,
};

const EMPTY_STRATEGIES: StrategyListResponse = {
  items: [],
  total: 0,
  page: 1,
  limit: 20,
  total_pages: 0,
};

const mockedGetServerAuth = vi.mocked(getServerAuth);
const mockedListBacktests = vi.mocked(listBacktests);
const mockedListStrategies = vi.mocked(listStrategies);

function prepareSuccessfulPrefetch(
  userId: string | null = "u1",
  token: string | null = "server-jwt",
) {
  mockedGetServerAuth.mockResolvedValue({ userId, token });
  mockedListBacktests.mockResolvedValue(EMPTY_BACKTESTS);
  mockedListStrategies.mockResolvedValue(EMPTY_STRATEGIES);
}

function getPrefetchedKeys(element: ReactElement) {
  const state = (element.props as { state?: DehydratedState }).state;
  if (!state) throw new Error("HydrationBoundary state가 없습니다.");

  const queryClient = new QueryClient();
  hydrate(queryClient, state);
  return queryClient
    .getQueryCache()
    .getAll()
    .map((query) => query.queryKey);
}

function renderPage(element: ReactElement) {
  return renderToStaticMarkup(
    <QueryClientProvider client={new QueryClient()}>{element}</QueryClientProvider>,
  );
}

async function renderBacktests(searchParams: SearchParams = {}) {
  return BacktestsPage({ searchParams: Promise.resolve(searchParams) });
}

async function renderStrategies(searchParams: SearchParams = {}) {
  return StrategiesPage({ searchParams: Promise.resolve(searchParams) });
}

afterEach(() => vi.resetAllMocks());

describe("[BL-786] 목록 서버 prefetch queryKey", () => {
  it("backtest — 서버 키는 클라이언트의 공용 목록 생성자와 같다", async () => {
    prepareSuccessfulPrefetch();

    const element = await renderBacktests({ order_by: "sharpe_ratio", order: "asc" });

    expect(getPrefetchedKeys(element)).toEqual([
      backtestKeys.list("u1", buildBacktestListQuery("sharpe_ratio", "asc")),
    ]);
  });

  it("strategy — 서버 키는 클라이언트 목록 리터럴의 정규화 값과 같다", async () => {
    prepareSuccessfulPrefetch();

    const element = await renderStrategies({ order_by: "sharpe_ratio", order: "asc" });
    const sort = resolveStrategySort("sharpe_ratio", "asc");

    // strategy는 서버와 클라이언트가 각자 객체를 조립한다.
    // 따라서 공용 생성자가 없는 지금은 값 비교가 두 리터럴의 드리프트를 잡는 계약이다.
    expect(getPrefetchedKeys(element)).toEqual([
      strategyKeys.list("u1", { limit: 20, offset: 0, is_archived: false, ...sort }),
    ]);
  });

  it("backtest — 정렬이 없으면 resolveBacktestSort 기본값으로 키를 만든다", async () => {
    prepareSuccessfulPrefetch();

    const element = await renderBacktests();
    const sort = resolveBacktestSort(undefined, undefined);

    expect(getPrefetchedKeys(element)).toEqual([
      backtestKeys.list("u1", { limit: BACKTEST_PAGE_SIZE, offset: 0, ...sort }),
    ]);
  });

  it("strategy — 정렬이 없으면 resolveStrategySort 기본값으로 키를 만든다", async () => {
    prepareSuccessfulPrefetch();

    const element = await renderStrategies();
    const sort = resolveStrategySort(undefined, undefined);

    expect(getPrefetchedKeys(element)).toEqual([
      strategyKeys.list("u1", { limit: 20, offset: 0, is_archived: false, ...sort }),
    ]);
  });

  it("backtest — 배열 정렬값은 첫 값만 반영한다", async () => {
    prepareSuccessfulPrefetch();

    const element = await renderBacktests({ order_by: ["total_return", "무시될값"] });

    expect(getPrefetchedKeys(element)).toEqual([
      backtestKeys.list("u1", buildBacktestListQuery("total_return", undefined)),
    ]);
  });

  it("strategy — 배열 정렬값은 첫 값만 반영한다", async () => {
    prepareSuccessfulPrefetch();

    const element = await renderStrategies({ order_by: ["total_return", "무시될값"] });
    const sort = resolveStrategySort("total_return", undefined);

    expect(getPrefetchedKeys(element)).toEqual([
      strategyKeys.list("u1", { limit: 20, offset: 0, is_archived: false, ...sort }),
    ]);
  });

  it("backtest — 알 수 없는 정렬은 기본 키로 안전하게 떨어진다", async () => {
    prepareSuccessfulPrefetch();

    const element = await renderBacktests({ order_by: "존재하지않는컬럼" });
    const sort = resolveBacktestSort("존재하지않는컬럼", undefined);

    expect(getPrefetchedKeys(element)).toEqual([
      backtestKeys.list("u1", { limit: BACKTEST_PAGE_SIZE, offset: 0, ...sort }),
    ]);
  });

  it("strategy — 알 수 없는 정렬은 기본 키로 안전하게 떨어진다", async () => {
    prepareSuccessfulPrefetch();

    const element = await renderStrategies({ order_by: "존재하지않는컬럼" });
    const sort = resolveStrategySort("존재하지않는컬럼", undefined);

    expect(getPrefetchedKeys(element)).toEqual([
      strategyKeys.list("u1", { limit: 20, offset: 0, is_archived: false, ...sort }),
    ]);
  });

  it("token이 없으면 인증 요청 없이 두 목록 모두 prefetch하지 않는다", async () => {
    prepareSuccessfulPrefetch("u1", null);

    const [backtests, strategies] = await Promise.all([renderBacktests(), renderStrategies()]);

    expect(mockedListBacktests).not.toHaveBeenCalled();
    expect(mockedListStrategies).not.toHaveBeenCalled();
    expect(getPrefetchedKeys(backtests)).toEqual([]);
    expect(getPrefetchedKeys(strategies)).toEqual([]);
  });

  it("prefetch API가 실패해도 두 페이지는 목록 마커를 렌더한다", async () => {
    prepareSuccessfulPrefetch();
    mockedListBacktests.mockRejectedValueOnce(new Error("backtests unavailable"));
    mockedListStrategies.mockRejectedValueOnce(new Error("strategies unavailable"));

    const [backtests, strategies] = await Promise.all([renderBacktests(), renderStrategies()]);

    expect(() => renderPage(backtests)).not.toThrow();
    expect(() => renderPage(strategies)).not.toThrow();
    expect(renderPage(backtests)).toContain("backtest-list-marker");
    expect(renderPage(strategies)).toContain("strategy-list-marker");
  });

  it("backtest — userId가 null이면 anon 키로 격리한다", async () => {
    prepareSuccessfulPrefetch(null);

    const element = await renderBacktests();

    expect(getPrefetchedKeys(element)).toEqual([
      backtestKeys.list("anon", buildBacktestListQuery(undefined, undefined)),
    ]);
  });

  it("strategy — userId가 null이면 anon 키로 격리한다", async () => {
    prepareSuccessfulPrefetch(null);

    const element = await renderStrategies();
    const sort = resolveStrategySort(undefined, undefined);

    expect(getPrefetchedKeys(element)).toEqual([
      strategyKeys.list("anon", { limit: 20, offset: 0, is_archived: false, ...sort }),
    ]);
  });

  it("backtest — getServerAuth가 준 토큰을 그대로 prefetch에 넘긴다", async () => {
    prepareSuccessfulPrefetch("u1", "backtest-token");

    await renderBacktests({ order_by: "num_trades" });

    expect(mockedListBacktests).toHaveBeenCalledWith(
      buildBacktestListQuery("num_trades", undefined),
      "backtest-token",
    );
  });

  it("strategy — getServerAuth가 준 토큰을 그대로 prefetch에 넘긴다", async () => {
    prepareSuccessfulPrefetch("u1", "strategy-token");

    await renderStrategies({ order_by: "name" });
    const sort = resolveStrategySort("name", undefined);

    expect(mockedListStrategies).toHaveBeenCalledWith(
      { limit: 20, offset: 0, is_archived: false, ...sort },
      "strategy-token",
    );
  });

  it("backtest — HydrationBoundary 상태와 목록 자식을 함께 반환한다", async () => {
    prepareSuccessfulPrefetch();

    const element = await renderBacktests();

    expect(element.type).toBe(HydrationBoundary);
    expect((element.props as { state?: DehydratedState }).state).toBeDefined();
    expect(renderPage(element)).toContain("backtest-list-marker");
  });

  it("strategy — HydrationBoundary 상태와 목록 자식을 함께 반환한다", async () => {
    prepareSuccessfulPrefetch();

    const element = await renderStrategies();

    expect(element.type).toBe(HydrationBoundary);
    expect((element.props as { state?: DehydratedState }).state).toBeDefined();
    expect(renderPage(element)).toContain("strategy-list-marker");
  });
});
