// MetricGroupsSection (03 상세 지표) — .metric-groups 4묶음 + 무데이터 셀(.empty + title) 검증
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  BacktestMetricsOut,
  EquityPoint,
} from "@/features/backtest/schemas";

import { MetricGroupsSection } from "@/app/(dashboard)/backtests/_components/report/metric-groups-section";

const FULL_METRICS = {
  total_return: 1.274,
  annual_return_pct: 0.4328,
  net_profit_abs: 12740.18,
  gross_profit_abs: 21864.3,
  gross_loss_abs: 9124.12,
  profit_factor: 2.4,
  max_drawdown: -0.146,
  drawdown_duration: 38,
  sharpe_ratio: 1.84,
  sortino_ratio: 2.61,
  calmar_ratio: 2.96,
  num_trades: 186,
  win_rate: 0.586,
  avg_win_abs: 200.59,
  avg_loss_abs: 118.5,
  ratio_avg_win_loss: 1.69,
  avg_holding_hours: 65,
  consecutive_wins_max: 9,
  consecutive_losses_max: 5,
  total_fees: 482.16,
  total_slippage: 63.4,
} as unknown as BacktestMetricsOut;

const BH: EquityPoint[] = [
  { timestamp: "2024-01-01T00:00:00Z", value: 10000 },
  { timestamp: "2026-04-14T00:00:00Z", value: 18610 },
];

describe("MetricGroupsSection (03 상세 지표)", () => {
  it("공용 .metric-groups 4묶음(수익성/위험/거래 통계/실행 품질) 시맨틱 구조", () => {
    const { container } = render(
      <MetricGroupsSection metrics={FULL_METRICS} buyAndHoldCurve={BH} />,
    );
    expect(container.querySelector(".metric-groups")).not.toBeNull();
    expect(container.querySelectorAll(".metric-group")).toHaveLength(4);
    for (const title of ["수익성", "위험", "거래 통계", "실행 품질"]) {
      expect(screen.getByText(title)).toBeInTheDocument();
    }
    // 각 묶음 6행 = 24 metric
    expect(container.querySelectorAll(".metric")).toHaveLength(24);
  });

  it("스키마가 받치는 값을 검산대로 렌더 (평균 보유 → 일·시간, 벤치마크 초과 %p 파생)", () => {
    render(<MetricGroupsSection metrics={FULL_METRICS} buyAndHoldCurve={BH} />);
    expect(screen.getByText("+127.40%")).toBeInTheDocument(); // 총 수익률
    expect(screen.getByText("2일 17시간")).toBeInTheDocument(); // 65h → 2일 17시간
    // 벤치마크 초과 = 127.4% - 86.1% = +41.30%p
    expect(screen.getByText("+41.30%p")).toBeInTheDocument();
  });

  it("스키마에 없는 연환산 변동성·베타 = 무데이터 셀(.empty + title)", () => {
    const { container } = render(
      <MetricGroupsSection metrics={FULL_METRICS} buyAndHoldCurve={BH} />,
    );
    const empties = container.querySelectorAll(".metric-value.empty");
    // 연환산 변동성 + 베타 최소 2개 (그 외 값은 전부 채워짐)
    expect(empties.length).toBeGreaterThanOrEqual(2);
    const beta = screen.getByText("베타").closest(".metric")?.querySelector(".metric-value.empty");
    expect(beta).not.toBeNull();
    expect(beta).toHaveAttribute("title", "이 실행에서는 계산되지 않았습니다.");
  });

  it("buyAndHoldCurve 부재 시 벤치마크 초과도 무데이터 셀", () => {
    render(<MetricGroupsSection metrics={FULL_METRICS} buyAndHoldCurve={null} />);
    const excess = screen
      .getByText("벤치마크 초과")
      .closest(".metric")
      ?.querySelector(".metric-value.empty");
    expect(excess).not.toBeNull();
  });
});
