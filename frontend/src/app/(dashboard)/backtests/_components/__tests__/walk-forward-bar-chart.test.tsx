// Phase C: WalkForwardBarChart unit test — degradation N/A + truncation 표시 + 빈 fold.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  WalkForwardFold,
  WalkForwardResult,
} from "@/features/backtest/schemas";
import { WalkForwardBarChart } from "../walk-forward-bar-chart";

function makeFold(index: number): WalkForwardFold {
  return {
    fold_index: index,
    train_start: "2026-01-01T00:00:00+00:00",
    train_end: "2026-02-01T00:00:00+00:00",
    test_start: "2026-02-01T00:00:00+00:00",
    test_end: "2026-03-01T00:00:00+00:00",
    in_sample_return: 0.1,
    out_of_sample_return: 0.05,
    oos_sharpe: 1.2,
    num_trades_oos: 5,
  };
}

describe("WalkForwardBarChart", () => {
  it("shows 'N/A' when valid_positive_regime is false", () => {
    const result: WalkForwardResult = {
      folds: [makeFold(0), makeFold(1)],
      aggregate_oos_return: -0.05,
      degradation_ratio: "Infinity",
      valid_positive_regime: false,
      total_possible_folds: 2,
      was_truncated: false,
    };
    render(<WalkForwardBarChart result={result} />);
    expect(screen.getByText(/N\/A/)).toBeInTheDocument();
  });

  it("shows degradation_ratio when valid_positive_regime=true", () => {
    const result: WalkForwardResult = {
      folds: [makeFold(0)],
      aggregate_oos_return: 0.05,
      degradation_ratio: "1.5",
      valid_positive_regime: true,
      total_possible_folds: 1,
      was_truncated: false,
    };
    render(<WalkForwardBarChart result={result} />);
    expect(screen.getByText(/Degradation ratio \(IS\/OOS\): 1\.5/)).toBeInTheDocument();
  });

  it("shows truncation message when was_truncated=true", () => {
    const result: WalkForwardResult = {
      folds: [makeFold(0), makeFold(1), makeFold(2)],
      aggregate_oos_return: 0.1,
      degradation_ratio: "1.2",
      valid_positive_regime: true,
      total_possible_folds: 10,
      was_truncated: true,
    };
    render(<WalkForwardBarChart result={result} />);
    expect(screen.getByText(/3\/10 folds/)).toBeInTheDocument();
  });

  it("shows empty state when folds array is empty", () => {
    const result: WalkForwardResult = {
      folds: [],
      aggregate_oos_return: 0,
      degradation_ratio: "0",
      valid_positive_regime: false,
      total_possible_folds: 0,
      was_truncated: false,
    };
    render(<WalkForwardBarChart result={result} />);
    expect(
      screen.getByText(/fold 데이터가 없습니다/),
    ).toBeInTheDocument();
  });
});
