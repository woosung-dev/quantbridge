// Sprint 43 W10 — prototype 02 정합. KPI 카드 left accent stripe (success/primary/destructive) 검증.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  BacktestConfig,
  BacktestMetricsOut,
} from "@/features/backtest/schemas";

import { MetricsCards } from "../metrics-cards";

const METRICS: BacktestMetricsOut = {
  total_return: 0.5234,
  sharpe_ratio: 2.47,
  max_drawdown: -0.1234,
  win_rate: 0.684,
  num_trades: 42,
  profit_factor: 1.85,
  mdd_exceeds_capital: false,
};

const CONFIG: BacktestConfig = {
  leverage: 1,
};

describe("MetricsCards — Sprint 43 W10 prototype 02 accent", () => {
  it("각 카드에 data-accent (positive/neutral/negative) 가 부여된다", () => {
    const { container } = render(
      <MetricsCards metrics={METRICS} config={CONFIG} />,
    );

    const cards = container.querySelectorAll("[data-accent]");
    expect(cards.length).toBe(5);

    const accents = Array.from(cards).map((c) =>
      c.getAttribute("data-accent"),
    );
    // 총 수익률 = positive (0.52 ≥ 0), Sharpe = neutral, MDD = negative,
    // Profit Factor = neutral, 승률 · 거래 = neutral.
    expect(accents).toEqual([
      "positive",
      "neutral",
      "negative",
      "neutral",
      "neutral",
    ]);
  });

  it("총 수익률 음수 시 accent 가 negative 로 바뀐다", () => {
    const { container } = render(
      <MetricsCards
        metrics={{ ...METRICS, total_return: -0.15 }}
        config={CONFIG}
      />,
    );

    const firstCard = container.querySelector("[data-accent]");
    expect(firstCard?.getAttribute("data-accent")).toBe("negative");
  });

  it("KPI value 폰트 크기 / weight 가 prototype 02 정합 (text-3xl + font-bold)", () => {
    render(<MetricsCards metrics={METRICS} config={CONFIG} />);

    const value = screen.getByText("52.34%");
    expect(value.className).toContain("text-3xl");
    expect(value.className).toContain("font-bold");
  });
});
