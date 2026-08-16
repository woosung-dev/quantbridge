// 포지션 청산 mutation이 거래소 요청 뒤 포지션 캐시를 무효화하는지 검증한다.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { liveSessionKeys } from "../query-keys";

const apiFetchMock = vi.hoisted(() => vi.fn());

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
      token: "test-token",
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

  it("잔량 필드를 스키마가 버리지 않는다 (BL-688)", async () => {
    // ★`z.object` 는 기본이 strip 이라 **선언하지 않은 키는 조용히 사라진다.** 파싱은
    //   성공하고 타입 에러도 안 난다 — 그래서 CLI 는 rc 4 로 잔량을 알리는데 화면은
    //   「청산 접수」만 보여줬다. `toMatchObject` 는 부분 매칭이라 이 회귀를 못 잡는다.
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const order = {
      order_id: "abc123",
      side: "buy",
      qty: "0.029",
      trigger_price: "100",
      order_link_id: "link-1",
    };
    apiFetchMock.mockResolvedValueOnce({
      order_id: "order-1",
      state: "submitted",
      detail: "reduce-only market close accepted · 미체결 진입 주문 1건이 남아 있다",
      resting_entries: [order],
      resting_entries_unknown: false,
    });
    const { result } = renderHook(
      () => useClosePosition({ sessionId: "session-1", symbol: "BTCUSDT" }),
      { wrapper: makeWrapper(queryClient) },
    );

    const data = await result.current.mutateAsync();
    expect(data.resting_entries).toEqual([order]);
    expect(data.resting_entries_unknown).toBe(false);
  });

  it("잔량 미확인 플래그도 살아서 넘어온다", async () => {
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    apiFetchMock.mockResolvedValueOnce({
      order_id: "order-1",
      state: "submitted",
      detail: "reduce-only market close accepted · 미체결 진입 주문 확인 실패",
      resting_entries: [],
      resting_entries_unknown: true,
    });
    const { result } = renderHook(
      () => useClosePosition({ sessionId: "session-1", symbol: "BTCUSDT" }),
      { wrapper: makeWrapper(queryClient) },
    );

    await expect(result.current.mutateAsync()).resolves.toMatchObject({
      resting_entries_unknown: true,
    });
  });
});
