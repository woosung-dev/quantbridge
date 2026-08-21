// Strategy API가 요청 기본값을 정규화하고 응답 계약을 검증하는지 확인한다.
// 네트워크 구현은 apiFetch 하나에 있으므로 이 경계에서만 mock 한다.

import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import { createStrategy, listStrategies } from "../api";

const TOKEN = "access-token";
const STRATEGY_ID = "11111111-1111-4111-8111-111111111111";

afterEach(() => {
  apiFetchMock.mockReset();
});

describe("strategy api", () => {
  it("listStrategies는 기본 query를 정규화해 목록 endpoint로 보낸다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      limit: 20,
      total_pages: 0,
    });

    await expect(listStrategies({ limit: 20, offset: 0 }, TOKEN)).resolves.toMatchObject({
      items: [],
      total: 0,
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/strategies", {
      method: "GET",
      token: TOKEN,
      params: {
        limit: 20,
        offset: 0,
        parse_status: undefined,
        is_archived: false,
        order_by: "updated_at",
        order: "desc",
      },
    });
  });

  it("createStrategy는 정규화한 본문을 create endpoint로 보낸다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      id: STRATEGY_ID,
      name: "Breakout",
      description: null,
      pine_source: "strategy('Breakout')",
      pine_version: "v5",
      parse_status: "ok",
      parse_errors: null,
      timeframe: "1h",
      symbol: "BTCUSDT",
      tags: [],
      trading_sessions: [],
      is_archived: false,
      created_at: "2026-08-22T00:00:00Z",
      updated_at: "2026-08-22T00:00:00Z",
    });

    await expect(
      createStrategy(
        {
          name: "Breakout",
          pine_source: "strategy('Breakout')",
          timeframe: "1h",
          symbol: "BTCUSDT",
        },
        TOKEN,
      ),
    ).resolves.toMatchObject({ id: STRATEGY_ID, name: "Breakout" });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/strategies", {
      method: "POST",
      token: TOKEN,
      body: {
        name: "Breakout",
        pine_source: "strategy('Breakout')",
        timeframe: "1h",
        symbol: "BTCUSDT",
        tags: [],
      },
    });
  });
});
