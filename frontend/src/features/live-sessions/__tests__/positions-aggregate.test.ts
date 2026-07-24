// 활성 세션 포지션 팬아웃 결과가 세션별로 보존되는지 검증한다.
import { describe, expect, it } from "vitest";

import { combineLiveSessionPositions } from "../hooks";

const firstSession = {
  id: "a0000000-0000-4000-8000-000000000001",
  strategy_id: "a0000000-0000-4000-8000-000000000011",
};
const secondSession = {
  id: "a0000000-0000-4000-8000-000000000002",
  strategy_id: "a0000000-0000-4000-8000-000000000012",
};

function result(session: typeof firstSession, positions: Record<string, unknown>) {
  return {
    data: { session, positions },
    isLoading: false,
    isError: false,
    isPending: false,
    refetch: async () => ({}),
  } as never;
}

const exchangePosition = {
  side: "long",
  size: "0.1",
  entry_price: "100",
  mark_price: "110",
  unrealized_pnl: "1",
  liquidation_price: "50",
  leverage: "10",
};

describe("combineLiveSessionPositions", () => {
  it("같은 계정·심볼의 두 세션을 합치지 않고 각각의 전략 라벨로 보존한다", () => {
    const aggregate = combineLiveSessionPositions([
      result(firstSession, {
        supported: true,
        symbol: "BTCUSDT",
        fetched_at: "2026-07-24T12:00:00Z",
        positions: [exchangePosition],
        diff: { verdict: "match" },
      }),
      result(secondSession, {
        supported: true,
        symbol: "BTCUSDT",
        fetched_at: "2026-07-24T12:01:00Z",
        positions: [exchangePosition],
        diff: { verdict: "qty_mismatch" },
      }),
    ]);

    expect(aggregate.rows).toMatchObject([
      { sessionId: firstSession.id, sessionLabel: "a0000000", symbol: "BTCUSDT", verdict: "match" },
      { sessionId: secondSession.id, sessionLabel: "a0000000", symbol: "BTCUSDT", verdict: "qty_mismatch" },
    ]);
    expect(aggregate.latestFetchedAt).toBe("2026-07-24T12:01:00Z");
  });

  it("지원하지 않는 세션은 행과 분리해 사유를 보존한다", () => {
    const aggregate = combineLiveSessionPositions([
      result(firstSession, {
        supported: false,
        symbol: "BTCUSDT",
        fetched_at: null,
        reason: "spot_position_api_unsupported",
      }),
    ]);

    expect(aggregate.rows).toEqual([]);
    expect(aggregate.unsupported).toMatchObject([
      { sessionId: firstSession.id, symbol: "BTCUSDT", reason: "spot_position_api_unsupported" },
    ]);
  });
});
