// Optimizer React Query 훅의 목록 조회 경계와 실행 종류별 invalidate key 계약.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authMockState, resetAuthMock } from "@/lib/__mocks__/auth-client";
import { ApiError } from "@/lib/api-client";

import type * as ApiModule from "../api";
import {
  getOptimizationRun,
  listOptimizationRuns,
  postBayesianSearch,
  postGeneticSearch,
  postGridSearch,
} from "../api";
import {
  optimizerKeys,
  useOptimizationRun,
  useOptimizationRuns,
  useSubmitBayesianSearch,
  useSubmitGeneticSearch,
  useSubmitGridSearch,
} from "../hooks";
import type { OptimizationRunListQuery } from "../query-keys";
import type {
  CreateOptimizationRunRequest,
  OptimizationRunListResponse,
  OptimizationRunResponse,
} from "../schemas";
import type { InvalidatingMutationOptions } from "@/hooks/use-invalidating-mutation";
import { useInvalidatingMutation } from "@/hooks/use-invalidating-mutation";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof ApiModule>();
  return {
    ...actual,
    getOptimizationRun: vi.fn(),
    listOptimizationRuns: vi.fn(),
    postBayesianSearch: vi.fn(),
    postGeneticSearch: vi.fn(),
    postGridSearch: vi.fn(),
  };
});

vi.mock("@/hooks/use-invalidating-mutation", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/hooks/use-invalidating-mutation")>();
  return { ...actual, useInvalidatingMutation: vi.fn() };
});

const listOptimizationRunsMock = vi.mocked(listOptimizationRuns);
const getOptimizationRunMock = vi.mocked(getOptimizationRun);
const postBayesianSearchMock = vi.mocked(postBayesianSearch);
const postGeneticSearchMock = vi.mocked(postGeneticSearch);
const postGridSearchMock = vi.mocked(postGridSearch);
const useInvalidatingMutationMock = vi.mocked(useInvalidatingMutation);

function makeWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

afterEach(() => {
  resetAuthMock();
  vi.clearAllMocks();
});

describe("optimizer hooks", () => {
  it("useOptimizationRuns forwards token and uses the user-scoped list key", async () => {
    authMockState.userId = "optimizer-user";
    const query: OptimizationRunListQuery = { limit: 20, offset: 0 };
    const page: OptimizationRunListResponse = {
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
      skipped_count: 0,
    };
    listOptimizationRunsMock.mockResolvedValue(page);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    const { result } = renderHook(() => useOptimizationRuns(query), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(page));
    expect(listOptimizationRunsMock).toHaveBeenCalledTimes(1);
    expect(listOptimizationRunsMock).toHaveBeenCalledWith(query, "test-token");
    expect(queryClient.getQueryData(optimizerKeys.list("optimizer-user", query))).toEqual(page);
  });

  it("useOptimizationRuns keeps the query idle until the auth user is known", () => {
    authMockState.userId = null;
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useOptimizationRuns({ limit: 0, offset: -1 }), {
      wrapper: makeWrapper(queryClient),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(listOptimizationRunsMock).not.toHaveBeenCalled();
  });

  it("useOptimizationRuns preserves zero and negative page bounds at its API boundary", async () => {
    authMockState.userId = "optimizer-user";
    const query: OptimizationRunListQuery = { limit: 0, offset: -1 };
    const page: OptimizationRunListResponse = {
      items: [],
      total: 0,
      limit: 0,
      offset: -1,
      skipped_count: 0,
    };
    listOptimizationRunsMock.mockResolvedValue(page);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useOptimizationRuns(query), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(page));
    expect(listOptimizationRunsMock).toHaveBeenCalledWith(query, "test-token");
  });

  it("useOptimizationRuns exposes the same ApiError returned by its API boundary", async () => {
    const error = new ApiError(502, "optimizer_unavailable", "API 502 /api/v1/optimizer/runs");
    listOptimizationRunsMock.mockRejectedValue(error);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useOptimizationRuns({ limit: 20, offset: 0 }), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.error).toBe(error));
    expect(result.current.error).toMatchObject({ status: 502, code: "optimizer_unavailable" });
  });

  it("three submit hooks preserve endpoint selection and invalidate the optimizer root key", async () => {
    renderHook(() => {
      useSubmitGridSearch();
      useSubmitBayesianSearch();
      useSubmitGeneticSearch();
    });

    const request = {
      backtest_id: "11111111-1111-4111-8111-111111111111",
    } as CreateOptimizationRunRequest;
    const response = { id: "run-1" } as OptimizationRunResponse;
    postGridSearchMock.mockResolvedValue(response);
    postBayesianSearchMock.mockResolvedValue(response);
    postGeneticSearchMock.mockResolvedValue(response);
    const options = useInvalidatingMutationMock.mock.calls.map(
      ([config]) =>
        config as InvalidatingMutationOptions<
          OptimizationRunResponse,
          CreateOptimizationRunRequest
        >,
    );

    await expect(options[0]?.mutationFn(request, "test-token")).resolves.toBe(response);
    await expect(options[1]?.mutationFn(request, "test-token")).resolves.toBe(response);
    await expect(options[2]?.mutationFn(request, "test-token")).resolves.toBe(response);
    expect(postGridSearchMock).toHaveBeenCalledTimes(1);
    expect(postBayesianSearchMock).toHaveBeenCalledTimes(1);
    expect(postGeneticSearchMock).toHaveBeenCalledTimes(1);
    expect(postGridSearchMock).toHaveBeenCalledWith(request, "test-token");
    expect(postBayesianSearchMock).toHaveBeenCalledWith(request, "test-token");
    expect(postGeneticSearchMock).toHaveBeenCalledWith(request, "test-token");
    for (const option of options) {
      expect(option.invalidateKeys("optimizer-user", response, request)).toEqual([
        optimizerKeys.all("optimizer-user"),
      ]);
    }
  });

  it("useOptimizationRun returns one tokenized detail request under the user-scoped key", async () => {
    authMockState.userId = "optimizer-user";
    const run = { id: "run-1", status: "completed" } as OptimizationRunResponse;
    getOptimizationRunMock.mockResolvedValue(run);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    const { result } = renderHook(() => useOptimizationRun("run-1"), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toBe(run));
    expect(getOptimizationRunMock).toHaveBeenCalledTimes(1);
    expect(getOptimizationRunMock).toHaveBeenCalledWith("run-1", "test-token");
    expect(queryClient.getQueryData(optimizerKeys.detail("optimizer-user", "run-1"))).toBe(run);
  });

  it("useOptimizationRun disables its detail query when its id is null", () => {
    authMockState.userId = "optimizer-user";
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useOptimizationRun(null), {
      wrapper: makeWrapper(queryClient),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(getOptimizationRunMock).not.toHaveBeenCalled();
  });
});
