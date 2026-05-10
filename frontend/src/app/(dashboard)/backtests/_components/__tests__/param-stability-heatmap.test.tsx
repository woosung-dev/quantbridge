// Sprint 51 BL-220 — Param Stability heatmap 검증 (9 cell + ▲/▼ marker + a11y, Sprint 50 cost-assumption 패턴 재사용)

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ParamStabilityResult } from "@/features/backtest/schemas";

import { ParamStabilityHeatmap } from "../param-stability-heatmap";

function makeResult(
  overrides: Partial<ParamStabilityResult> = {},
): ParamStabilityResult {
  return {
    param1_name: "emaPeriod",
    param2_name: "stopLossPct",
    param1_values: ["10", "20", "30"],
    param2_values: ["1.0", "2.0", "3.0"],
    cells: [
      ...Array.from({ length: 9 }, (_, i) => ({
        param1_value: String(i),
        param2_value: String(i),
        sharpe: i % 2 === 0 ? "1.5" : "-1.2",
        total_return: "0.05",
        max_drawdown: "0.02",
        num_trades: 10,
        is_degenerate: false,
      })),
    ],
    ...overrides,
  };
}

describe("ParamStabilityHeatmap (Sprint 51 BL-220)", () => {
  it("9 cell grid 렌더 + 양수/음수 sharpe 모두 표시", () => {
    render(<ParamStabilityHeatmap result={makeResult()} />);
    const positiveCells = screen.getAllByText(/1\.50/);
    const negativeCells = screen.getAllByText(/1\.20/);
    expect(positiveCells.length).toBeGreaterThan(0);
    expect(negativeCells.length).toBeGreaterThan(0);
  });

  it("legend 에 ▲/▼ marker + degenerate 설명 표시 (색맹 fallback)", () => {
    render(<ParamStabilityHeatmap result={makeResult()} />);
    expect(screen.getByText(/양수 Sharpe/)).toBeInTheDocument();
    expect(screen.getByText(/음수 Sharpe/)).toBeInTheDocument();
    expect(screen.getByText(/거래 0건/)).toBeInTheDocument();
  });

  it("degenerate cell 은 — 표시 + sharpe 숫자 미렌더", () => {
    const result = makeResult({
      cells: [
        {
          param1_value: "10",
          param2_value: "1.0",
          sharpe: null,
          total_return: "0",
          max_drawdown: "0",
          num_trades: 0,
          is_degenerate: true,
        },
      ],
      param1_values: ["10"],
      param2_values: ["1.0"],
    });
    render(<ParamStabilityHeatmap result={result} />);
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThan(0);
  });

  it("table aria-label + 셀 tabIndex (keyboard 접근)", () => {
    render(<ParamStabilityHeatmap result={makeResult()} />);
    const table = screen.getByLabelText("Param Stability heatmap");
    expect(table).toBeInTheDocument();
    expect(table.tagName).toBe("TABLE");
    const focusableCells = table.querySelectorAll('td[tabindex="0"]');
    expect(focusableCells.length).toBe(9);
  });
});
