// 미실현 손익의 정상 계산과 훅 조립 경계를 고정한다.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";

const mocks = vi.hoisted(() => ({
  getLiveSessionState: vi.fn(),
  getToken: vi.fn(),
  useQueries: vi.fn(),
}));

vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQueries: mocks.useQueries };
});

vi.mock("@/hooks/use-auth-ctx", () => ({
  useAuthCtx: () => ({ uid: "user-1", getToken: mocks.getToken }),
}));

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return { ...actual, getLiveSessionState: mocks.getLiveSessionState };
});

import { useRealtimeStore } from "@/features/realtime/store";

import { computeUnrealizedPnl, OpenTradeSchema, useUnrealizedPnlEstimate } from "../unrealized";

const SESSION = {
  id: "00000000-0000-4000-a000-000000000031",
  user_id: "00000000-0000-4000-a000-000000000032",
  strategy_id: "00000000-0000-4000-a000-000000000033",
  exchange_account_id: "00000000-0000-4000-a000-000000000034",
  symbol: "BTC/USDT:USDT",
  interval: "1h" as const,
  is_active: true,
  last_evaluated_bar_time: null,
  created_at: "2026-08-22T00:00:00Z",
  deactivated_at: null,
};

const LIVE_STATE = {
  session_id: SESSION.id,
  evaluated: true,
  schema_version: 1,
  last_strategy_state_report: {
    open_trades: [{ direction: "long", qty: 2, entry_price: 100 }],
  },
  total_closed_trades: 0,
  total_realized_pnl: "0",
  equity_curve: [],
  updated_at: "2026-08-22T00:00:00Z",
};

beforeEach(() => {
  mocks.getLiveSessionState.mockReset();
  mocks.getToken.mockReset();
  mocks.useQueries.mockReset();
  useRealtimeStore.getState().reset();
});

afterEach(() => {
  useRealtimeStore.getState().reset();
});

describe("computeUnrealizedPnl 추가 분기", () => {
  it("공백이 있는 유한 mark 가격에서도 short 손익 방향을 반대로 계산한다", () => {
    expect(
      computeUnrealizedPnl(
        [
          { direction: "short", qty: 2, entry_price: 100 },
          { direction: "long", qty: 1, entry_price: 80 },
        ],
        " 90 ",
      ),
    ).toBe(30);
  });

  it("OpenTradeSchema 밖의 방향은 파싱과 손익 계산 모두에서 거절한다", () => {
    const invalidTrade = { direction: "flat", qty: 1, entry_price: 100 };

    expect(OpenTradeSchema.safeParse(invalidTrade).success).toBe(false);
    expect(computeUnrealizedPnl([invalidTrade] as never, "90")).toBeNull();
  });
});

describe("useUnrealizedPnlEstimate 정상 경로", () => {
  it("state query와 ticker를 같은 세션으로 조립해 손익과 최신 시각을 반환한다", async () => {
    mocks.getToken.mockResolvedValue("jwt");
    mocks.getLiveSessionState.mockResolvedValue(LIVE_STATE);
    mocks.useQueries.mockImplementation(({ combine }) => combine([{ data: LIVE_STATE }]));
    useRealtimeStore.getState().applyTicker("BTCUSDT", {
      markPrice: "110",
      lastPrice: "110",
      ts: 1_725_000_000_000,
    });

    const { result, unmount } = renderHook(() => useUnrealizedPnlEstimate([SESSION]));

    expect(result.current).toEqual({
      total: 20,
      isEstimating: false,
      latestTs: 1_725_000_000_000,
    });
    expect(mocks.useQueries).toHaveBeenCalledTimes(1);

    const queryOptions = mocks.useQueries.mock.calls[0]?.[0];
    expect(queryOptions).toBeDefined();
    if (!queryOptions) throw new Error("useQueries options were not captured");
    const { queries } = queryOptions;
    expect(queries).toHaveLength(1);
    expect(queries[0]).toMatchObject({
      queryKey: ["live-sessions", "user-1", "state", SESSION.id],
      enabled: true,
    });

    await expect(queries[0].queryFn()).resolves.toEqual(LIVE_STATE);
    expect(mocks.getToken).toHaveBeenCalledTimes(1);
    expect(mocks.getLiveSessionState).toHaveBeenCalledWith(SESSION.id, "jwt");
    unmount();
  });
});
