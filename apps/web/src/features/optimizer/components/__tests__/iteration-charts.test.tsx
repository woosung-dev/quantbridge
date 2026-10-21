import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BayesianIterationChart } from "../bayesian-iteration-chart";
import { GeneticGenerationChart } from "../genetic-generation-chart";
import { BayesianSearchResultSchema, GeneticSearchResultSchema } from "../../schemas";

const common = {
  schema_version: 2,
  param_names: ["fast"],
  best_params: null,
  best_objective_value: null,
  best_iteration_idx: null,
  objective_metric: "sharpe_ratio",
  direction: "maximize",
  max_evaluations: 3,
  degenerate_count: 1,
  total_iterations: 3,
};

function chart(kind: "bayesian" | "genetic", values: (string | null)[]) {
  const iterations = values.map((value, idx) => ({
    idx,
    params: {},
    objective_value: value,
    best_so_far: value,
    is_degenerate: value === null,
    phase: idx === 0 ? "random" : "acquisition",
    generation: idx === 0 ? 0 : 1,
  }));
  if (kind === "bayesian") {
    const result = BayesianSearchResultSchema.parse({
      ...common,
      kind,
      iterations,
      bayesian_acquisition: "EI",
      bayesian_n_initial_random: 1,
    });
    return <BayesianIterationChart result={result} />;
  }
  const result = GeneticSearchResultSchema.parse({
    ...common,
    kind,
    iterations,
    population_size: 2,
    n_generations: 1,
    mutation_rate: "0.1",
    crossover_rate: "0.8",
  });
  return <GeneticGenerationChart result={result} />;
}

describe.each(["bayesian", "genetic"] as const)("%s 반복 차트", (kind) => {
  it("null 반복은 건너뛰고 음수·양수 극값과 원래 반복 위치를 유지한다", () => {
    render(chart(kind, ["-2", null, "3"]));
    const svg = screen.getByRole("img");
    expect(svg.querySelectorAll("circle")).toHaveLength(2);
    expect(svg.querySelector("path")?.getAttribute("d")).toBe("M 28 172 L 612 28");
    expect(svg).toHaveTextContent("-2.000");
    expect(svg).toHaveTextContent("3.000");
  });

  it("값이 하나면 0으로 나누지 않고 선을 그린다", () => {
    render(chart(kind, ["2"]));
    expect(screen.getByRole("img").querySelector("path")?.getAttribute("d")).toBe("M 28 172");
  });

  it("모든 반복이 null이면 축퇴 안내를 표시한다", () => {
    render(chart(kind, [null, null]));
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.getByText(/모든 반복이 축퇴/)).toBeInTheDocument();
  });
});
