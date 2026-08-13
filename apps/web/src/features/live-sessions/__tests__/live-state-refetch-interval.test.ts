// liveStateRefetchInterval 회귀 테스트 — aggregate 팬아웃의 error 가드 누락(LESSON-004 위반) 수정 고정.

import { describe, expect, it } from "vitest";
import type { Query } from "@tanstack/react-query";

import { liveSessionEventsRefetchInterval, liveStateRefetchInterval } from "../hooks";
import type { LiveSignalEvent, LiveSignalState } from "../schemas";
import { LIVE_SESSION_STATE_REFETCH_ACTIVE_MS } from "../utils";

function fakeQuery(
  status: "success" | "error",
): Query<LiveSignalState | null, Error> {
  return { state: { status, data: undefined } } as unknown as Query<
    LiveSignalState | null,
    Error
  >;
}

function fakeEventsQuery(status: "success" | "error"): Query<{ items: LiveSignalEvent[] }, Error> {
  return { state: { status, data: undefined } } as unknown as Query<
    { items: LiveSignalEvent[] },
    Error
  >;
}

describe("liveStateRefetchInterval", () => {
  it("active 세션 — 정상 상태면 active 간격", () => {
    expect(liveStateRefetchInterval(true)(fakeQuery("success"))).toBe(
      LIVE_SESSION_STATE_REFETCH_ACTIVE_MS,
    );
  });

  it("종료 세션은 정상 상태여도 폴링하지 않는다", () => {
    expect(liveStateRefetchInterval(false)(fakeQuery("success"))).toBe(false);
  });

  it("error 상태 — active/idle 무관 폴링 중단 (LESSON-004)", () => {
    expect(liveStateRefetchInterval(true)(fakeQuery("error"))).toBe(false);
    expect(liveStateRefetchInterval(false)(fakeQuery("error"))).toBe(false);
  });

  it("종료 세션의 이벤트도 폴링하지 않는다", () => {
    expect(
      liveSessionEventsRefetchInterval(false)(fakeEventsQuery("success")),
    ).toBe(false);
  });
});
