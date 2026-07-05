// KeyStatsStrip — 4 스탯 렌더 + abs null graceful(% 단독) 검증
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { BacktestMetricsOut } from "@/features/backtest/schemas";

import { KeyStatsStrip } from "../key-stats-strip";

const BASE_METRICS = {
  total_return: 0.1890,
  sharpe_ratio: 1.154,
  max_drawdown: -0.0252,
  win_rate: 0.9898,
  num_trades: 295,
  profit_factor: 21.343,
} as unknown as BacktestMetricsOut;

describe("KeyStatsStrip", () => {
  it("TV 4 스탯 (총 PnL / 최대 손실폭 / 수익성 거래 / 수익지수) 렌더", () => {
    render(
      <KeyStatsStrip
        metrics={{
          ...BASE_METRICS,
          net_profit_abs: 1890087.72,
          excursion_stats: { max_drawdown_abs: 72109.49 },
        } as unknown as BacktestMetricsOut}
      />,
    );
    expect(screen.getByText("총 PnL")).toBeInTheDocument();
    expect(screen.getByText("+1,890,087.72 USDT")).toBeInTheDocument();
    expect(screen.getByText("+18.90%")).toBeInTheDocument();
    expect(screen.getByText("최대 손실폭")).toBeInTheDocument();
    expect(screen.getByText("72,109.49 USDT")).toBeInTheDocument();
    expect(screen.getByText("수익성 거래")).toBeInTheDocument();
    expect(screen.getByText("292/295 거래")).toBeInTheDocument();
    expect(screen.getByText("수익지수")).toBeInTheDocument();
    expect(screen.getByText("21.343")).toBeInTheDocument();
  });

  it("abs 금액 null (구 백테스트) → % 단독 graceful", () => {
    render(<KeyStatsStrip metrics={BASE_METRICS} />);
    // 총 PnL 이 % 로 표기 (USDT 라인 없음)
    expect(screen.getByText("18.90%")).toBeInTheDocument();
    expect(screen.queryByText(/USDT/)).not.toBeInTheDocument();
    // MDD 도 % 단독
    expect(screen.getByText("2.52%")).toBeInTheDocument();
  });

  it("profit_factor null (손실 0건) → em dash", () => {
    render(
      <KeyStatsStrip
        metrics={{ ...BASE_METRICS, profit_factor: null } as unknown as BacktestMetricsOut}
      />,
    );
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.getByText("손실 거래 없음")).toBeInTheDocument();
  });
});
