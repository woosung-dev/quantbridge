// 실제 조회 훅과 QueryClient를 연결하고 API 함수만 대체해 코크핏의 조합 계약을 검증한다.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { alertRuleKeys } from "@/features/alert-rules/query-keys";
import { listLiveSessions } from "@/features/live-sessions/api";
import { useLiveSessions } from "@/features/live-sessions/hooks";
import { liveSessionKeys } from "@/features/live-sessions/query-keys";
import { LiveSessionSchema, type LiveSession } from "@/features/live-sessions/schemas";
import { listStrategies } from "@/features/strategy/api";
import { listCodeStrategies } from "@/features/strategy/code-api";
import { CodeStrategySchema, codeStrategyKeys } from "@/features/strategy/code-schemas";
import { strategyKeys } from "@/features/strategy/query-keys";
import { StrategyListItemSchema } from "@/features/strategy/schemas";
import { authMockState, resetAuthMock } from "@/lib/__mocks__/auth-client";
import { ApiError } from "@/lib/api-client";

import { listExchangeAccounts, listKillSwitchEvents } from "../api";
import { tradingKeys } from "../query-keys";
import { ExchangeAccountSchema, type ExchangeAccount } from "../schemas";
import { useTradingCockpitData } from "../use-trading-cockpit-data";

vi.mock("../api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api")>()),
  listExchangeAccounts: vi.fn(),
  listKillSwitchEvents: vi.fn(),
}));
vi.mock("@/features/live-sessions/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/live-sessions/api")>()),
  listLiveSessions: vi.fn(),
}));
vi.mock("@/features/strategy/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/strategy/api")>()),
  listStrategies: vi.fn(),
}));
vi.mock("@/features/strategy/code-api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/strategy/code-api")>()),
  listCodeStrategies: vi.fn(),
}));

const accountsMock = vi.mocked(listExchangeAccounts);
const killSwitchMock = vi.mocked(listKillSwitchEvents);
const sessionsMock = vi.mocked(listLiveSessions);
const strategiesMock = vi.mocked(listStrategies);
const codeStrategiesMock = vi.mocked(listCodeStrategies);
const clients: QueryClient[] = [];
const ACCOUNT_ID = "10000000-0000-4000-8000-000000000001";
const IDLE_ACCOUNT_ID = "20000000-0000-4000-8000-000000000001";
const LEGACY_ACCOUNT_ID = "30000000-0000-4000-8000-000000000001";
const SESSION_ID = "40000000-0000-4000-8000-000000000001";
const SECOND_SESSION_ID = "50000000-0000-4000-8000-000000000001";
const INACTIVE_SESSION_ID = "60000000-0000-4000-8000-000000000001";
const LEGACY_SESSION_ID = "70000000-0000-4000-8000-000000000001";
const STRATEGY_ID = "80000000-0000-4000-8000-000000000001";
const CODE_ONLY_ID = "90000000-0000-4000-8000-000000000001";
const UNKNOWN_ID = "a0000000-0000-4000-8000-000000000001";
const CREATED_AT = "2026-10-24T00:00:00Z";
const STRATEGY_QUERY = { limit: 100, offset: 0, is_archived: false };

function account(overrides: Partial<ExchangeAccount> = {}): ExchangeAccount {
  return ExchangeAccountSchema.parse({
    id: ACCOUNT_ID,
    exchange: "bybit",
    mode: "demo",
    label: "조회 계정",
    api_key_masked: "***masked***",
    exchange_uid: "exchange-user-1",
    read_only: true,
    created_at: CREATED_AT,
    ...overrides,
  });
}

function session(overrides: Partial<LiveSession> = {}): LiveSession {
  return LiveSessionSchema.parse({
    id: SESSION_ID,
    user_id: "b0000000-0000-4000-8000-000000000001",
    strategy_id: STRATEGY_ID,
    exchange_account_id: ACCOUNT_ID,
    symbol: "BTC/USDT",
    interval: "1h",
    is_active: true,
    last_evaluated_bar_time: null,
    created_at: CREATED_AT,
    deactivated_at: null,
    ...overrides,
  });
}

function makeClient() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, retryDelay: 0, staleTime: Infinity, gcTime: Infinity },
    },
  });
  clients.push(client);
  return client;
}

function wrapper(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  resetAuthMock();
  accountsMock.mockReset().mockResolvedValue([]);
  killSwitchMock.mockReset().mockResolvedValue({ items: [] });
  sessionsMock.mockReset().mockResolvedValue({ items: [], total: 0 });
  strategiesMock.mockReset().mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    limit: 100,
    total_pages: 0,
  });
  codeStrategiesMock.mockReset().mockResolvedValue({ items: [], total: 0 });
});

afterEach(() => {
  cleanup();
  for (const client of clients) client.clear();
  clients.length = 0;
  resetAuthMock();
});

describe("useTradingCockpitData", () => {
  it("비활성 포함 조회를 목록 소비자와 공유하고 다섯 조회를 사용자별 키에 저장한다", async () => {
    const pending = deferred<Awaited<ReturnType<typeof listLiveSessions>>>();
    sessionsMock.mockReturnValue(pending.promise);
    const client = makeClient();
    const { result } = renderHook(
      () => ({ cockpit: useTradingCockpitData(null), list: useLiveSessions(true) }),
      { wrapper: wrapper(client) },
    );

    await waitFor(() => expect(sessionsMock).toHaveBeenCalledTimes(1));
    expect(sessionsMock).toHaveBeenCalledWith("test-token", true);
    const items = [session({ is_active: false })];
    await act(async () => pending.resolve({ items, total: 1 }));
    await waitFor(() => expect(result.current.list.isSuccess).toBe(true));
    expect(result.current.cockpit.sessionTable.sessions).toEqual(items);
    expect(sessionsMock).toHaveBeenCalledTimes(1);
    expect(strategiesMock.mock.calls).toEqual([[STRATEGY_QUERY, "test-token"]]);
    expect(accountsMock.mock.calls).toEqual([["test-token"]]);
    expect(killSwitchMock.mock.calls).toEqual([["test-token"]]);
    expect(codeStrategiesMock.mock.calls).toEqual([["test-token"]]);
    expect(
      client
        .getQueryCache()
        .getAll()
        .map((query) => query.queryKey),
    ).toEqual(
      expect.arrayContaining([
        liveSessionKeys.listWithInactive("user-1"),
        tradingKeys.exchangeAccounts("user-1"),
        tradingKeys.killSwitch("user-1"),
        strategyKeys.list("user-1", STRATEGY_QUERY),
        codeStrategyKeys.list("user-1"),
      ]),
    );
    expect(client.getQueryCache().getAll()).toHaveLength(5);
  });

  it("전체 현황을 보존하면서 Demo 운영 대상·중복 없는 잔고·계정 메타데이터를 나눈다", async () => {
    const demo = account();
    const idle = account({
      id: IDLE_ACCOUNT_ID,
      label: null,
      exchange_uid: null,
      read_only: false,
    });
    const legacy = account({ id: LEGACY_ACCOUNT_ID, mode: "live", label: "이력 계정" });
    const active = session();
    const second = session({ id: SECOND_SESSION_ID });
    const inactive = session({ id: INACTIVE_SESSION_ID, is_active: false });
    const legacySession = session({
      id: LEGACY_SESSION_ID,
      exchange_account_id: LEGACY_ACCOUNT_ID,
    });
    accountsMock.mockResolvedValue([demo, idle, legacy]);
    sessionsMock.mockResolvedValue({ items: [active, second, inactive, legacySession], total: 4 });
    const client = makeClient();
    const { result } = renderHook(() => useTradingCockpitData(null), { wrapper: wrapper(client) });
    await waitFor(() => expect(client.isFetching()).toBe(0));

    expect(result.current.overview.accounts.count).toBe(3);
    expect(result.current.overview.sessions.count).toBe(3);
    expect(result.current.positions.sessions).toEqual([active, second]);
    expect(result.current.positions.demoSessionIds).toEqual(
      new Set([SESSION_ID, SECOND_SESSION_ID]),
    );
    expect(result.current.positions.balanceAccounts).toEqual([
      { id: ACCOUNT_ID, label: demo.label },
    ]);
    expect(result.current.positions.accounts).toEqual([
      { id: ACCOUNT_ID, label: demo.label, exchangeUid: demo.exchange_uid, readOnly: true },
      { id: IDLE_ACCOUNT_ID, label: "bybit demo", exchangeUid: null, readOnly: false },
    ]);
    expect(result.current.registration.activeSessionsCount).toBe(2);
    expect(result.current.registration.exchangeAccounts).toEqual([
      { id: ACCOUNT_ID, exchange: "bybit", mode: "demo", label: demo.label, read_only: true },
      { id: IDLE_ACCOUNT_ID, exchange: "bybit", mode: "demo", label: null, read_only: false },
    ]);
    expect(result.current.sessionTable.sessions).toEqual([active, second, inactive, legacySession]);
    expect(result.current.sessionTable.resolveExchangeLabel(IDLE_ACCOUNT_ID)).toBe("bybit demo");
    expect(result.current.sessionTable.resolveExchangeLabel(UNKNOWN_ID)).toBe(
      UNKNOWN_ID.slice(0, 8),
    );
  });

  it("이름 충돌은 Code가 우선하고 등록 폼은 Pine만 받으며 조회 누락은 기존 fallback을 쓴다", async () => {
    const pine = StrategyListItemSchema.parse({
      id: STRATEGY_ID,
      name: "Pine 원문",
      pine_version: "v5",
      parse_status: "ok",
      parse_errors: null,
      timeframe: "1h",
      symbol: "BTC/USDT",
      is_archived: false,
      created_at: CREATED_AT,
      updated_at: CREATED_AT,
    });
    const code = CodeStrategySchema.parse({
      id: STRATEGY_ID,
      name: "Code 원문",
      description: null,
      symbol: "BTC/USDT",
      timeframe: "1h",
      is_archived: false,
      settings: null,
      version: {
        id: CODE_ONLY_ID,
        schema_version: 1,
        execution_policy: "code_v1",
        language: "python",
        source_code: "def on_bar(ctx): pass",
        warmup_bars: 1,
        params: {},
        provenance: {},
        source_hash: "a".repeat(64),
        execution_hash: "b".repeat(64),
        created_at: CREATED_AT,
      },
    });
    strategiesMock.mockResolvedValue({
      items: [pine],
      total: 1,
      page: 1,
      limit: 100,
      total_pages: 1,
    });
    codeStrategiesMock.mockResolvedValue({
      items: [code, { ...code, id: CODE_ONLY_ID, name: "Code 전용" }],
      total: 2,
    });
    sessionsMock.mockResolvedValue({
      items: [session(), session({ id: SECOND_SESSION_ID, strategy_id: UNKNOWN_ID })],
      total: 2,
    });
    const client = makeClient();
    const { result } = renderHook(() => useTradingCockpitData(null), { wrapper: wrapper(client) });
    await waitFor(() => expect(client.isFetching()).toBe(0));

    expect(result.current.sessionTable.resolveStrategyName(STRATEGY_ID)).toBe("Code 원문");
    expect(result.current.sessionTable.resolveStrategyName(CODE_ONLY_ID)).toBe("Code 전용");
    expect(result.current.sessionTable.resolveStrategyName(UNKNOWN_ID)).toBe(
      UNKNOWN_ID.slice(0, 8),
    );
    expect(result.current.positions.resolveStrategyName(SESSION_ID, "대체 이름")).toBe("Code 원문");
    expect(result.current.positions.resolveStrategyName(SECOND_SESSION_ID, "대체 이름")).toBe(
      UNKNOWN_ID.slice(0, 8),
    );
    expect(result.current.positions.resolveStrategyName(UNKNOWN_ID, "대체 이름")).toBe("대체 이름");
    expect(result.current.registration.strategies).toEqual([
      { id: STRATEGY_ID, name: "Pine 원문" },
    ]);
  });

  it("계정 실패와 세션 로딩을 독립적으로 보존하고 미지 선택을 성공 응답 뒤에 판정한다", async () => {
    const pending = deferred<Awaited<ReturnType<typeof listLiveSessions>>>();
    sessionsMock.mockReturnValue(pending.promise);
    accountsMock.mockRejectedValue(new ApiError(503, "accounts_unavailable", "계정 조회 실패"));
    const unresolved = {
      id: UNKNOWN_ID,
      trigger_type: "daily_loss" as const,
      trigger_value: "100",
      threshold: "90",
      triggered_at: CREATED_AT,
      resolved_at: null,
    };
    killSwitchMock.mockResolvedValue({
      items: [unresolved, { ...unresolved, id: CODE_ONLY_ID, resolved_at: CREATED_AT }],
    });
    const client = makeClient();
    const initialProps: { selectedId: string | null } = { selectedId: UNKNOWN_ID };
    const { result, rerender } = renderHook(
      ({ selectedId }: { selectedId: string | null }) => useTradingCockpitData(selectedId),
      { initialProps, wrapper: wrapper(client) },
    );
    await waitFor(() => expect(result.current.overview.accounts.isError).toBe(true));
    expect(result.current.overview.accounts.isPending).toBe(false);
    expect(result.current.overview.sessions).toEqual({ count: 0, isError: false, isPending: true });
    expect(result.current.overview.killSwitch).toEqual({
      unresolvedCount: 1,
      isError: false,
      isPending: false,
    });
    expect(result.current.selection).toEqual({ status: "loading" });
    rerender({ selectedId: null });
    expect(result.current.selection).toEqual({ status: "none" });
    await act(async () => pending.resolve({ items: [], total: 0 }));
    await waitFor(() => expect(result.current.overview.sessions.isPending).toBe(false));
    rerender({ selectedId: UNKNOWN_ID });
    expect(result.current.selection).toEqual({ status: "missing" });
  });

  it("캐시의 종료 세션은 refetch와 실패 중에도 선택되며 목록 밖 ID만 오류 상태가 된다", async () => {
    const inactive = session({ is_active: false });
    const pending = deferred<Awaited<ReturnType<typeof listLiveSessions>>>();
    sessionsMock.mockReturnValue(pending.promise);
    killSwitchMock.mockRejectedValue(new ApiError(503, "ks_unavailable", "킬 스위치 조회 실패"));
    const client = makeClient();
    const key = liveSessionKeys.listWithInactive("user-1");
    client.setQueryData(key, { items: [inactive], total: 1 });
    const initialProps: { selectedId: string | null } = { selectedId: SESSION_ID };
    const { result, rerender } = renderHook(
      ({ selectedId }: { selectedId: string | null }) => useTradingCockpitData(selectedId),
      { initialProps, wrapper: wrapper(client) },
    );
    let refetch!: Promise<void>;
    act(() => {
      refetch = client.refetchQueries({ queryKey: key });
    });
    await waitFor(() => expect(sessionsMock).toHaveBeenCalledTimes(1));
    expect(result.current.selection).toEqual({ status: "selected", session: inactive });
    rerender({ selectedId: UNKNOWN_ID });
    expect(result.current.selection).toEqual({ status: "loading" });
    await act(async () => {
      pending.reject(new ApiError(503, "sessions_unavailable", "세션 조회 실패"));
      await refetch;
    });
    await waitFor(() => expect(result.current.overview.sessions.isError).toBe(true));
    expect(result.current.selection).toEqual({ status: "error" });
    expect(result.current.overview.accounts).toEqual({
      count: 0,
      isError: false,
      isPending: false,
    });
    expect(result.current.overview.killSwitch.isError).toBe(true);
    rerender({ selectedId: SESSION_ID });
    expect(result.current.selection).toEqual({ status: "selected", session: inactive });
    rerender({ selectedId: null });
    expect(result.current.selection).toEqual({ status: "none" });
  });

  it("UID 변경 뒤 새 사용자만 정확한 다섯 범위로 갱신하고 활성 조회를 다시 요청한다", async () => {
    const firstAccount = account();
    accountsMock.mockResolvedValue([firstAccount]);
    const client = makeClient();
    const { result, rerender } = renderHook(() => useTradingCockpitData(null), {
      wrapper: wrapper(client),
    });
    await waitFor(() => expect(client.isFetching()).toBe(0));
    expect(result.current.overview.accounts.count).toBe(1);

    authMockState.userId = "second-user";
    authMockState.token = "second-token";
    accountsMock.mockResolvedValue([]);
    rerender();
    await waitFor(() => expect(client.isFetching()).toBe(0));
    expect(result.current.overview.accounts.count).toBe(0);
    expect(client.getQueryData(tradingKeys.exchangeAccounts("user-1"))).toEqual([firstAccount]);
    for (const queryKey of [
      tradingKeys.exchangeAccounts("second-user"),
      tradingKeys.killSwitch("second-user"),
      liveSessionKeys.listWithInactive("second-user"),
      strategyKeys.list("second-user", STRATEGY_QUERY),
      codeStrategyKeys.list("second-user"),
    ]) {
      expect(client.getQueryData(queryKey)).toBeDefined();
    }
    const alertKey = alertRuleKeys.list("second-user", SESSION_ID);
    const unrelatedKey = ["backtests", "second-user"];
    client.setQueryData(alertKey, { items: [] });
    client.setQueryData(unrelatedKey, { items: [] });
    const invalidateSpy = vi.spyOn(client, "invalidateQueries");
    act(() => result.current.refresh());
    expect(invalidateSpy.mock.calls).toEqual([
      [{ queryKey: tradingKeys.all("second-user") }],
      [{ queryKey: liveSessionKeys.all("second-user") }],
      [{ queryKey: strategyKeys.all("second-user") }],
      [{ queryKey: codeStrategyKeys.list("second-user") }],
      [{ queryKey: alertRuleKeys.all("second-user") }],
    ]);
    await waitFor(() => expect(client.isFetching()).toBe(0));
    for (const api of [
      accountsMock,
      killSwitchMock,
      sessionsMock,
      strategiesMock,
      codeStrategiesMock,
    ]) {
      expect(api).toHaveBeenCalledTimes(3);
    }
    expect(sessionsMock).toHaveBeenLastCalledWith("second-token", true);
    expect(strategiesMock).toHaveBeenLastCalledWith(STRATEGY_QUERY, "second-token");
    expect(client.getQueryState(alertKey)?.isInvalidated).toBe(true);
    expect(client.getQueryState(unrelatedKey)?.isInvalidated).toBe(false);
    expect(client.getQueryState(tradingKeys.exchangeAccounts("user-1"))?.isInvalidated).toBe(false);
  });
});
