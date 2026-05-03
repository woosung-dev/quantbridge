// Sprint 26 — Live Sessions utils unit tests (Vitest).

import { describe, expect, it } from "vitest";

import {
  LIVE_SESSION_STATE_REFETCH_ACTIVE_MS,
  LIVE_SESSION_STATE_REFETCH_IDLE_MS,
  buildPnlSeries,
  computeLiveSessionStateRefetchInterval,
} from "../utils";

describe("computeLiveSessionStateRefetchInterval", () => {
  it("active=true → 5s", () => {
    expect(computeLiveSessionStateRefetchInterval(true)).toBe(
      LIVE_SESSION_STATE_REFETCH_ACTIVE_MS,
    );
  });

  it("active=false → 30s", () => {
    expect(computeLiveSessionStateRefetchInterval(false)).toBe(
      LIVE_SESSION_STATE_REFETCH_IDLE_MS,
    );
  });
});

describe("buildPnlSeries", () => {
  it("빈 배열 → 빈 결과", () => {
    expect(buildPnlSeries([])).toEqual([]);
  });

  it("단일 trade → cumulative_pnl == pnl", () => {
    const series = buildPnlSeries([
      { exit_time: "2026-05-01T12:00:00Z", pnl: 10.5 },
    ]);
    expect(series).toEqual([
      { timestamp: "2026-05-01T12:00:00Z", cumulative_pnl: 10.5 },
    ]);
  });

  it("3건 누적 — string Decimal 도 parse", () => {
    const series = buildPnlSeries([
      { exit_time: "2026-05-01T12:00:00Z", pnl: "1.0" },
      { exit_time: "2026-05-01T13:00:00Z", pnl: "2.5" },
      { exit_time: "2026-05-01T14:00:00Z", pnl: -0.5 },
    ]);
    expect(series.map((p) => p.cumulative_pnl)).toEqual([1.0, 3.5, 3.0]);
  });

  it("malformed pnl string 은 0 처리", () => {
    const series = buildPnlSeries([
      { exit_time: "2026-05-01T12:00:00Z", pnl: "not-a-number" },
      { exit_time: "2026-05-01T13:00:00Z", pnl: 5 },
    ]);
    expect(series.map((p) => p.cumulative_pnl)).toEqual([0, 5]);
  });
});
