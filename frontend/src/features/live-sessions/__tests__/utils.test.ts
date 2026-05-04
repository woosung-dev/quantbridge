// Sprint 26 — Live Sessions utils unit tests (Vitest).
// Sprint 27 BL-140 — buildActivityTimeline test cases (codex G.2 P2 #4).

import { describe, expect, it } from "vitest";

import type { LiveSignalEvent } from "../schemas";
import {
  LIVE_SESSION_STATE_REFETCH_ACTIVE_MS,
  LIVE_SESSION_STATE_REFETCH_IDLE_MS,
  buildActivityTimeline,
  buildPnlSeries,
  computeLiveSessionStateRefetchInterval,
} from "../utils";

// Helper — fixture builder. status는 최소 valid 값 ("dispatched").
function ev(
  partial: Partial<LiveSignalEvent> &
    Pick<LiveSignalEvent, "bar_time" | "sequence_no" | "action">,
): LiveSignalEvent {
  return {
    id: "00000000-0000-0000-0000-000000000000",
    session_id: "00000000-0000-0000-0000-000000000001",
    direction: "long",
    trade_id: "T",
    qty: "1",
    comment: "",
    status: "dispatched",
    order_id: null,
    error_message: null,
    retry_count: 0,
    created_at: partial.bar_time,
    dispatched_at: partial.bar_time,
    ...partial,
  };
}

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

describe("buildActivityTimeline (Sprint 27 BL-140)", () => {
  it("빈 배열 → 빈 결과", () => {
    expect(buildActivityTimeline([])).toEqual([]);
  });

  it("단일 entry → cumulative entries=1, closes=0", () => {
    const result = buildActivityTimeline([
      ev({ bar_time: "2026-05-01T12:00:00Z", sequence_no: 0, action: "entry" }),
    ]);
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      entries_in_window: 1,
      closes_in_window: 0,
    });
  });

  it("entry+close 페어 → cumulative entries=1, closes=1", () => {
    const result = buildActivityTimeline([
      ev({ bar_time: "2026-05-01T12:00:00Z", sequence_no: 0, action: "entry" }),
      ev({ bar_time: "2026-05-01T12:01:00Z", sequence_no: 0, action: "close" }),
    ]);
    expect(result.map((p) => p.entries_in_window)).toEqual([1, 1]);
    expect(result.map((p) => p.closes_in_window)).toEqual([0, 1]);
  });

  it("BE created_at desc 응답 (역순) → client-side bar_time asc 정렬 (codex P1 #4)", () => {
    // BE 가 created_at.desc() 로 응답 → 시간 역순 입력
    const result = buildActivityTimeline([
      ev({ bar_time: "2026-05-01T12:02:00Z", sequence_no: 0, action: "close" }),
      ev({ bar_time: "2026-05-01T12:01:00Z", sequence_no: 0, action: "entry" }),
      ev({ bar_time: "2026-05-01T12:00:00Z", sequence_no: 0, action: "entry" }),
    ]);
    // 정렬 후 chronological → entry, entry, close 순서
    expect(result.map((p) => p.entries_in_window)).toEqual([1, 2, 2]);
    expect(result.map((p) => p.closes_in_window)).toEqual([0, 0, 1]);
  });

  it("같은 bar_time 의 sequence_no asc 보조 정렬", () => {
    // 동일 bar_time 에 entry sequence_no=0, close sequence_no=1
    const result = buildActivityTimeline([
      ev({ bar_time: "2026-05-01T12:00:00Z", sequence_no: 1, action: "close" }),
      ev({ bar_time: "2026-05-01T12:00:00Z", sequence_no: 0, action: "entry" }),
    ]);
    expect(result.map((p) => p.entries_in_window)).toEqual([1, 1]);
    expect(result.map((p) => p.closes_in_window)).toEqual([0, 1]);
  });

  it("non-entry/non-close action (e.g. NaN protection) → counts 무변동", () => {
    // schemas.action 은 z.string() 이므로 unknown action 도 가능
    const result = buildActivityTimeline([
      ev({ bar_time: "2026-05-01T12:00:00Z", sequence_no: 0, action: "entry" }),
      ev({ bar_time: "2026-05-01T12:01:00Z", sequence_no: 0, action: "noop" as string }),
      ev({ bar_time: "2026-05-01T12:02:00Z", sequence_no: 0, action: "close" }),
    ]);
    expect(result.map((p) => p.entries_in_window)).toEqual([1, 1, 1]);
    expect(result.map((p) => p.closes_in_window)).toEqual([0, 0, 1]);
  });

  it("immutable — 입력 events array 변경 안 함", () => {
    const original = [
      ev({ bar_time: "2026-05-01T12:01:00Z", sequence_no: 0, action: "entry" }),
      ev({ bar_time: "2026-05-01T12:00:00Z", sequence_no: 0, action: "entry" }),
    ];
    const before = original.map((e) => e.bar_time);
    buildActivityTimeline(original);
    const after = original.map((e) => e.bar_time);
    expect(after).toEqual(before);
  });
});
