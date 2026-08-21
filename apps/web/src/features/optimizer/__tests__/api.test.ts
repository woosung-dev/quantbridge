// Optimizer API가 탐색 방식별로 서로 다른 제출 endpoint를 쓰는지 확인한다.
// 네트워크 구현은 apiFetch 하나에 있으므로 이 경계에서만 mock 한다.

import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiFetchMock };
});

import { ApiError } from "@/lib/api-client";
import type { CreateOptimizationRunRequest } from "../schemas";
import {
  getOptimizationRun,
  listOptimizationRuns,
  postBayesianSearch,
  postGeneticSearch,
  postGridSearch,
} from "../api";

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
    genetic_selection_method: null,
  },
} satisfies Omit<CreateOptimizationRunRequest, "kind">;

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
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
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
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
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
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("getOptimizationRun은 실행 상세 endpoint에서 검증된 실행을 반환한다", async () => {
    const response = runResponse("grid_search");
    apiFetchMock.mockResolvedValueOnce(response);

    await expect(getOptimizationRun(RUN_ID, TOKEN)).resolves.toMatchObject({
      id: RUN_ID,
      kind: "grid_search",
    });

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/optimizer/runs/${RUN_ID}`, {
      method: "GET",
      token: TOKEN,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("listOptimizationRuns는 backtest_id를 목록 query params로 보내고 유효 행을 반환한다", async () => {
    const response = {
      items: [runResponse("bayesian")],
      total: 1,
      limit: 10,
      offset: 20,
    };
    apiFetchMock.mockResolvedValueOnce(response);

    await expect(
      listOptimizationRuns({ limit: 10, offset: 20, backtest_id: BACKTEST_ID }, TOKEN),
    ).resolves.toMatchObject({
      items: [{ id: RUN_ID, kind: "bayesian" }],
      total: 1,
      limit: 10,
      offset: 20,
      skipped_count: 0,
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/optimizer/runs", {
      method: "GET",
      token: TOKEN,
      params: { limit: 10, offset: 20, backtest_id: BACKTEST_ID },
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("postGeneticSearch는 ApiError의 status와 code를 감싸지 않고 그대로 전파한다", async () => {
    const body = { ...REQUEST_BASE, kind: "genetic" as const };
    const error = new ApiError(422, "invalid_param_space", "invalid parameter space");
    apiFetchMock.mockRejectedValueOnce(error);

    await expect(postGeneticSearch(body, TOKEN)).rejects.toBe(error);

    expect(error).toMatchObject({ status: 422, code: "invalid_param_space" });
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/optimizer/runs/genetic", {
      method: "POST",
      token: TOKEN,
      body: normalizedRequest("genetic"),
    });
  });

  it("getOptimizationRun은 계약을 어긴 응답을 조용히 반환하지 않는다", async () => {
    apiFetchMock.mockResolvedValueOnce({ id: RUN_ID });

    await expect(getOptimizationRun(RUN_ID, TOKEN)).rejects.toThrow();

    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("listOptimizationRuns는 backtest_id 없이 빈 첫 페이지와 total=0을 보존한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 0, limit: 1, offset: 0 });

    await expect(listOptimizationRuns({ limit: 1, offset: 0 }, null)).resolves.toEqual({
      items: [],
      total: 0,
      limit: 1,
      offset: 0,
      skipped_count: 0,
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/optimizer/runs", {
      method: "GET",
      token: null,
      params: { limit: 1, offset: 0 },
    });
  });

  it("listOptimizationRuns는 outer 목록 계약 위반을 조용히 통과시키지 않는다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: -1, limit: 1, offset: 0 });

    await expect(listOptimizationRuns({ limit: 1, offset: 0 }, TOKEN)).rejects.toThrow();
  });

  it("listOptimizationRuns는 호환 불가 행만 건너뛰고 건너뛴 수를 노출한다", async () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    apiFetchMock.mockResolvedValueOnce({ items: [{ id: RUN_ID }], total: 1, limit: 1, offset: 0 });

    await expect(listOptimizationRuns({ limit: 1, offset: 0 }, TOKEN)).resolves.toEqual({
      items: [],
      total: 1,
      limit: 1,
      offset: 0,
      skipped_count: 1,
    });

    expect(warnSpy).toHaveBeenCalledOnce();
  });

  it.each([0, -1])(
    "postGridSearch는 max_evaluations=%i를 요청 전에 거절한다",
    async (maxEvaluations) => {
      const body = {
        ...REQUEST_BASE,
        kind: "grid_search" as const,
        param_space: { ...REQUEST_BASE.param_space, max_evaluations: maxEvaluations },
      };

      await expect(postGridSearch(body, TOKEN)).rejects.toThrow();

      expect(apiFetchMock).not.toHaveBeenCalled();
    },
  );
});
