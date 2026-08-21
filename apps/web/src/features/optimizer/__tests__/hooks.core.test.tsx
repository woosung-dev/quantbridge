// Optimizer React Query 훅의 목록 조회 경계와 실행 종류별 invalidate key 계약.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authMockState, resetAuthMock } from "@/lib/__mocks__/auth-client";

import type * as ApiModule from "../api";
import {
  listOptimizationRuns,
  postBayesianSearch,
  postGeneticSearch,
  postGridSearch,
} from "../api";
import {
  optimizerKeys,
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
    expect(listOptimizationRunsMock).toHaveBeenCalledWith(query, "test-token");
    expect(queryClient.getQueryData(optimizerKeys.list("optimizer-user", query))).toEqual(page);
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
    expect(postGridSearchMock).toHaveBeenCalledWith(request, "test-token");
    expect(postBayesianSearchMock).toHaveBeenCalledWith(request, "test-token");
    expect(postGeneticSearchMock).toHaveBeenCalledWith(request, "test-token");
    for (const option of options) {
      expect(option.invalidateKeys("optimizer-user", response, request)).toEqual([
        optimizerKeys.all("optimizer-user"),
      ]);
    }
  });
});
