// Optimizer REST 래퍼의 현재 경로·요청·응답 스키마 계약을 고정한다.
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import type { CreateOptimizationRunRequest } from "../schemas";
import {
  getOptimizationRun,
  listOptimizationRuns,
  postBayesianSearch,
  postGeneticSearch,
  postGridSearch,
} from "../api";

const TOKEN = "optimizer-contract-token";
const RUN_ID = "00000000-0000-4000-a000-000000000001";
const USER_ID = "00000000-0000-4000-a000-000000000002";
const BACKTEST_ID = "00000000-0000-4000-a000-000000000003";
const STRATEGY_ID = "00000000-0000-4000-a000-000000000004";

const GRID_REQUEST = {
  backtest_id: BACKTEST_ID,
  kind: "grid_search",
  param_space: {
    schema_version: 1,
    objective_metric: "sharpe_ratio",
    direction: "maximize",
    max_evaluations: 10,
    parameters: {
      length: { kind: "integer", min: 5, max: 20, step: 1 },
    },
    genetic_selection_method: null,
  },
} satisfies CreateOptimizationRunRequest;

const BAYESIAN_REQUEST = { ...GRID_REQUEST, kind: "bayesian" as const };
const GENETIC_REQUEST = { ...GRID_REQUEST, kind: "genetic" as const };

// BE OptimizationRunResponse의 필수·nullable 필드를 모두 담은 대표 응답 fixture.
const OPTIMIZATION_RUN = {
  id: RUN_ID,
  user_id: USER_ID,
  backtest_id: BACKTEST_ID,
  strategy_id: STRATEGY_ID,
  backtest_symbol: "BTCUSDT",
  backtest_timeframe: "1h",
  backtest_period_start: "2026-08-01T00:00:00Z",
  backtest_period_end: "2026-08-22T00:00:00Z",
  kind: "grid_search" as const,
  status: "queued" as const,
  param_space: GRID_REQUEST.param_space,
  result: null,
  best_total_return: null,
  best_max_drawdown: null,
  error_message: null,
  created_at: "2026-08-22T00:00:00Z",
  started_at: null,
  completed_at: null,
};

const BAYESIAN_RUN = { ...OPTIMIZATION_RUN, kind: "bayesian" as const };
const GENETIC_RUN = { ...OPTIMIZATION_RUN, kind: "genetic" as const };
const LIST_RESPONSE = { items: [OPTIMIZATION_RUN], total: 1, limit: 20, offset: 40 };
const PARSED_LIST_RESPONSE = { ...LIST_RESPONSE, skipped_count: 0 };

afterEach(() => {
  apiFetchMock.mockReset();
});

describe("optimizer API contract", () => {
  it("현재 계약: Grid Search 제출은 POST 경로·본문·응답을 보존한다", async () => {
    apiFetchMock.mockResolvedValueOnce(OPTIMIZATION_RUN);

    await expect(postGridSearch(GRID_REQUEST, TOKEN)).resolves.toEqual(OPTIMIZATION_RUN);

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/optimizer/runs/grid-search", {
      method: "POST",
      token: TOKEN,
      body: GRID_REQUEST,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("현재 계약: Bayesian 제출은 POST 경로·본문·응답을 보존한다", async () => {
    apiFetchMock.mockResolvedValueOnce(BAYESIAN_RUN);

    await expect(postBayesianSearch(BAYESIAN_REQUEST, TOKEN)).resolves.toEqual(BAYESIAN_RUN);

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/optimizer/runs/bayesian", {
      method: "POST",
      token: TOKEN,
      body: BAYESIAN_REQUEST,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("현재 계약: Genetic 제출은 POST 경로·본문·응답을 보존한다", async () => {
    apiFetchMock.mockResolvedValueOnce(GENETIC_RUN);

    await expect(postGeneticSearch(GENETIC_REQUEST, TOKEN)).resolves.toEqual(GENETIC_RUN);

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/optimizer/runs/genetic", {
      method: "POST",
      token: TOKEN,
      body: GENETIC_REQUEST,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("현재 계약: 상세 조회는 run 식별자 GET 경로와 응답을 보존한다", async () => {
    apiFetchMock.mockResolvedValueOnce(OPTIMIZATION_RUN);

    await expect(getOptimizationRun(RUN_ID, TOKEN)).resolves.toEqual(OPTIMIZATION_RUN);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/optimizer/runs/${RUN_ID}`, {
      method: "GET",
      token: TOKEN,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("현재 계약: 목록 조회는 backtest query를 보내고 유효 행 필터링 결과를 반환한다", async () => {
    const query = { limit: 20, offset: 40, backtest_id: BACKTEST_ID };
    apiFetchMock.mockResolvedValueOnce(LIST_RESPONSE);

    await expect(listOptimizationRuns(query, TOKEN)).resolves.toEqual(PARSED_LIST_RESPONSE);

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/optimizer/runs", {
      method: "GET",
      token: TOKEN,
      params: query,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });
});
