import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type * as ApiClient from "@/lib/api-client";
import type * as LiveSessionHooks from "@/features/live-sessions/hooks";
import type { AccountPositions, LiveSession } from "@/features/live-sessions/schemas";

const apiFetchMock = vi.hoisted(() => vi.fn());
const mockUseAccountPositions = vi.hoisted(() => vi.fn());
const mockUseLiveSessionsPositions = vi.hoisted(() => vi.fn());

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({
    userId: "user-1",
    getToken: async () => "jwt-token",
  }),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof ApiClient>();
  return { ...actual, apiFetch: apiFetchMock };
});

vi.mock("@/features/live-sessions/hooks", async (importOriginal) => {
  const actual = await importOriginal<typeof LiveSessionHooks>();
  return {
    ...actual,
    useAccountPositions: (...args: unknown[]) => mockUseAccountPositions(...args),
    useLiveSessionsPositions: (...args: unknown[]) => mockUseLiveSessionsPositions(...args),
  };
});

import { AccountPositionsTable } from "../account-positions-table";
import { OpenPositionsTable } from "../open-positions-table";

const ACCOUNT = { id: "b0000000-0000-4000-8000-000000000001", label: "Bybit 데모" };
const SESSION_ID = "a0000000-0000-4000-8000-000000000001";
const SYMBOL = "BTC/USDT";

const session = {
  id: SESSION_ID,
  strategy_id: "a0000000-0000-4000-8000-000000000011",
  is_active: true,
} as unknown as LiveSession;

function position() {
  return {
    side: "long",
    size: "1",
    entry_price: "100",
    mark_price: "100",
    unrealized_pnl: "0",
    take_profit_prices: [],
    stop_loss_prices: [],
    has_trailing_stop: false,
    liquidation_price: null,
    leverage: null,
  };
}

function renderTables(accountSessionId: string, accountSymbol: string) {
  mockUseLiveSessionsPositions.mockReturnValue({
    rows: [
      {
        sessionId: SESSION_ID,
        sessionLabel: "전략 A",
        symbol: SYMBOL,
        verdict: "match",
        position: position(),
      },
    ],
    unsupported: [],
    divergences: [],
    latestFetchedAt: null,
    isLoading: false,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  } as never);
  mockUseAccountPositions.mockReturnValue([
    {
      data: {
        account_id: ACCOUNT.id,
        supported: true,
        reason: null,
        fetched_at: null,
        settle_coin: "USDT",
        truncated: false,
        rows: [
          {
            symbol: accountSymbol,
            position: position(),
            closable_session_id: accountSessionId,
            close_blocked_reason: null,
          },
        ],
      } as AccountPositions,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    },
  ] as never);

  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { gcTime: Infinity } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <OpenPositionsTable sessions={[session]} demoSessionIds={new Set([SESSION_ID])} />
      <AccountPositionsTable accounts={[ACCOUNT]} />
    </QueryClientProvider>,
  );
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

function submitSessionClose() {
  const table = screen.getByRole("table", { name: "세션별 열린 포지션 대조" });
  fireEvent.click(within(table).getByRole("button", { name: "청산" }));
  fireEvent.click(screen.getByRole("button", { name: "청산 실행" }));
}

beforeEach(() => {
  apiFetchMock.mockReset();
  mockUseAccountPositions.mockReset();
  mockUseLiveSessionsPositions.mockReset();
});

describe("close position shared lock", () => {
  it("D1: 세션 표 청산 중 같은 포지션의 계정 표 버튼도 비활성화한다", async () => {
    const request = deferred<{ order_id: string; state: string; detail: null }>();
    apiFetchMock.mockReturnValueOnce(request.promise);
    renderTables(SESSION_ID, SYMBOL);
    const sessionTable = screen.getByRole("table", { name: "세션별 열린 포지션 대조" });
    const accountTable = screen.getByRole("table", { name: "계정별 잔여 포지션" });

    submitSessionClose();

    await waitFor(() =>
      expect(
        within(sessionTable).getByRole("button", { name: "청산 중...", hidden: true }),
      ).toBeDisabled(),
    );
    expect(
      within(accountTable).getByRole("button", { name: "청산 중...", hidden: true }),
    ).toBeDisabled();

    request.resolve({ order_id: "order-1", state: "submitted", detail: null });
    await waitFor(() =>
      expect(within(accountTable).getByRole("button", { name: "청산" })).toBeEnabled(),
    );
  });

  it("D2: 다른 포지션의 계정 표 버튼은 비활성화하지 않는다", async () => {
    const request = deferred<{ order_id: string; state: string; detail: null }>();
    apiFetchMock.mockReturnValueOnce(request.promise);
    renderTables("a0000000-0000-4000-8000-000000000009", "ETH/USDT");
    const sessionTable = screen.getByRole("table", { name: "세션별 열린 포지션 대조" });
    const accountTable = screen.getByRole("table", { name: "계정별 잔여 포지션" });

    submitSessionClose();

    await waitFor(() =>
      expect(
        within(sessionTable).getByRole("button", { name: "청산 중...", hidden: true }),
      ).toBeDisabled(),
    );
    expect(within(accountTable).getByRole("button", { name: "청산", hidden: true })).toBeEnabled();

    request.resolve({ order_id: "order-1", state: "submitted", detail: null });
  });
});
