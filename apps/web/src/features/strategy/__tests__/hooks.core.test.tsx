// Strategy React Query 훅의 API 경계·preview query·settings invalidate key 계약.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authMockState, resetAuthMock } from "@/lib/__mocks__/auth-client";
import { ApiError } from "@/lib/api-client";

import type * as ApiModule from "../api";
import {
  createStrategy,
  deleteStrategy,
  getStrategy,
  listStrategies,
  parseStrategy,
  rotateWebhookSecret,
  updateStrategy,
} from "../api";
import {
  strategyKeys,
  useCreateStrategy,
  useDeleteStrategy,
  useParseStrategy,
  usePreviewParse,
  useRotateWebhookSecret,
  useStrategies,
  useStrategy,
  useUpdateStrategy,
  useUpdateStrategySettings,
} from "../hooks";
import type {
  CreateStrategyRequest,
  ParsePreviewResponse,
  StrategyCreateResponse,
  StrategyListQuery,
  StrategyListResponse,
  StrategyResponse,
  UpdateStrategySettingsRequest,
  UpdateStrategyRequest,
  WebhookRotateResponse,
} from "../schemas";
import type { InvalidatingMutationOptions } from "@/hooks/use-invalidating-mutation";
import { useInvalidatingMutation } from "@/hooks/use-invalidating-mutation";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof ApiModule>();
  return {
    ...actual,
    createStrategy: vi.fn(),
    deleteStrategy: vi.fn(),
    getStrategy: vi.fn(),
    listStrategies: vi.fn(),
    parseStrategy: vi.fn(),
    rotateWebhookSecret: vi.fn(),
    updateStrategy: vi.fn(),
  };
});

vi.mock("@/hooks/use-invalidating-mutation", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/hooks/use-invalidating-mutation")>();
  return { ...actual, useInvalidatingMutation: vi.fn() };
});

const listStrategiesMock = vi.mocked(listStrategies);
const parseStrategyMock = vi.mocked(parseStrategy);
const createStrategyMock = vi.mocked(createStrategy);
const deleteStrategyMock = vi.mocked(deleteStrategy);
const getStrategyMock = vi.mocked(getStrategy);
const rotateWebhookSecretMock = vi.mocked(rotateWebhookSecret);
const updateStrategyMock = vi.mocked(updateStrategy);
const useInvalidatingMutationMock = vi.mocked(useInvalidatingMutation);

function makeWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

afterEach(() => {
  resetAuthMock();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
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
    expect(listStrategiesMock).toHaveBeenCalledTimes(1);
    expect(listStrategiesMock).toHaveBeenCalledWith(query, "test-token");
    expect(queryClient.getQueryData(strategyKeys.list("strategy-user", query))).toEqual(page);
  });

  it("listStrategies propagates apiFetch ApiError without changing its status or code", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: { code: "strategy_invalid" } }), { status: 422 }),
      );
    vi.stubGlobal("fetch", fetchMock);
    const actualApi = await vi.importActual<typeof ApiModule>("../api");

    const error = await actualApi
      .listStrategies({ limit: 20, offset: 0, is_archived: false }, "test-token")
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 422, code: "strategy_invalid" });
  });

  it("listStrategies rejects a response that violates the list schema", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ items: "not-an-array", total: 0, page: 1, limit: 20, total_pages: 0 }),
          { status: 200 },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    const actualApi = await vi.importActual<typeof ApiModule>("../api");

    await expect(
      actualApi.listStrategies({ limit: 20, offset: 0, is_archived: false }, "test-token"),
    ).rejects.toThrow();
  });

  it("listStrategies rejects zero limit and negative offset before an HTTP request", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const actualApi = await vi.importActual<typeof ApiModule>("../api");

    await expect(
      actualApi.listStrategies({ limit: 0, offset: -1, is_archived: false }, "test-token"),
    ).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("apiFetch omits undefined params and returns void for a 204 response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    const { apiFetch: actualApiFetch } =
      await vi.importActual<typeof import("@/lib/api-client")>("@/lib/api-client");

    await expect(
      actualApiFetch<void>("/api/v1/strategies/strategy-1", {
        method: "DELETE",
        params: { limit: 0, offset: -1, parse_status: undefined },
      }),
    ).resolves.toBeUndefined();

    const [url] = fetchMock.mock.calls[0] ?? [];
    expect(String(url)).toContain("limit=0");
    expect(String(url)).toContain("offset=-1");
    expect(String(url)).not.toContain("parse_status=undefined");
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
      declaration: null,
      inputs: [],
      dogfood_only_warning: null,
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
    expect(parseStrategyMock).toHaveBeenCalledTimes(1);
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
      schema_version: 1,
      leverage: 2,
      margin_mode: "cross",
      position_size_pct: 10,
      max_trigger_breach_pct: null,
      max_reversal_overshoot_ratio: null,
      fill_timing: "bar_close",
    };

    expect(options.invalidateKeys("strategy-user", updated, request)).toEqual([
      strategyKeys.lists("strategy-user"),
      strategyKeys.detail("strategy-user", "strategy-1"),
    ]);
  });

  it("useStrategy returns the fetched detail after one tokenized request", async () => {
    authMockState.userId = "strategy-user";
    const strategy = { id: "strategy-1" } as StrategyResponse;
    getStrategyMock.mockResolvedValue(strategy);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    const { result } = renderHook(() => useStrategy("strategy-1"), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toBe(strategy));
    expect(getStrategyMock).toHaveBeenCalledTimes(1);
    expect(getStrategyMock).toHaveBeenCalledWith("strategy-1", "test-token");
    expect(queryClient.getQueryData(strategyKeys.detail("strategy-user", "strategy-1"))).toBe(
      strategy,
    );
  });

  it("useStrategy disables its detail query when the id is undefined", () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useStrategy(undefined), {
      wrapper: makeWrapper(queryClient),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(getStrategyMock).not.toHaveBeenCalled();
  });

  it("useStrategies exposes the same ApiError returned by its API boundary", async () => {
    const error = new ApiError(503, "upstream_unavailable", "API 503 /api/v1/strategies");
    listStrategiesMock.mockRejectedValue(error);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, retryDelay: 1 } },
    });
    const { result } = renderHook(
      () => useStrategies({ limit: 20, offset: 0, is_archived: false }),
      { wrapper: makeWrapper(queryClient) },
    );

    await waitFor(() => expect(result.current.error).toBe(error));
    expect(result.current.error).toMatchObject({ status: 503, code: "upstream_unavailable" });
  });

  it("useCreateStrategy returns the created strategy from one tokenized request", async () => {
    const body: CreateStrategyRequest = {
      name: "Core strategy",
      pine_source: "strategy('core')",
      tags: [],
    };
    const created = { id: "strategy-1" } as StrategyCreateResponse;
    createStrategyMock.mockResolvedValue(created);
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const { result } = renderHook(() => useCreateStrategy(), {
      wrapper: makeWrapper(queryClient),
    });

    await act(async () => expect(await result.current.mutateAsync(body)).toBe(created));
    expect(createStrategyMock).toHaveBeenCalledTimes(1);
    expect(createStrategyMock).toHaveBeenCalledWith(body, "test-token");
  });

  it("useCreateStrategy forwards an ApiError to its error callback without wrapping it", async () => {
    const body: CreateStrategyRequest = {
      name: "Core strategy",
      pine_source: "strategy('core')",
      tags: [],
    };
    const error = new ApiError(409, "strategy_conflict", "API 409 /api/v1/strategies");
    const onError = vi.fn();
    createStrategyMock.mockRejectedValue(error);
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const { result } = renderHook(() => useCreateStrategy({ onError }), {
      wrapper: makeWrapper(queryClient),
    });

    await act(async () => expect(result.current.mutateAsync(body)).rejects.toBe(error));
    expect(onError).toHaveBeenCalledWith(error);
    expect(onError).toHaveBeenCalledTimes(1);
  });

  it("useRotateWebhookSecret returns the replacement secret from one tokenized request", async () => {
    const rotated = {
      secret: "secret-value",
      webhook_url: "https://example.test/webhook",
    } satisfies WebhookRotateResponse;
    rotateWebhookSecretMock.mockResolvedValue(rotated);
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const { result } = renderHook(() => useRotateWebhookSecret("strategy-1"), {
      wrapper: makeWrapper(queryClient),
    });

    await act(async () => expect(await result.current.mutateAsync()).toBe(rotated));
    expect(rotateWebhookSecretMock).toHaveBeenCalledTimes(1);
    expect(rotateWebhookSecretMock).toHaveBeenCalledWith("strategy-1", "test-token");
  });

  it("useUpdateStrategy returns the updated strategy from one tokenized request", async () => {
    const body: UpdateStrategyRequest = { name: "Renamed strategy" };
    const updated = { id: "strategy-1" } as StrategyResponse;
    updateStrategyMock.mockResolvedValue(updated);
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const { result } = renderHook(() => useUpdateStrategy("strategy-1"), {
      wrapper: makeWrapper(queryClient),
    });

    await act(async () => expect(await result.current.mutateAsync(body)).toBe(updated));
    expect(updateStrategyMock).toHaveBeenCalledTimes(1);
    expect(updateStrategyMock).toHaveBeenCalledWith("strategy-1", body, "test-token");
  });

  it("useDeleteStrategy keeps the delete API boundary and cache keys aligned", async () => {
    renderHook(() => useDeleteStrategy());
    deleteStrategyMock.mockResolvedValue(undefined);

    const options = useInvalidatingMutationMock.mock.calls[0]?.[0] as InvalidatingMutationOptions<
      void,
      string
    >;

    await expect(options.mutationFn("strategy-1", "test-token")).resolves.toBeUndefined();
    expect(deleteStrategyMock).toHaveBeenCalledTimes(1);
    expect(deleteStrategyMock).toHaveBeenCalledWith("strategy-1", "test-token");
    expect(options.removeKeys?.("strategy-user", undefined, "strategy-1")).toEqual([
      strategyKeys.detail("strategy-user", "strategy-1"),
    ]);
    expect(options.invalidateKeys("strategy-user", undefined, "strategy-1")).toEqual([
      strategyKeys.lists("strategy-user"),
    ]);
  });

  it("useParseStrategy returns the parse preview from one tokenized request", async () => {
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
      declaration: null,
      inputs: [],
      dogfood_only_warning: null,
    };
    parseStrategyMock.mockResolvedValue(preview);
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const { result } = renderHook(() => useParseStrategy(), {
      wrapper: makeWrapper(queryClient),
    });

    await act(async () =>
      expect(await result.current.mutateAsync("strategy('core')")).toBe(preview),
    );
    expect(parseStrategyMock).toHaveBeenCalledTimes(1);
    expect(parseStrategyMock).toHaveBeenCalledWith("strategy('core')", "test-token");
  });
});
