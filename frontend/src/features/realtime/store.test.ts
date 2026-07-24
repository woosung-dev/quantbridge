// 실시간 Zustand store의 진단 scalar와 ticker 캐시 계약을 검증한다.
import { afterEach, describe, expect, it } from "vitest";

import { useRealtimeStore } from "./store";

afterEach(() => {
  useRealtimeStore.getState().reset();
});

describe("useRealtimeStore", () => {
  it("연결 상태·마지막 이벤트 시각·재연결 횟수 scalar를 갱신한다", () => {
    const store = useRealtimeStore.getState();
    store.setConnection("authed", 2);
    store.recordEvent(1_720_000_000);

    expect(useRealtimeStore.getState()).toMatchObject({
      status: "authed",
      lastEventTs: 1_720_000_000,
      reconnectCount: 2,
    });
    expect(Object.keys(useRealtimeStore.getState())).not.toContain("events");
  });

  it("ticker를 심볼별로 적용하고 clearTickers가 캐시만 비운다", () => {
    const store = useRealtimeStore.getState();
    store.setConnection("authed", 1);
    store.applyTicker("BTCUSDT", { markPrice: "100", lastPrice: "99", ts: 1_720_000_000_000 });

    expect(useRealtimeStore.getState().tickers).toEqual({
      BTCUSDT: { markPrice: "100", lastPrice: "99", ts: 1_720_000_000_000 },
    });

    store.clearTickers();
    expect(useRealtimeStore.getState()).toMatchObject({
      status: "authed",
      reconnectCount: 1,
      tickers: {},
    });

    store.applyTicker("BTCUSDT", { markPrice: "101", lastPrice: null, ts: 2 });
    store.reset();
    expect(useRealtimeStore.getState().tickers).toEqual({});
  });

  it("다른 심볼 갱신 때 선택 ticker entry 참조를 유지한다", () => {
    const store = useRealtimeStore.getState();
    store.applyTicker("BTCUSDT", { markPrice: "100", lastPrice: null, ts: 1 });
    const btcTicker = useRealtimeStore.getState().tickers.BTCUSDT;

    store.applyTicker("ETHUSDT", { markPrice: "50", lastPrice: null, ts: 2 });

    expect(useRealtimeStore.getState().tickers.BTCUSDT).toBe(btcTicker);
  });
});
