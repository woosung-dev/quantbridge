// RunupDrawdownSection — 잠금 empty state / 팩 존재 시 값 렌더 + "(bar 근사)" 라벨
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { BacktestMetricsOut } from "@/features/backtest/schemas";

import { RunupDrawdownSection } from "@/app/(dashboard)/backtests/_components/report/runup-drawdown-section";

const BASE = {
  total_return: 0.1,
  sharpe_ratio: 1,
  max_drawdown: -0.05,
  win_rate: 0.5,
  num_trades: 4,
} as unknown as BacktestMetricsOut;

describe("RunupDrawdownSection", () => {
  it("excursion_stats null (구 백테스트) → 잠금 empty state + 재실행 안내", () => {
    render(<RunupDrawdownSection metrics={BASE} initialCapital={10000} />);
    expect(screen.getByTestId("runup-drawdown-locked")).toBeInTheDocument();
    expect(
      screen.getByText("런업/드로다운 통계가 없는 구 백테스트입니다"),
    ).toBeInTheDocument();
  });

  it("팩 존재 시 오버뷰 KPI + 서브탭 3 렌더, 인트라바 근사 라벨 명시", () => {
    render(
      <RunupDrawdownSection
        metrics={
          {
            ...BASE,
            excursion_stats: {
              max_runup_abs: 14,
              max_runup_pct: 0.1458,
              avg_runup_abs: 11,
              avg_runup_duration_days: 3,
              avg_drawdown_abs: 7,
              avg_drawdown_duration_days: 2,
              max_drawdown_abs: 12,
              max_drawdown_recovery_bars: 3,
              max_drawdown_recovery_days: 3,
              max_drawdown_intrabar_abs: 17,
              max_drawdown_intrabar_pct: 0.1545,
            },
          } as unknown as BacktestMetricsOut
        }
        initialCapital={100}
      />,
    );
    for (const label of ["오버뷰", "런업", "드로다운"]) {
      expect(screen.getByRole("tab", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByText("평균 상승 지속 기간")).toBeInTheDocument();
    // 평균 상승 지속 3.0 일 + 최대 손실폭 회복 3.0 일 = 2회 등장.
    expect(screen.getAllByText("3.0 일")).toHaveLength(2);
    // 초기 자본 대비 최대 손실률 = 17/100 = 17% + (bar 근사) 라벨
    expect(screen.getByText("17.00%")).toBeInTheDocument();
    expect(screen.getAllByText("(bar 근사)").length).toBeGreaterThan(0);
    expect(screen.getByText("최대 손실폭의 회복")).toBeInTheDocument();
  });

  it("미회복 MDD → '미회복' 표기", () => {
    render(
      <RunupDrawdownSection
        metrics={
          {
            ...BASE,
            excursion_stats: {
              max_drawdown_abs: 30,
              max_drawdown_recovery_bars: null,
              max_drawdown_recovery_days: null,
            },
          } as unknown as BacktestMetricsOut
        }
        initialCapital={10000}
      />,
    );
    expect(screen.getByText("미회복")).toBeInTheDocument();
  });
});
