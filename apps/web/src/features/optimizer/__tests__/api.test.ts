// Optimizer API가 탐색 방식별로 서로 다른 제출 endpoint를 쓰는지 확인한다.
// 네트워크 구현은 apiFetch 하나에 있으므로 이 경계에서만 mock 한다.

import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import { postBayesianSearch, postGeneticSearch, postGridSearch } from "../api";

const TOKEN = "access-token";
const BACKTEST_ID = "22222222-2222-4222-8222-222222222222";
const RUN_ID = "33333333-3333-4333-8333-333333333333";
const USER_ID = "44444444-4444-4444-8444-444444444444";
const REQUEST_BASE = {
  backtest_id: BACKTEST_ID,
  param_space: {
    schema_version: 1,
    objective_metric: "sharpe_ratio",
    direction: "maximize",
    max_evaluations: 4,
    parameters: {
      length: { kind: "integer", min: 5, max: 20, step: 1 },
    },
  },
};

function runResponse(kind: "grid_search" | "bayesian" | "genetic") {
  return {
    id: RUN_ID,
    user_id: USER_ID,
    backtest_id: BACKTEST_ID,
    kind,
    status: "queued",
    param_space: REQUEST_BASE.param_space,
    result: null,
    created_at: "2026-08-22T00:00:00Z",
  };
}

function normalizedRequest(kind: "grid_search" | "bayesian" | "genetic") {
  return {
    ...REQUEST_BASE,
    kind,
    param_space: {
      ...REQUEST_BASE.param_space,
      genetic_selection_method: null,
    },
  };
}

afterEach(() => {
  apiFetchMock.mockReset();
});

describe("optimizer api", () => {
  it("postGridSearch는 grid-search endpoint로 제출한다", async () => {
    const body = { ...REQUEST_BASE, kind: "grid_search" as const };
    apiFetchMock.mockResolvedValueOnce(runResponse(body.kind));

    await expect(postGridSearch(body, TOKEN)).resolves.toMatchObject({ kind: body.kind });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/optimizer/runs/grid-search", {
      method: "POST",
      token: TOKEN,
      body: normalizedRequest(body.kind),
    });
  });

  it("postBayesianSearch는 bayesian endpoint로 제출한다", async () => {
    const body = { ...REQUEST_BASE, kind: "bayesian" as const };
    apiFetchMock.mockResolvedValueOnce(runResponse(body.kind));

    await expect(postBayesianSearch(body, TOKEN)).resolves.toMatchObject({ kind: body.kind });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/optimizer/runs/bayesian", {
      method: "POST",
      token: TOKEN,
      body: normalizedRequest(body.kind),
    });
  });

  it("postGeneticSearch는 genetic endpoint로 제출한다", async () => {
    const body = { ...REQUEST_BASE, kind: "genetic" as const };
    apiFetchMock.mockResolvedValueOnce(runResponse(body.kind));

    await expect(postGeneticSearch(body, TOKEN)).resolves.toMatchObject({ kind: body.kind });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/optimizer/runs/genetic", {
      method: "POST",
      token: TOKEN,
      body: normalizedRequest(body.kind),
    });
  });
});
