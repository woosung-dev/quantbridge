// 실시간 Zustand store가 진단 scalar만 보관하는 계약을 검증한다.
import { afterEach, describe, expect, it } from "vitest";

import { useRealtimeStore } from "./store";

afterEach(() => {
  useRealtimeStore.getState().reset();
});

describe("useRealtimeStore", () => {
  it("연결 상태·마지막 이벤트 시각·재연결 횟수 scalar만 갱신한다", () => {
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
});
