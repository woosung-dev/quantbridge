// query-poll 팩토리 진리표 — LESSON-004 가드(error→false) + terminal 중단 계약 고정.

import { describe, expect, it } from "vitest";
import type { Query } from "@tanstack/react-query";

import { makeRefetchInterval, makeStatusPoll } from "../query-poll";

interface FakeStatusData {
  status: string;
}

function fakeQuery<TData>(opts: {
  status?: "pending" | "error" | "success";
  data?: TData;
}): Query<TData, Error> {
  return {
    state: {
      status: opts.status ?? "success",
      data: opts.data,
    },
  } as unknown as Query<TData, Error>;
}

describe("makeRefetchInterval", () => {
  const fn = makeRefetchInterval<FakeStatusData>(() => 30_000);

  it("error 상태면 compute 무관 false (LESSON-004 가드)", () => {
    expect(fn(fakeQuery<FakeStatusData>({ status: "error" }))).toBe(false);
  });

  it("정상 상태면 compute 결과 반환", () => {
    expect(fn(fakeQuery({ data: { status: "running" } }))).toBe(30_000);
  });

  it("compute 에 현재 data 가 전달된다", () => {
    const dataAware = makeRefetchInterval<FakeStatusData>((data) =>
      data?.status === "idle" ? false : 1_000,
    );
    expect(dataAware(fakeQuery({ data: { status: "idle" } }))).toBe(false);
    expect(dataAware(fakeQuery({ data: { status: "busy" } }))).toBe(1_000);
    expect(dataAware(fakeQuery<FakeStatusData>({ data: undefined }))).toBe(1_000);
  });
});

describe("makeStatusPoll", () => {
  const TERMINAL = new Set(["completed", "failed", "cancelled"]);
  const fn = makeStatusPoll<FakeStatusData>((d) => d.status, TERMINAL, 2_000);

  it("error 상태 → false", () => {
    expect(fn(fakeQuery<FakeStatusData>({ status: "error" }))).toBe(false);
  });

  it("data 미도착 → interval 유지 (첫 응답 전 폴링 지속)", () => {
    expect(fn(fakeQuery<FakeStatusData>({ data: undefined }))).toBe(2_000);
  });

  it.each(["completed", "failed", "cancelled"])(
    "terminal status %s → false",
    (status) => {
      expect(fn(fakeQuery({ data: { status } }))).toBe(false);
    },
  );

  it.each(["queued", "running", "cancelling"])(
    "active status %s → interval",
    (status) => {
      expect(fn(fakeQuery({ data: { status } }))).toBe(2_000);
    },
  );
});
