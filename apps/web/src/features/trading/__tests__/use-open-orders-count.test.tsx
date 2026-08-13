// useOpenOrdersCount가 미체결 state 필터의 total만 소비하는지 검증한다.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api-client", () => ({
  apiFetch: apiFetchMock,
  ApiError: class ApiError extends Error {},
}));
vi.mock("@/hooks/use-auth-ctx", () => ({
  useAuthCtx: () => ({ uid: "user-1", getToken: async () => "token" }),
}));

import { useOpenOrdersCount } from "../hooks";

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("useOpenOrdersCount", () => {
  afterEach(() => {
    apiFetchMock.mockReset();
  });

  it("대기·전송 필터의 total만 반환한다", async () => {
    apiFetchMock.mockResolvedValue({ items: [], total: 7 });
    const { result } = renderHook(() => useOpenOrdersCount(), { wrapper });

    await waitFor(() => expect(result.current).toBe(7));
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/orders?state=pending&state=submitted",
      { method: "GET", token: "token", params: { limit: 1, offset: 0 } },
    );
  });
});
