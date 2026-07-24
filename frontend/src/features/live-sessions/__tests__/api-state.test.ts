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
