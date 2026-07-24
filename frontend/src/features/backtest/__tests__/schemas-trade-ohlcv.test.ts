// 거래 구간 OHLCV 응답의 Decimal 문자열 파싱을 검증한다.

import { describe, expect, it } from "vitest";

import { TradeOhlcvResponseSchema } from "../schemas";

describe("TradeOhlcvResponseSchema", () => {
  it("BE Decimal 문자열 fixture를 숫자로 변환한다", () => {
    const parsed = TradeOhlcvResponseSchema.parse({
      backtest_id: "11111111-1111-4111-8111-111111111111",
      trade_index: 12,
      symbol: "BTC/USDT",
      timeframe: "1h",
      entry_time: "2026-01-01T01:00:00+00:00",
      exit_time: "2026-01-01T03:00:00+00:00",
      pad_bars: 4,
      stride: 1,
      truncated: false,
      bars: [
        {
          time: "2026-01-01T00:00:00+00:00",
          open: "100.10",
          high: "101.20",
          low: "99.80",
          close: "100.50",
          volume: "12.345",
        },
      ],
    });

    expect(parsed.bars[0]).toMatchObject({
      open: 100.1,
      high: 101.2,
      low: 99.8,
      close: 100.5,
      volume: 12.345,
    });
  });
});
