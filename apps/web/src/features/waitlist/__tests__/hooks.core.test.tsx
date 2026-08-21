// Waitlist React Query 훅의 공개 제출·관리자 조회·승인 invalidate key 계약.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authMockState, resetAuthMock } from "@/lib/__mocks__/auth-client";
import { ApiError } from "@/lib/api-client";

import type * as ApiModule from "../api";
import { listAdminWaitlist, submitWaitlist } from "../api";
import {
  useAdminWaitlistList,
  useApproveWaitlist,
  useCreateWaitlist,
  waitlistKeys,
} from "../hooks";
import type {
  AdminApproveResponse,
  AdminWaitlistListResponse,
  CreateWaitlistApplication,
} from "../schemas";
import type { InvalidatingMutationOptions } from "@/hooks/use-invalidating-mutation";
import { useInvalidatingMutation } from "@/hooks/use-invalidating-mutation";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof ApiModule>();
  return { ...actual, listAdminWaitlist: vi.fn(), submitWaitlist: vi.fn() };
});

vi.mock("@/hooks/use-invalidating-mutation", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/hooks/use-invalidating-mutation")>();
  return { ...actual, useInvalidatingMutation: vi.fn() };
});

const listAdminWaitlistMock = vi.mocked(listAdminWaitlist);
const submitWaitlistMock = vi.mocked(submitWaitlist);
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

describe("waitlist hooks", () => {
  it("useCreateWaitlist submits the public application without an auth accessor", async () => {
    const body: CreateWaitlistApplication = {
      email: "alice@example.com",
      tv_subscription: "pro",
      exchange_capital: "under_1k",
      pine_experience: "beginner",
      pain_point: "I need one place for validation and execution.",
    };
    const accepted = { id: "11111111-1111-4111-8111-111111111111", status: "pending" } as const;
    submitWaitlistMock.mockResolvedValue(accepted);
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const { result } = renderHook(() => useCreateWaitlist(), {
      wrapper: makeWrapper(queryClient),
    });

    await act(async () => expect(await result.current.mutateAsync(body)).toEqual(accepted));
    expect(submitWaitlistMock).toHaveBeenCalledTimes(1);
    expect(submitWaitlistMock).toHaveBeenCalledWith(body);
  });

  it("useAdminWaitlistList forwards token and stores the admin page under its scoped key", async () => {
    authMockState.userId = "admin-user";
    const query = { status: "pending" as const, limit: 50, offset: 0 };
    const page: AdminWaitlistListResponse = { items: [], total: 0 };
    listAdminWaitlistMock.mockResolvedValue(page);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    const { result } = renderHook(() => useAdminWaitlistList(query), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(page));
    expect(listAdminWaitlistMock).toHaveBeenCalledTimes(1);
    expect(listAdminWaitlistMock).toHaveBeenCalledWith(query, "test-token");
    expect(queryClient.getQueryData(waitlistKeys.adminList("admin-user", query))).toEqual(page);
  });

  it("useAdminWaitlistList preserves zero and negative page bounds at its API boundary", async () => {
    authMockState.userId = "admin-user";
    const query = { limit: 0, offset: -1 };
    const page: AdminWaitlistListResponse = { items: [], total: 0 };
    listAdminWaitlistMock.mockResolvedValue(page);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useAdminWaitlistList(query), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(page));
    expect(listAdminWaitlistMock).toHaveBeenCalledWith(query, "test-token");
  });

  it("useCreateWaitlist forwards an ApiError to its error callback without wrapping it", async () => {
    const body: CreateWaitlistApplication = {
      email: "alice@example.com",
      tv_subscription: "pro",
      exchange_capital: "under_1k",
      pine_experience: "beginner",
      pain_point: "I need one place for validation and execution.",
    };
    const error = new ApiError(422, "invalid_waitlist", "API 422 /api/v1/waitlist");
    const onError = vi.fn();
    submitWaitlistMock.mockRejectedValue(error);
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const { result } = renderHook(() => useCreateWaitlist({ onError }), {
      wrapper: makeWrapper(queryClient),
    });

    await act(async () => expect(result.current.mutateAsync(body)).rejects.toBe(error));
    expect(onError).toHaveBeenCalledWith(error);
    expect(onError).toHaveBeenCalledTimes(1);
  });

  it("useApproveWaitlist invalidates every admin-list variant for the current user", () => {
    renderHook(() => useApproveWaitlist());

    const options = useInvalidatingMutationMock.mock.calls[0]?.[0] as InvalidatingMutationOptions<
      AdminApproveResponse,
      string
    >;
    const response = {
      id: "application-1",
      status: "invited",
      email: "alice@example.com",
      invite_sent_at: null,
    };

    expect(options.invalidateKeys("admin-user", response, "application-1")).toEqual([
      waitlistKeys.adminLists("admin-user"),
    ]);
  });
});
