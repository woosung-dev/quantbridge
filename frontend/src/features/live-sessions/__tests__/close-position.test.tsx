// 포지션 청산 mutation이 거래소 요청 뒤 포지션 캐시를 무효화하는지 검증한다.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { liveSessionKeys } from "../query-keys";

const apiFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({
    userId: "user-1",
    getToken: async () => "jwt-token",
  }),
}));

vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import { closePositionMutationKey, useClosePosition } from "../hooks";

function makeWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("useClosePosition", () => {
  it("202 응답을 파싱하고 사용자의 포지션 캐시를 무효화한다", async () => {
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    apiFetchMock.mockResolvedValueOnce({
      order_id: "order-1",
      state: "submitted",
      detail: null,
    });
    const target = { sessionId: "session-1", symbol: "BTCUSDT" };
    const { result } = renderHook(() => useClosePosition(target), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync()).resolves.toMatchObject({
      order_id: "order-1",
      state: "submitted",
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/live-sessions/session-1/positions/close", {
      method: "POST",
      token: "jwt-token",
    });
    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: liveSessionKeys.positionsPrefix("user-1"),
      }),
    );
    expect(queryClient.getMutationCache().getAll()[0]?.options.mutationKey).toEqual(
      closePositionMutationKey(target),
    );
  });
});
