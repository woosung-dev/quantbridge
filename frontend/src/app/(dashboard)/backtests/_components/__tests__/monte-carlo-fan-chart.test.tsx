// Phase C: MonteCarloFanChart unit test — 빈 입력/정상 입력 분기 + width(-1) 경고 0건.

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { MonteCarloResult } from "@/features/backtest/schemas";
import { MonteCarloFanChart } from "../monte-carlo-fan-chart";

const RESULT_EMPTY: MonteCarloResult = {
  samples: 0,
  ci_lower_95: 0,
  ci_upper_95: 0,
  median_final_equity: 0,
  max_drawdown_mean: 0,
  max_drawdown_p95: 0,
  equity_percentiles: {},
};

const RESULT_3BARS: MonteCarloResult = {
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

describe("MonteCarloFanChart", () => {
  it("renders empty-state when equity_percentiles is empty", () => {
    render(<MonteCarloFanChart result={RESULT_EMPTY} />);
    expect(
      screen.getByText(/Monte Carlo 데이터가 없습니다/),
    ).toBeInTheDocument();
  });

  it("does not emit recharts width(-1) warning in jsdom (placeholder branch)", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const { container } = render(<MonteCarloFanChart result={RESULT_3BARS} />);

    // jsdom 기본: rect width=0 + ResizeObserver 미정의 → placeholder 렌더
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(
      container.querySelector(".recharts-responsive-container"),
    ).toBeNull();

    const hasWarn = warnSpy.mock.calls.some((args) =>
      args.some((a) => typeof a === "string" && /width\(-1\)/.test(a)),
    );
    const hasErr = errSpy.mock.calls.some((args) =>
      args.some((a) => typeof a === "string" && /width\(-1\)/.test(a)),
    );
    expect(hasWarn).toBe(false);
    expect(hasErr).toBe(false);

    warnSpy.mockRestore();
    errSpy.mockRestore();
  });
});
