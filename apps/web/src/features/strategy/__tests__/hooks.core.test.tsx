// Strategy React Query 훅의 API 경계·preview query·settings invalidate key 계약.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authMockState, resetAuthMock } from "@/lib/__mocks__/auth-client";

import type * as ApiModule from "../api";
import { listStrategies, parseStrategy } from "../api";
import { strategyKeys, usePreviewParse, useStrategies, useUpdateStrategySettings } from "../hooks";
import type {
  ParsePreviewResponse,
  StrategyListQuery,
  StrategyListResponse,
  StrategyResponse,
  UpdateStrategySettingsRequest,
} from "../schemas";
import type { InvalidatingMutationOptions } from "@/hooks/use-invalidating-mutation";
import { useInvalidatingMutation } from "@/hooks/use-invalidating-mutation";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof ApiModule>();
  return { ...actual, listStrategies: vi.fn(), parseStrategy: vi.fn() };
});

vi.mock("@/hooks/use-invalidating-mutation", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/hooks/use-invalidating-mutation")>();
  return { ...actual, useInvalidatingMutation: vi.fn() };
});

const listStrategiesMock = vi.mocked(listStrategies);
const parseStrategyMock = vi.mocked(parseStrategy);
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

describe("strategy hooks", () => {
  it("useStrategies forwards the auth token and stores the page under the user-scoped key", async () => {
    authMockState.userId = "strategy-user";
    const query: StrategyListQuery = { limit: 20, offset: 0, is_archived: false };
    const page: StrategyListResponse = {
      items: [],
      total: 0,
      page: 1,
      limit: 20,
      total_pages: 0,
    };
    listStrategiesMock.mockResolvedValue(page);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    const { result } = renderHook(() => useStrategies(query), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(page));
    expect(listStrategiesMock).toHaveBeenCalledWith(query, "test-token");
    expect(queryClient.getQueryData(strategyKeys.list("strategy-user", query))).toEqual(page);
  });

  it("usePreviewParse skips blank source and parses the trimmed source", async () => {
    authMockState.userId = "strategy-user";
    const preview: ParsePreviewResponse = {
      status: "ok",
      pine_version: "v5",
      warnings: [],
      errors: [],
      entry_count: 0,
      exit_count: 0,
      functions_used: [],
      unsupported_builtins: [],
      unsupported_calls: [],
      is_runnable: true,
    };
    parseStrategyMock.mockResolvedValue(preview);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result, rerender } = renderHook(({ source }) => usePreviewParse(source), {
      initialProps: { source: "   " },
      wrapper: makeWrapper(queryClient),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(parseStrategyMock).not.toHaveBeenCalled();

    rerender({ source: "  indicator('core')  " });

    await waitFor(() => expect(result.current.data).toEqual(preview));
    expect(parseStrategyMock).toHaveBeenCalledWith("indicator('core')", "test-token");
    expect(
      queryClient.getQueryData(strategyKeys.parsePreview("strategy-user", "indicator('core')")),
    ).toEqual(preview);
  });

  it("useUpdateStrategySettings invalidates the list and server-truth detail keys", () => {
    renderHook(() => useUpdateStrategySettings("strategy-1"));

    const options = useInvalidatingMutationMock.mock.calls[0]?.[0] as InvalidatingMutationOptions<
      StrategyResponse,
      UpdateStrategySettingsRequest
    >;
    const updated = { id: "strategy-1" } as StrategyResponse;
    const request: UpdateStrategySettingsRequest = {
      leverage: 2,
      margin_mode: "cross",
      position_size_pct: 10,
    };

    expect(options.invalidateKeys("strategy-user", updated, request)).toEqual([
      strategyKeys.lists("strategy-user"),
      strategyKeys.detail("strategy-user", "strategy-1"),
    ]);
  });
});
