// Optimizer 3폼 characterization 스모크 — 통합 리팩토링 전 기본값 제출 body 를 고정하는 회귀 방어망.
// 폼 구현이 바뀌어도 mutateAsync 로 넘어가는 wire-shape 이 그대로면 green 이어야 한다.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BayesianSearchForm } from "../bayesian-search-form";
import { GeneticSearchForm } from "../genetic-search-form";
import { GridSearchForm } from "../grid-search-form";

const BACKTEST_ID = "3f9c1a52-1111-4222-8333-944455556666";

const gridMutateAsync = vi.fn(async (_body: unknown) => ({ id: "run-grid" }));
const bayesianMutateAsync = vi.fn(async (_body: unknown) => ({ id: "run-bayes" }));
const geneticMutateAsync = vi.fn(async (_body: unknown) => ({ id: "run-gen" }));

vi.mock("@/features/optimizer/hooks", () => ({
  useSubmitGridSearch: () => ({
    mutateAsync: gridMutateAsync,
    isPending: false,
  }),
  useSubmitBayesianSearch: () => ({
    mutateAsync: bayesianMutateAsync,
    isPending: false,
  }),
  useSubmitGeneticSearch: () => ({
    mutateAsync: geneticMutateAsync,
    isPending: false,
  }),
}));

function fillVarName(value: string) {
  fireEvent.change(screen.getByPlaceholderText("변수 이름 (예: length)"), {
    target: { value },
  });
}

beforeEach(() => {
  gridMutateAsync.mockClear();
  bayesianMutateAsync.mockClear();
  geneticMutateAsync.mockClear();
});

describe("GridSearchForm — 기본값 제출 body", () => {
  it("kind=grid_search / schema_version=1 / integer row 숫자 coerce", async () => {
    const onSuccess = vi.fn();
    render(<GridSearchForm backtestId={BACKTEST_ID} onSuccess={onSuccess} />);
    fillVarName("length");
    fireEvent.click(screen.getByRole("button", { name: /그리드 탐색 실행/ }));

    await waitFor(() => expect(gridMutateAsync).toHaveBeenCalledTimes(1));
    expect(gridMutateAsync.mock.calls[0]![0]).toEqual({
      backtest_id: BACKTEST_ID,
      kind: "grid_search",
      param_space: {
        schema_version: 1,
        objective_metric: "sharpe_ratio",
        direction: "maximize",
        max_evaluations: 9,
        parameters: {
          length: { kind: "integer", min: 10, max: 30, step: 5 },
        },
      },
    });
    expect(onSuccess).toHaveBeenCalledWith("run-grid");
  });
});

describe("BayesianSearchForm — 기본값 제출 body", () => {
  it("kind=bayesian / schema_version=2 / min·max 문자열 + prior/log_scale + 고유 필드", async () => {
    const onSuccess = vi.fn();
    render(
      <BayesianSearchForm backtestId={BACKTEST_ID} onSuccess={onSuccess} />,
    );
    fillVarName("length");
    fireEvent.click(screen.getByRole("button", { name: /베이지안 탐색 실행/ }));

    await waitFor(() => expect(bayesianMutateAsync).toHaveBeenCalledTimes(1));
    expect(bayesianMutateAsync.mock.calls[0]![0]).toEqual({
      backtest_id: BACKTEST_ID,
      kind: "bayesian",
      param_space: {
        schema_version: 2,
        objective_metric: "sharpe_ratio",
        direction: "maximize",
        max_evaluations: 15,
        parameters: {
          length: {
            kind: "bayesian",
            min: "5",
            max: "30",
            prior: "uniform",
            log_scale: false,
          },
        },
        bayesian_n_initial_random: 5,
        bayesian_acquisition: "EI",
      },
    });
    expect(onSuccess).toHaveBeenCalledWith("run-bayes");
  });

  it("n_initial_random > max_evaluations 이면 제출 차단 + 에러 노출", async () => {
    render(<BayesianSearchForm backtestId={BACKTEST_ID} />);
    fillVarName("length");
    fireEvent.change(screen.getByLabelText(/초기 랜덤 탐색 횟수/), {
      target: { value: "50" },
    });
    fireEvent.click(screen.getByRole("button", { name: /베이지안 탐색 실행/ }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        /초기 랜덤 탐색 횟수.*클 수 없습니다/,
      ),
    );
    expect(bayesianMutateAsync).not.toHaveBeenCalled();
  });
});

describe("GeneticSearchForm — 기본값 제출 body", () => {
  it("kind=genetic / schema_version=2 / integer row parseInt + 하이퍼파라미터", async () => {
    const onSuccess = vi.fn();
    render(
      <GeneticSearchForm backtestId={BACKTEST_ID} onSuccess={onSuccess} />,
    );
    fillVarName("length");
    fireEvent.click(
      screen.getByRole("button", { name: /유전 알고리즘 탐색 실행/ }),
    );

    await waitFor(() => expect(geneticMutateAsync).toHaveBeenCalledTimes(1));
    expect(geneticMutateAsync.mock.calls[0]![0]).toEqual({
      backtest_id: BACKTEST_ID,
      kind: "genetic",
      param_space: {
        schema_version: 2,
        objective_metric: "sharpe_ratio",
        direction: "maximize",
        max_evaluations: 25,
        parameters: {
          length: { kind: "integer", min: 5, max: 30, step: 1 },
        },
        population_size: 5,
        n_generations: 4,
        mutation_rate: "0.2",
        crossover_rate: "0.8",
        genetic_selection_method: "tournament",
      },
    });
    expect(onSuccess).toHaveBeenCalledWith("run-gen");
  });

  it("budget 초과 (population × (gens+1) > max_evaluations) 시 제출 차단", async () => {
    render(<GeneticSearchForm backtestId={BACKTEST_ID} />);
    fillVarName("length");
    fireEvent.change(screen.getByLabelText(/개체군 크기/), {
      target: { value: "10" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /유전 알고리즘 탐색 실행/ }),
    );

    // budget 10×5=50 > max_evaluations 25 → zod superRefine 이 제출 차단.
    await waitFor(() => expect(geneticMutateAsync).not.toHaveBeenCalled());
  });
});
