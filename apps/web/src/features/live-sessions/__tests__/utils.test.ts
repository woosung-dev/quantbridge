// Sprint 26 — Live Sessions utils unit tests (Vitest).
// Sprint 27 BL-140 — buildActivityTimeline test cases (codex G.2 P2 #4).

import { describe, expect, it } from "vitest";

import type { EquityCurvePoint, LiveSignalEvent } from "../schemas";
import {
  LIVE_SESSION_STATE_REFETCH_ACTIVE_MS,
  buildActivityTimeline,
  buildActivityTimelineWithEquity,
  computeLiveSessionStateRefetchInterval,
  formatDateTime,
} from "../utils";

// C 이식(W3-F) — 세션 시각 표기는 실행 환경 타임존과 무관하게 결정적이어야 한다(UTC).
describe("formatDateTime — 결정적 UTC 표기", () => {
  it("ISO datetime 을 YYYY-MM-DD HH:mm (UTC) 로 포맷한다", () => {
    expect(formatDateTime("2026-04-14T21:07:00Z")).toBe("2026-04-14 21:07");
  });

  it("타임존 오프셋 입력도 UTC 로 정규화한다 (환경 무관 결정성)", () => {
    // +09:00(KST) 자정 = 전날 15:00 UTC. Date.getTimezoneOffset 에 의존하지 않는다.
    expect(formatDateTime("2026-04-14T00:00:00+09:00")).toBe("2026-04-13 15:00");
  });

  it("null/undefined/파싱 불가 값은 무데이터 셀(—)로 떨어뜨린다", () => {
    expect(formatDateTime(null)).toBe("—");
    expect(formatDateTime(undefined)).toBe("—");
    expect(formatDateTime("not-a-date")).toBe("—");
  });
});

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

  it("active=false → 폴링 중단", () => {
    expect(computeLiveSessionStateRefetchInterval(false)).toBe(false);
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

describe("buildActivityTimelineWithEquity (two-pointer 경계)", () => {
  // Helper — equity_curve fixture.
  const eq = (iso: string, pnl: string): EquityCurvePoint => ({
    timestamp_ms: Date.parse(iso),
    cumulative_pnl: pnl,
  });

  it("이벤트가 첫 equity point 이전 → cumulative_pnl=0", () => {
    const result = buildActivityTimelineWithEquity(
      [
        ev({ bar_time: "2026-05-01T11:00:00Z", sequence_no: 0, action: "entry" }),
      ],
      [eq("2026-05-01T12:00:00Z", "10.5")],
    );
    expect(result).toHaveLength(1);
    expect(result[0]!.cumulative_pnl).toBe(0);
  });

  it("이벤트가 마지막 equity point 이후 → 마지막 값 carry-forward (경계 = 포함)", () => {
    const result = buildActivityTimelineWithEquity(
      [
        ev({ bar_time: "2026-05-01T12:00:00Z", sequence_no: 0, action: "entry" }),
        ev({ bar_time: "2026-05-01T14:00:00Z", sequence_no: 0, action: "close" }),
      ],
      [
        eq("2026-05-01T12:00:00Z", "10.5"), // 같은 timestamp (≤) → 포함
        eq("2026-05-01T13:00:00Z", "-3.25"),
      ],
    );
    expect(result.map((p) => p.cumulative_pnl)).toEqual([10.5, -3.25]);
  });

  it("BL-458 — carry-forward 되는 값의 출처도 같이 옮긴다", () => {
    // ★값만 옮기고 출처를 안 옮기면 차트 색이 값과 어긋난다 — 그 상태는 화면에서
    // 구분할 수 없고, "확정" 으로 잘못 칠해지면 없는 신뢰를 주장하는 셈이다.
    const result = buildActivityTimelineWithEquity(
      [
        ev({ bar_time: "2026-05-01T12:00:00Z", sequence_no: 0, action: "entry" }),
        ev({ bar_time: "2026-05-01T14:00:00Z", sequence_no: 0, action: "close" }),
      ],
      [
        { ...eq("2026-05-01T12:00:00Z", "-4"), source: "estimated" },
        { ...eq("2026-05-01T13:00:00Z", "-6"), source: "confirmed" },
      ],
    );

    expect(result.map((p) => p.cumulative_pnl)).toEqual([-4, -6]);
    expect(result.map((p) => p.cumulative_pnl_source)).toEqual([
      "estimated",
      "confirmed",
    ]);
  });

  it("BL-458 — source 가 없는 구 응답은 추정으로 폴백한다", () => {
    const result = buildActivityTimelineWithEquity(
      [ev({ bar_time: "2026-05-01T12:00:00Z", sequence_no: 0, action: "entry" })],
      [eq("2026-05-01T12:00:00Z", "-4")],
    );
    expect(result[0]!.cumulative_pnl_source).toBe("estimated");
  });
});
