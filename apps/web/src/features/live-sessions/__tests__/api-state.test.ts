// 라이브 세션 state API의 pending 및 이전 응답 호환을 검증한다.
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({
  apiFetch: apiFetchMock,
  ApiError: class ApiError extends Error {},
}));

import { getLiveSessionState } from "../api";

const sessionId = "00000000-0000-4000-a000-000000000001";
const stateResponse = {
  session_id: sessionId,
  schema_version: 1,
  last_strategy_state_report: {},
  total_closed_trades: 0,
  total_realized_pnl: "0",
  equity_curve: [],
  updated_at: "2026-07-24T00:00:00Z",
};

afterEach(() => {
  apiFetchMock.mockReset();
});

describe("getLiveSessionState", () => {
  it("evaluated=false pending 응답을 null로 변환한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      ...stateResponse,
      evaluated: false,
      schema_version: 0,
      updated_at: null,
    });

    await expect(getLiveSessionState(sessionId, "token")).resolves.toBeNull();
  });

  it("evaluated 키가 없는 이전 응답은 true 기본값으로 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce(stateResponse);

    await expect(getLiveSessionState(sessionId, "token")).resolves.toMatchObject({
      ...stateResponse,
      evaluated: true,
    });
  });
});

describe("getLiveSessionState — BL-458 출처 필드", () => {
  it("커브 포인트의 source 와 소계 4필드를 벗기지 않고 통과시킨다", async () => {
    // ★zod 는 기본적으로 미지 키를 조용히 벗긴다. 이 스키마 갱신이 없으면 BE 가
    // 필드를 실어 보내도 FE 에서 사라지고, 기능 전체가 green 으로 출하되면서
    // 화면에는 아무것도 안 나온다. 그 실패 모드를 여기서 못 지나가게 막는다.
    apiFetchMock.mockResolvedValueOnce({
      ...stateResponse,
      confirmed_realized_pnl: "-2",
      estimated_realized_pnl: "-4",
      confirmed_closed_trades: 1,
      estimated_closed_trades: 1,
      equity_curve: [
        { timestamp_ms: 1000, cumulative_pnl: "-4", source: "estimated" },
        { timestamp_ms: 2000, cumulative_pnl: "-6", source: "confirmed" },
      ],
    });

    const state = await getLiveSessionState(sessionId, "token");

    expect(state).not.toBeNull();
    expect(state!.confirmed_realized_pnl).toBe("-2");
    expect(state!.estimated_realized_pnl).toBe("-4");
    expect(state!.confirmed_closed_trades).toBe(1);
    expect(state!.estimated_closed_trades).toBe(1);
    expect(state!.equity_curve.map((p) => p.source)).toEqual(["estimated", "confirmed"]);
  });

  it("source 가 없는 구 응답은 추정으로 폴백한다", async () => {
    // 증거 부재가 "거래소 확정" 이 되면 안 된다 — 폴백 방향이 계약이다.
    const { curvePointSource } = await import("../schemas");
    apiFetchMock.mockResolvedValueOnce({
      ...stateResponse,
      equity_curve: [{ timestamp_ms: 1000, cumulative_pnl: "-4" }],
    });

    const state = await getLiveSessionState(sessionId, "token");

    expect(state!.equity_curve[0]!.source).toBeUndefined();
    expect(curvePointSource(state!.equity_curve[0]!)).toBe("estimated");
    expect(state!.confirmed_realized_pnl).toBeUndefined();
  });
});
