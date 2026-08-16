// screen-10 03 파라미터 안정성 섹션 시맨틱 구조 회귀 테스트 (프로토타입 .pgrid/.pcol/.prow/.pbar).

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";

import { ParameterStabilitySection } from "@/features/optimizer/components/parameter-stability-section";
import type { GridSearchCell, GridSearchResult } from "@/features/optimizer/schemas";

function cell(
  params: Record<string, number>,
  objective: number | null,
  numTrades: number,
): GridSearchCell {
  return {
    param_values: params,
    sharpe: objective,
    total_return: objective ?? 0,
    max_drawdown: objective ?? 0,
    num_trades: numTrades,
    is_degenerate: numTrades === 0,
    objective_value: objective,
  };
}

// _KIT.md §4.5 opt_3a90 원장.
const RESULT: GridSearchResult = {
  schema_version: 1,
  kind: "grid_search",
  param_names: ["fastLength", "slowLength"],
  param_values: { fastLength: [10, 20, 30], slowLength: [40, 50, 60] },
  cells: [
    cell({ fastLength: 20, slowLength: 50 }, 1.84, 186),
    cell({ fastLength: 20, slowLength: 60 }, 1.61, 163),
    cell({ fastLength: 20, slowLength: 40 }, 1.53, 224),
    cell({ fastLength: 30, slowLength: 40 }, 1.29, 149),
    cell({ fastLength: 30, slowLength: 50 }, 1.21, 96),
    cell({ fastLength: 10, slowLength: 40 }, 1.12, 312),
    cell({ fastLength: 10, slowLength: 50 }, 0.94, 268),
    cell({ fastLength: 10, slowLength: 60 }, 0.71, 241),
    cell({ fastLength: 30, slowLength: 60 }, null, 0),
  ],
  objective_metric: "sharpe_ratio",
  direction: "maximize",
  best_cell_index: 0,
};

describe("ParameterStabilitySection — screen-10 03 구조", () => {
  afterEach(() => cleanup());

  it(".pgrid 안에 파라미터별 .pcol 2개(fastLength/slowLength)를 그린다", () => {
    render(<ParameterStabilitySection result={RESULT} />);
    const grid = screen.getByTestId("param-stability-grid");
    expect(grid.className).toContain("pgrid");
    const cols = grid.querySelectorAll(".pcol");
    expect(cols).toHaveLength(2);
    const titles = Array.from(grid.querySelectorAll(".pcol-title")).map((e) => e.textContent);
    expect(titles).toEqual(["fastLength", "slowLength"]);
  });

  it("fastLength 값별 평균(0.92/1.66/1.25)을 .pval 로 인쇄하고 최적 값에 .best 를 단다", () => {
    render(<ParameterStabilitySection result={RESULT} />);
    const grid = screen.getByTestId("param-stability-grid");
    const fastCol = grid.querySelectorAll(".pcol")[0]!;
    const pvals = Array.from(fastCol.querySelectorAll(".pval")).map((e) => e.textContent);
    expect(pvals).toEqual(["0.92", "1.66", "1.25"]);
    // 최적(최대) = fastLength 20 → .prow.best
    const best = fastCol.querySelector(".prow.best");
    expect(best).toBeTruthy();
    expect(within(best as HTMLElement).getByText("fastLength 20")).toBeTruthy();
  });

  it("막대는 최고 평균 1.66 을 100% 로 두고 축 시작을 0.00 으로 표기한다", () => {
    render(<ParameterStabilitySection result={RESULT} />);
    const grid = screen.getByTestId("param-stability-grid");
    const fastCol = grid.querySelectorAll(".pcol")[0]!;
    // fastLength 20 막대 폭 100%
    const bestBar = fastCol.querySelector(".prow.best .pbar > span") as HTMLElement;
    expect(bestBar.style.width).toBe("100%");
    // 축 스케일 0.00 ~ 1.66
    const scale = fastCol.querySelector(".pscale-in")!;
    expect(scale.textContent).toBe("0.001.66");
  });

  it("전 셀 축퇴면 무데이터 문구를 그린다", () => {
    const allDegenerate: GridSearchResult = {
      ...RESULT,
      cells: [cell({ fastLength: 10, slowLength: 40 }, null, 0)],
      param_values: { fastLength: [10], slowLength: [40] },
    };
    render(<ParameterStabilitySection result={allDegenerate} />);
    expect(screen.getByTestId("param-stability-nodata")).toBeTruthy();
    expect(screen.queryByTestId("param-stability-grid")).toBeNull();
  });
});
