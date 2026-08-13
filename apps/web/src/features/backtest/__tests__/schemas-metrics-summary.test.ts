// 백테스트 목록 성과 요약 스키마의 Decimal 문자열 변환을 검증한다.

import { describe, expect, it } from "vitest";

import { BacktestMetricsSummarySchema } from "@/features/backtest/schemas";

describe("BacktestMetricsSummarySchema", () => {
  it("BE Decimal 문자열을 숫자로 변환하고 nullable 필드를 보존한다", () => {
    const parsed = BacktestMetricsSummarySchema.parse({
      total_return: "0.1234",
      net_profit_abs: "-42.50",
      sharpe_ratio: "1.87",
      sharpe_convention: "tv_monthly_rfr2",
      max_drawdown: "-0.081",
      num_trades: 12,
      total_open_trades: null,
    });

    expect(parsed).toEqual({
      total_return: 0.1234,
      net_profit_abs: -42.5,
      sharpe_ratio: 1.87,
      sharpe_convention: "tv_monthly_rfr2",
      max_drawdown: -0.081,
      num_trades: 12,
      total_open_trades: null,
    });
  });

  it("sharpe_convention 이 없는 구 실행 요약도 파싱한다", () => {
    const parsed = BacktestMetricsSummarySchema.parse({
      total_return: "0.1234",
      net_profit_abs: "-42.50",
      sharpe_ratio: "1.87",
      max_drawdown: "-0.081",
      num_trades: 12,
      total_open_trades: null,
    });

    expect(parsed.sharpe_convention).toBeUndefined();
  });
});
