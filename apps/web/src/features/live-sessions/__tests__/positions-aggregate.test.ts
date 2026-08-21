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

function result(positions?: Record<string, unknown>) {
  return {
    data: positions,
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
  take_profit_prices: [],
  stop_loss_prices: [],
  has_trailing_stop: false,
  liquidation_price: "50",
  leverage: "10",
};

describe("combineLiveSessionPositions", () => {
  it("같은 계정·심볼의 두 세션을 합치지 않고 각각의 전략 라벨로 보존한다", () => {
    const aggregate = combineLiveSessionPositions(
      [firstSession, secondSession],
      [
        result({
          supported: true,
          symbol: "BTCUSDT",
          fetched_at: "2026-07-24T12:00:00Z",
          positions: [exchangePosition],
          diff: { verdict: "match" },
        }),
        result({
          supported: true,
          symbol: "BTCUSDT",
          fetched_at: "2026-07-24T12:01:00Z",
          positions: [exchangePosition],
          diff: { verdict: "qty_mismatch" },
        }),
      ],
    );

    expect(aggregate.rows).toMatchObject([
      { sessionId: firstSession.id, sessionLabel: "a0000000", symbol: "BTCUSDT", verdict: "match" },
      {
        sessionId: secondSession.id,
        sessionLabel: "a0000000",
        symbol: "BTCUSDT",
        verdict: "qty_mismatch",
      },
    ]);
    expect(aggregate.latestFetchedAt).toBe("2026-07-24T12:01:00Z");
  });

  it("지원하지 않는 세션은 행과 분리해 사유를 보존한다", () => {
    const aggregate = combineLiveSessionPositions(
      [firstSession],
      [
        result({
          supported: false,
          symbol: "BTCUSDT",
          fetched_at: null,
          reason: "spot_position_api_unsupported",
        }),
      ],
    );

    expect(aggregate.rows).toEqual([]);
    expect(aggregate.unsupported).toMatchObject([
      { sessionId: firstSession.id, symbol: "BTCUSDT", reason: "spot_position_api_unsupported" },
    ]);
  });

  it("앞선 disabled 슬롯의 응답이 없어도 다음 세션의 인덱스를 보존한다", () => {
    const aggregate = combineLiveSessionPositions(
      [firstSession, secondSession],
      [
        result(),
        result({
          supported: true,
          symbol: "ETHUSDT",
          fetched_at: null,
          positions: [exchangePosition],
          diff: { verdict: "match" },
        }),
      ],
    );

    expect(aggregate.rows).toMatchObject([{ sessionId: secondSession.id, symbol: "ETHUSDT" }]);
  });
});

// === BL-480 — 발산 판정이 화면에서 사라지던 자리 ===
//
// 행 생성이 `positions` 배열 순회라, `positions` 가 비어 있는 것이 곧 정의인
// `local_only` 는 **정확히 그 순간에만** 행이 하나도 안 만들어졌다. 그래서
// 상위 표가 "열린 포지션이 없습니다" 로 떨어지며 발산을 은폐했다.
// 백엔드는 내내 정확히 보고하고 있었다(실측 2026-07-26: verdict=local_only +
// local_open_trades_snapshot=[PivRevLE long qty 1 @ 64557.51]).

describe("combineLiveSessionPositions — 발산 표면화 (BL-480)", () => {
  it("local_only 는 거래소 포지션이 0이어도 발산으로 남는다", () => {
    const aggregate = combineLiveSessionPositions(
      [firstSession],
      [
        result({
          supported: true,
          symbol: "BTCUSDT",
          fetched_at: "2026-07-26T04:47:19Z",
          positions: [],
          local_open_trades_snapshot: [
            { id: "PivRevLE", direction: "long", qty: 1, entry_price: 64557.51 },
          ],
          diff: { verdict: "local_only", local_source: "strategy_state_report" },
        }),
      ],
    );

    expect(aggregate.rows).toHaveLength(0);
    expect(aggregate.divergences).toMatchObject([
      {
        sessionId: firstSession.id,
        sessionLabel: "a0000000",
        symbol: "BTCUSDT",
        verdict: "local_only",
        localOpenTrades: [{ id: "PivRevLE", direction: "long", qty: "1" }],
      },
    ]);
    // ★핵심 — 상위 표가 "열린 포지션이 없습니다" 로 떨어지면 안 된다.
    expect(aggregate.isEmpty).toBe(false);
  });

  it("양쪽 모두 비어 있으면(match) 발산으로 보지 않는다", () => {
    const aggregate = combineLiveSessionPositions(
      [firstSession],
      [
        result({
          supported: true,
          symbol: "BTCUSDT",
          fetched_at: "2026-07-26T04:47:19Z",
          positions: [],
          local_open_trades_snapshot: [],
          diff: { verdict: "match", local_source: "strategy_state_report" },
        }),
      ],
    );

    expect(aggregate.divergences).toHaveLength(0);
    expect(aggregate.isEmpty).toBe(true);
  });

  it("평가 전(local_source=none)의 unknown 은 발산이 아니다 — 숨길 것이 없다", () => {
    const aggregate = combineLiveSessionPositions(
      [firstSession],
      [
        result({
          supported: true,
          symbol: "BTCUSDT",
          fetched_at: null,
          positions: [],
          local_open_trades_snapshot: [],
          diff: { verdict: "unknown", local_source: "none" },
        }),
      ],
    );

    expect(aggregate.divergences).toHaveLength(0);
    expect(aggregate.isEmpty).toBe(true);
  });

  it("전략 상태는 있는데 대조 불가(unknown)면 발산으로 남긴다", () => {
    // local_source 가 strategy_state_report 인데 unknown = 스냅샷을 못 읽었다는 뜻.
    // 이건 "아직 평가 전" 과 달리 진짜로 알아야 하는 상태다.
    const aggregate = combineLiveSessionPositions(
      [firstSession],
      [
        result({
          supported: true,
          symbol: "BTCUSDT",
          fetched_at: "2026-07-26T04:47:19Z",
          positions: [],
          local_open_trades_snapshot: [{ direction: "sideways", qty: "x" }],
          diff: { verdict: "unknown", local_source: "strategy_state_report" },
        }),
      ],
    );

    expect(aggregate.divergences).toMatchObject([
      { sessionId: firstSession.id, verdict: "unknown" },
    ]);
    expect(aggregate.isEmpty).toBe(false);
  });

  it("거래소 포지션이 있으면 기존대로 행으로만 나가고 발산 목록은 비어 있다", () => {
    const aggregate = combineLiveSessionPositions(
      [firstSession],
      [
        result({
          supported: true,
          symbol: "BTCUSDT",
          fetched_at: "2026-07-26T04:47:19Z",
          positions: [exchangePosition],
          local_open_trades_snapshot: [],
          diff: { verdict: "exchange_only", local_source: "strategy_state_report" },
        }),
      ],
    );

    expect(aggregate.rows).toHaveLength(1);
    expect(aggregate.divergences).toHaveLength(0);
  });
});
