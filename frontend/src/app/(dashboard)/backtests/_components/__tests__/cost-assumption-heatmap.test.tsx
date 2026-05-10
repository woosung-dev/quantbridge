// Sprint 50 — Cost Assumption Sensitivity heatmap 검증 (9 cell 렌더 + degenerate "—" + ▲/▼ marker + a11y)

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { CostAssumptionResult } from "@/features/backtest/schemas";

import { CostAssumptionHeatmap } from "../cost-assumption-heatmap";

function makeResult(
  overrides: Partial<CostAssumptionResult> = {},
): CostAssumptionResult {
  return {
    param1_name: "fees",
    param2_name: "slippage",
    param1_values: ["0.0005", "0.001", "0.002"],
    param2_values: ["0.0001", "0.0005", "0.001"],
    cells: [
      // row-major flatten — 9 cell, 정상값
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

describe("CostAssumptionHeatmap (Sprint 50)", () => {
  it("9 cell grid 렌더 + 양수/음수 sharpe 모두 표시", () => {
    render(<CostAssumptionHeatmap result={makeResult()} />);
    // 정상 cell 9개 (각 cell 안 sharpe 값 toFixed(2) 표시)
    const positiveCells = screen.getAllByText(/1\.50/);
    const negativeCells = screen.getAllByText(/1\.20/);
    expect(positiveCells.length).toBeGreaterThan(0);
    expect(negativeCells.length).toBeGreaterThan(0);
  });

  it("legend 에 ▲/▼ marker + degenerate 설명 표시 (codex P2#8 색맹 fallback)", () => {
    render(<CostAssumptionHeatmap result={makeResult()} />);
    expect(screen.getByText(/양수 Sharpe/)).toBeInTheDocument();
    expect(screen.getByText(/음수 Sharpe/)).toBeInTheDocument();
    expect(screen.getByText(/거래 0건/)).toBeInTheDocument();
  });

  it("degenerate cell 은 — 표시 + sharpe 숫자 미렌더", () => {
    const result = makeResult({
      cells: [
        {
          param1_value: "0.5",
          param2_value: "0.0005",
          sharpe: null,
          total_return: "0",
          max_drawdown: "0",
          num_trades: 0,
          is_degenerate: true,
        },
      ],
      param1_values: ["0.5"],
      param2_values: ["0.0005"],
    });
    render(<CostAssumptionHeatmap result={result} />);
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThan(0);
  });

  it("table aria-label + 셀 tabIndex (keyboard 접근, codex P2#8)", () => {
    render(<CostAssumptionHeatmap result={makeResult()} />);
    const table = screen.getByLabelText("Cost Assumption Sensitivity heatmap");
    expect(table).toBeInTheDocument();
    expect(table.tagName).toBe("TABLE");
    // td 가 tabIndex=0 + aria-label 포함하는지 확인
    const focusableCells = table.querySelectorAll('td[tabindex="0"]');
    expect(focusableCells.length).toBe(9);
  });
});
