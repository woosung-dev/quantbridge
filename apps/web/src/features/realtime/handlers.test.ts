// 실시간 이벤트가 서버 데이터를 쓰지 않고 정확한 Query Key만 무효화하는지 검증한다.
import { describe, expect, it, vi } from "vitest";

import type { QueryClient } from "@tanstack/react-query";

import { liveSessionKeys } from "@/features/live-sessions/query-keys";
import { tradingKeys } from "@/features/trading/query-keys";

import { handleRealtimeEvent } from "./handlers";
import type { RealtimeEnvelope } from "./schemas";
import { useRealtimeStore } from "./store";

const userId = "user-1";

function makeQueryClient() {
  return {
    invalidateQueries: vi.fn(),
  } as unknown as QueryClient;
}

describe("handleRealtimeEvent", () => {
  it.each([
    [
      {
        v: 1,
        type: "order_update",
        ts: 1,
        payload: { order_id: "order-1", state: "filled", symbol: "BTC", side: "buy", source: "ws" },
      },
      tradingKeys.ordersPrefix(userId),
    ],
    [
      {
        v: 1,
        type: "kill_switch",
        ts: 1,
        payload: { event_id: "kill-1", trigger_type: "daily_loss" },
      },
      tradingKeys.killSwitch(userId),
    ],
  ] as const)("%s 이벤트를 해당 키로 invalidate한다", (event, queryKey) => {
    const queryClient = makeQueryClient();
    handleRealtimeEvent(queryClient, userId, event as RealtimeEnvelope);

    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey });
  });

  it("session_state는 상세와 목록 키를 함께 invalidate한다", () => {
    const queryClient = makeQueryClient();
    handleRealtimeEvent(queryClient, userId, {
      v: 1,
      type: "session_state",
      ts: 1,
      payload: { session_id: "session-1" },
    });

    expect(queryClient.invalidateQueries).toHaveBeenNthCalledWith(1, {
      queryKey: liveSessionKeys.state(userId, "session-1"),
    });
    expect(queryClient.invalidateQueries).toHaveBeenNthCalledWith(2, {
      queryKey: liveSessionKeys.list(userId),
    });
  });

  it("ticker는 store만 갱신하고 query를 invalidate하지 않는다", () => {
    const queryClient = makeQueryClient();
    useRealtimeStore.getState().clearTickers();

    handleRealtimeEvent(queryClient, userId, {
      v: 1,
      type: "ticker",
      ts: 1_720_000_000_000,
      payload: { symbol: "BTCUSDT", mark_price: "100.25", last_price: "100.20" },
    });

    expect(useRealtimeStore.getState().tickers.BTCUSDT).toEqual({
      markPrice: "100.25",
      lastPrice: "100.20",
      ts: 1_720_000_000_000,
    });
    expect(queryClient.invalidateQueries).not.toHaveBeenCalled();
  });

  it("position_update는 포지션 prefix만 한 번 무효화하고 store를 쓰지 않는다", () => {
    const queryClient = makeQueryClient();
    const setQueryData = vi.fn();
    (queryClient as unknown as { setQueryData: typeof setQueryData }).setQueryData = setQueryData;

    handleRealtimeEvent(queryClient, userId, {
      v: 1,
      type: "position_update",
      ts: 1,
      payload: { symbol: "BTCUSDT", side: "long", size: "0.1" },
    });

    expect(queryClient.invalidateQueries).toHaveBeenCalledTimes(1);
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
      queryKey: liveSessionKeys.positionsPrefix(userId),
    });
    expect(setQueryData).not.toHaveBeenCalled();
  });
});
