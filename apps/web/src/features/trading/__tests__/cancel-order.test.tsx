// 주문 취소 실패가 사용자에게 토스트로 표시되는지 검증한다.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => {
  class ApiError extends Error {
    constructor(
      public readonly status: number,
      public readonly code: string,
      message: string,
      public readonly detail?: unknown,
    ) {
      super(message);
    }
  }
  return { apiFetch: vi.fn(), ApiError };
});
const toastError = vi.hoisted(() => vi.fn());

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({
    userId: "user-1",
    getToken: async () => "jwt-token",
  }),
}));
vi.mock("@/lib/api-client", () => ({
  apiFetch: mocks.apiFetch,
  ApiError: mocks.ApiError,
}));
vi.mock("sonner", () => ({
  toast: { error: toastError, info: vi.fn(), success: vi.fn(), warning: vi.fn() },
}));

import { useCancelOrder } from "../hooks";

function makeWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("useCancelOrder", () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset();
    toastError.mockReset();
  });

  it("409가 아닌 실패도 토스트로 알린다", async () => {
    mocks.apiFetch.mockRejectedValueOnce(new mocks.ApiError(500, "server_error", "server error"));
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const { result } = renderHook(() => useCancelOrder(), {
      wrapper: makeWrapper(queryClient),
    });

    result.current.mutate("order-1");

    await waitFor(() =>
      expect(toastError).toHaveBeenCalledWith("주문 취소에 실패했습니다. 잠시 후 다시 시도해주세요."),
    );
  });
});
