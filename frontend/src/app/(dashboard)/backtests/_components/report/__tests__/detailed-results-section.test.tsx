// DetailedResultsSection — 서브탭 4 + 오버뷰 KPI + waterfall 잠금/벤치마킹 파생 검증
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  BacktestMetricsOut,
  EquityPoint,
} from "@/features/backtest/schemas";

import { DetailedResultsSection } from "@/app/(dashboard)/backtests/_components/report/detailed-results-section";

const METRICS = {
  total_return: 0.2,
  sharpe_ratio: 1.154,
  max_drawdown: -0.1,
  win_rate: 0.6,
  num_trades: 10,
  avg_trade_abs: 6407.08,
  avg_trade_pct: 0.0049,
  open_pnl: 0,
  sortino_ratio: 0.54,
  calmar_ratio: 2.0,
  drawdown_duration: 12,
} as unknown as BacktestMetricsOut;

const EQUITY: EquityPoint[] = [
  { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
  { timestamp: "2026-01-02T00:00:00Z", value: 12000 },
];
const BH: EquityPoint[] = [
  { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
  { timestamp: "2026-01-02T00:00:00Z", value: 11000 },
];

describe("DetailedResultsSection", () => {
  it("서브탭 4종 (오버뷰/수익률/벤치마킹/위험 조정 성과) 렌더", () => {
    render(
      <DetailedResultsSection
        metrics={METRICS}
        equityCurve={EQUITY}
        buyAndHoldCurve={BH}
        initialCapital={10000}
      />,
    );
    for (const label of ["오버뷰", "수익률", "벤치마킹", "위험 조정 성과"]) {
      expect(screen.getByRole("tab", { name: label })).toBeInTheDocument();
    }
  });

  it("오버뷰 KPI — 기대 수익(avg_trade_abs) + 전략 초과 수익 FE 파생 (+1,000)", () => {
    render(
      <DetailedResultsSection
        metrics={METRICS}
        equityCurve={EQUITY}
        buyAndHoldCurve={BH}
        initialCapital={10000}
      />,
    );
    expect(screen.getByText("기대 수익")).toBeInTheDocument();
    expect(screen.getByText("+6,407.08 USDT")).toBeInTheDocument();
    expect(screen.getByText("전략 초과 수익")).toBeInTheDocument();
    // 12000 - 11000 = +1000 / 초기 10000 = +10%
    expect(screen.getByText("+1,000.00 USDT")).toBeInTheDocument();
  });

  it("abs 팩 null (구 백테스트) → waterfall 잠금 empty state", () => {
    render(
      <DetailedResultsSection
        metrics={METRICS}
        equityCurve={EQUITY}
        buyAndHoldCurve={null}
        initialCapital={10000}
      />,
    );
    expect(screen.getByTestId("profit-waterfall-locked")).toBeInTheDocument();
    expect(
      screen.getByText("수익 구조 데이터가 없는 구 백테스트입니다"),
    ).toBeInTheDocument();
  });
});
