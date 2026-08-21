// Live sessions REST 래퍼의 경로·메서드·응답 스키마 계약을 고정한다.
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import { closePosition, listLiveSessions } from "../api";

const SESSION = {
  id: "00000000-0000-4000-a000-000000000001",
  user_id: "00000000-0000-4000-a000-000000000002",
  strategy_id: "00000000-0000-4000-a000-000000000003",
  exchange_account_id: "00000000-0000-4000-a000-000000000004",
  symbol: "BTC/USDT:USDT",
  interval: "1h",
  is_active: true,
  last_evaluated_bar_time: null,
  created_at: "2026-08-22T00:00:00Z",
  deactivated_at: null,
};

afterEach(() => {
  apiFetchMock.mockReset();
});

describe("live sessions API contract", () => {
  it("비활성 포함 목록은 query 경로와 GET 인증을 전달하고 목록 응답을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [SESSION], total: 1 });

    await expect(listLiveSessions("jwt", true)).resolves.toEqual({ items: [SESSION], total: 1 });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/live-sessions?include_inactive=true", {
      method: "GET",
      token: "jwt",
    });
  });

  it("포지션 청산은 세션 경로의 POST로 발주하고 구 응답 기본값을 보완한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      order_id: "close-001",
      state: "submitted",
      detail: null,
    });

    await expect(closePosition(SESSION.id, "jwt")).resolves.toEqual({
      order_id: "close-001",
      state: "submitted",
      detail: null,
      resting_entries: [],
      resting_entries_unknown: false,
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      `/api/v1/live-sessions/${SESSION.id}/positions/close`,
      { method: "POST", token: "jwt" },
    );
  });
});
