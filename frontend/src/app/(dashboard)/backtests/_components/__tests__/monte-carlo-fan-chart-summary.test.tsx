// Sprint 43 W10 — prototype 02 정합. Monte Carlo fan chart 위 요약 통계 카드 (CI 95% / median / MDD p95) 검증.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { MonteCarloResult } from "@/features/backtest/schemas";

import { MonteCarloFanChart } from "../monte-carlo-fan-chart";

const RESULT: MonteCarloResult = {
  samples: 1000,
  ci_lower_95: 9500,
  ci_upper_95: 11000,
  median_final_equity: 10500,
  max_drawdown_mean: -500,
  max_drawdown_p95: -1200,
  equity_percentiles: {
    "5": [10000, 9800, 9500],
    "25": [10000, 10000, 9900],
    "50": [10000, 10100, 10300],
    "75": [10000, 10200, 10600],
    "95": [10000, 10400, 11000],
  },
};

describe("MonteCarloFanChart — Sprint 43 W10 prototype 02 summary cards", () => {
  it("3개 요약 카드 (신뢰구간 95% / 중앙값 / 최대 낙폭 p95) 가 표시된다", () => {
    render(<MonteCarloFanChart result={RESULT} />);

    const summary = screen.getByTestId("mc-summary-cards");
    expect(summary).toBeInTheDocument();

    expect(screen.getByText("신뢰구간 95%")).toBeInTheDocument();
    expect(screen.getByText("중앙값 최종 자산")).toBeInTheDocument();
    expect(screen.getByText("최대 낙폭 (p95)")).toBeInTheDocument();
  });

  it("CI 95% 카드는 lower ~ upper 형식으로 값을 보여준다", () => {
    render(<MonteCarloFanChart result={RESULT} />);

    expect(screen.getByText("9,500 ~ 11,000")).toBeInTheDocument();
    expect(
      screen.getByText("1,000 회 시뮬레이션"),
    ).toBeInTheDocument();
  });

  it("MDD p95 카드는 destructive tone 으로 렌더된다", () => {
    const { container } = render(<MonteCarloFanChart result={RESULT} />);

    // 3번째 카드 = MDD. font-mono value 노드에 destructive 색 클래스 포함.
    const valueNodes = container.querySelectorAll(".font-mono.text-lg");
    const mddValue = Array.from(valueNodes).find((n) =>
      (n.textContent ?? "").includes("-1,200"),
    );
    expect(mddValue?.className).toContain("var(--destructive)");
  });

  it("빈 결과 시 요약 카드 표시 없이 empty-state 만 보인다", () => {
    render(
      <MonteCarloFanChart
        result={{ ...RESULT, equity_percentiles: {} }}
      />,
    );

    expect(
      screen.queryByTestId("mc-summary-cards"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/Monte Carlo 데이터가 없습니다/),
    ).toBeInTheDocument();
  });
});
