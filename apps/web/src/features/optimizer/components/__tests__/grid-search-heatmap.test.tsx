// 그리드서치 히트맵 칸 매핑 계약 — (행, 열) 칸이 어느 셀의 목표값을 그리는지 잠근다.
// 칸 조회를 「칸마다 전 셀 선형 탐색」에서 「좌표 색인 1회 구축」으로 바꾼 뒤에도
// ① N>2 단면은 최적 셀의 나머지 변수 값으로 고정되고 ② 없는 조합은 빈 칸이며
// ③ 같은 좌표에 셀이 여럿이면 먼저 나온 셀이 이긴다는 종전 동작이 그대로여야 한다.

import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { GridSearchHeatmap } from "../grid-search-heatmap";
import type { GridSearchCell, GridSearchResult } from "@/features/optimizer/schemas";
import { formatObjectiveValue } from "@/features/optimizer/format";
import { EMPTY_CELL } from "@/lib/labels";

afterEach(() => cleanup());

function cell(values: Record<string, number>, objective: number): GridSearchCell {
  return {
    param_values: values,
    sharpe: objective,
    total_return: 0.1,
    max_drawdown: -0.05,
    num_trades: 10,
    is_degenerate: false,
    objective_value: objective,
  };
}

const fmt = (v: number) =>
  formatObjectiveValue("sharpe_ratio", v, {
    percentDigits: 1,
  });

/** tbody 의 데이터 칸 텍스트를 행 단위 2차원 배열로 */
function grid(container: HTMLElement): string[][] {
  return [...container.querySelectorAll("tbody tr")].map((tr) =>
    [...tr.querySelectorAll("td")].map((td) => td.textContent ?? ""),
  );
}

describe("GridSearchHeatmap — 칸 ↔ 셀 매핑", () => {
  it("N>2 이면 최적 셀의 나머지 변수 값으로 고정한 단면만 그린다 · 없는 조합은 빈 칸", () => {
    const result: GridSearchResult = {
      schema_version: 1,
      kind: "grid_search",
      param_names: ["fast", "slow", "mult"],
      param_values: { fast: [10, 20], slow: [40, 50], mult: [1.5, 2.5] },
      cells: [
        cell({ fast: 10, slow: 40, mult: 1.5 }, 1.1),
        // 같은 (fast, slow) 이지만 mult 가 달라 단면 밖 — 그려지면 안 된다.
        cell({ fast: 10, slow: 40, mult: 2.5 }, 9.9),
        cell({ fast: 10, slow: 50, mult: 1.5 }, 1.2),
        cell({ fast: 20, slow: 40, mult: 1.5 }, 2.1),
        // (20, 50, 1.5) 조합 없음 → 빈 칸.
        cell({ fast: 20, slow: 50, mult: 2.5 }, 8.8),
      ],
      objective_metric: "sharpe_ratio",
      direction: "maximize",
      best_cell_index: 3,
    };

    const { container } = render(<GridSearchHeatmap result={result} pair={["fast", "slow"]} />);

    expect(grid(container)).toEqual([
      [fmt(1.1), fmt(1.2)],
      [fmt(2.1), EMPTY_CELL],
    ]);
    // 최적 칸은 (fast=20, slow=40) 하나뿐이다.
    const best = container.querySelectorAll(".hm-cell.best");
    expect(best.length).toBe(1);
    expect(best[0]?.textContent).toBe(fmt(2.1));
  });

  it("대량 셀에서도 전체 결과의 최솟값·최댓값으로 색을 정규화한다", () => {
    const sample = cell({ fast: 10, slow: 40 }, 1);
    const result: GridSearchResult = {
      schema_version: 1,
      kind: "grid_search",
      param_names: ["fast", "slow"],
      param_values: { fast: [10], slow: [40] },
      cells: [...Array<GridSearchCell>(200_000).fill(sample), cell({ fast: 20, slow: 50 }, 3)],
      objective_metric: "sharpe_ratio",
      direction: "maximize",
      best_cell_index: null,
    };
    const { container } = render(<GridSearchHeatmap result={result} pair={["fast", "slow"]} />);
    expect(grid(container)).toEqual([[fmt(1)]]);
    expect(container.querySelector(".hm-cell")?.getAttribute("style")).toContain("5.0%");
  });

  it("같은 좌표에 셀이 여럿이면 먼저 나온 셀을 그린다 (2D)", () => {
    const result: GridSearchResult = {
      schema_version: 1,
      kind: "grid_search",
      param_names: ["fast", "slow"],
      param_values: { fast: [10], slow: [40] },
      cells: [cell({ fast: 10, slow: 40 }, 1.5), cell({ fast: 10, slow: 40 }, 3.5)],
      objective_metric: "sharpe_ratio",
      direction: "maximize",
      best_cell_index: 1,
    };

    const { container } = render(<GridSearchHeatmap result={result} pair={["fast", "slow"]} />);

    expect(grid(container)).toEqual([[fmt(1.5)]]);
  });
});
