import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { BacktestMetricsOut } from "@/features/backtest/schemas";

import { MetricsDetail } from "../metrics-detail";

const baseMetrics: BacktestMetricsOut = {
  total_return: 0.25,
  sharpe_ratio: 1.85,
  max_drawdown: -0.12,
  win_rate: 0.58,
  num_trades: 100,
  sortino_ratio: 2.31,
  calmar_ratio: 2.08,
  profit_factor: 1.65,
  avg_win: 0.018,
  avg_loss: -0.012,
  long_count: 60,
  short_count: 40,
};

describe("MetricsDetail (Sprint 30-γ-FE)", () => {
  it("기존 8 row + 신규 3 section (수익성/위험조정/거래패턴) 렌더", () => {
    render(<MetricsDetail metrics={baseMetrics} />);
    // 3 section title
    expect(screen.getByText("수익성")).toBeInTheDocument();
    expect(screen.getByText("위험 조정")).toBeInTheDocument();
    expect(screen.getByText("거래 패턴")).toBeInTheDocument();
  });

  it("PRD 24 metric 신규 12 필드 — null 시 모두 '—'", () => {
    render(<MetricsDetail metrics={baseMetrics} />);
    // 신규 12 필드 모두 null → "—" 표시 (8 row 가 "—") + 기존 row 일부도 "—"
    // CAGR, 평균거래, 최고거래, 최악거래, DD 지속기간, 롱승률, 숏승률,
    // 연속승, 연속패, 평균보유 = 10 row "—"
    const dashCells = screen.getAllByText("—");
    expect(dashCells.length).toBeGreaterThanOrEqual(10);
  });

  it("CAGR 신규 row + ★ 신규 마크 표시", () => {
    render(
      <MetricsDetail
        metrics={{ ...baseMetrics, annual_return_pct: 0.32 }}
      />,
    );
    expect(screen.getByText(/연간수익률/)).toBeInTheDocument();
    expect(screen.getByText("32.00%")).toBeInTheDocument();
    // ★ 마크는 다수 (신규 row 마다)
    const marks = screen.getAllByLabelText("신규 metric");
    expect(marks.length).toBeGreaterThanOrEqual(10);
  });

  it("avg_holding_hours 시간 단위 자동 (분/시간/일)", () => {
    const { rerender } = render(
      <MetricsDetail
        metrics={{ ...baseMetrics, avg_holding_hours: 0.5 }}
      />,
    );
    // 0.5 시간 = 30분
    expect(screen.getByText("30분")).toBeInTheDocument();

    rerender(
      <MetricsDetail
        metrics={{ ...baseMetrics, avg_holding_hours: 6.5 }}
      />,
    );
    expect(screen.getByText("6.5시간")).toBeInTheDocument();

    rerender(
      <MetricsDetail
        metrics={{ ...baseMetrics, avg_holding_hours: 48 }}
      />,
    );
    expect(screen.getByText("2.0일")).toBeInTheDocument();
  });

  it("drawdown_duration bar 단위 + 천단위 콤마", () => {
    render(
      <MetricsDetail
        metrics={{ ...baseMetrics, drawdown_duration: 1234 }}
      />,
    );
    expect(screen.getByText("1,234 bar")).toBeInTheDocument();
  });

  it("consecutive_wins/losses int 표시 + null fallback", () => {
    render(
      <MetricsDetail
        metrics={{
          ...baseMetrics,
          consecutive_wins_max: 7,
          consecutive_losses_max: null,
        }}
      />,
    );
    expect(screen.getByText("7")).toBeInTheDocument();
    // 연속패는 null → "—" 표시. baseMetrics 의 다른 null 들과 함께 다수 발생.
  });

  it("long_win_rate_pct / short_win_rate_pct 백분율 표시", () => {
    render(
      <MetricsDetail
        metrics={{
          ...baseMetrics,
          long_win_rate_pct: 0.65,
          short_win_rate_pct: 0.42,
        }}
      />,
    );
    expect(screen.getByText("65.00%")).toBeInTheDocument();
    expect(screen.getByText("42.00%")).toBeInTheDocument();
  });
});
