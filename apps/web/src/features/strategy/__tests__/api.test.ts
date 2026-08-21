// Strategy API가 요청 기본값을 정규화하고 응답 계약을 검증하는지 확인한다.
// 네트워크 구현은 apiFetch 하나에 있으므로 이 경계에서만 mock 한다.

import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiFetchMock };
});

import { ApiError } from "@/lib/api-client";
import type { CreateStrategyRequest, UpdateStrategySettingsRequest } from "../schemas";
import {
  createStrategy,
  deleteStrategy,
  getStrategy,
  listStrategies,
  parseStrategy,
  rotateWebhookSecret,
  updateStrategy,
  updateStrategySettings,
} from "../api";

const TOKEN = "access-token";
const STRATEGY_ID = "11111111-1111-4111-8111-111111111111";

function strategyResponse() {
  return {
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
  };
}

afterEach(() => {
  apiFetchMock.mockReset();
  vi.unstubAllGlobals();
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
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("createStrategy는 검증된 본문을 create endpoint로 보낸다", async () => {
    apiFetchMock.mockResolvedValueOnce(strategyResponse());
    const body: CreateStrategyRequest = {
      name: "Breakout",
      pine_source: "strategy('Breakout')",
      timeframe: "1h",
      symbol: "BTCUSDT",
      tags: [],
    };

    await expect(createStrategy(body, TOKEN)).resolves.toMatchObject({
      id: STRATEGY_ID,
      name: "Breakout",
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/strategies", {
      method: "POST",
      token: TOKEN,
      body,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("getStrategy는 전략 상세 endpoint에서 검증된 응답을 반환한다", async () => {
    const response = strategyResponse();
    apiFetchMock.mockResolvedValueOnce(response);

    await expect(getStrategy(STRATEGY_ID, TOKEN)).resolves.toEqual(response);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/strategies/${STRATEGY_ID}`, {
      method: "GET",
      token: TOKEN,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("rotateWebhookSecret는 전략별 secret rotate endpoint의 결과를 반환한다", async () => {
    const response = {
      secret: "new-webhook-secret",
      webhook_url: `https://api.quantbridge.example/webhooks/${STRATEGY_ID}`,
    };
    apiFetchMock.mockResolvedValueOnce(response);

    await expect(rotateWebhookSecret(STRATEGY_ID, TOKEN)).resolves.toEqual(response);

    expect(apiFetchMock).toHaveBeenCalledWith(
      `/api/v1/strategies/${STRATEGY_ID}/rotate-webhook-secret`,
      {
        method: "POST",
        token: TOKEN,
      },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("updateStrategy는 검증한 부분 수정 본문을 전략 endpoint로 보낸다", async () => {
    const body = { name: "Updated breakout", tags: ["trend"] };
    const response = { ...strategyResponse(), ...body };
    apiFetchMock.mockResolvedValueOnce(response);

    await expect(updateStrategy(STRATEGY_ID, body, TOKEN)).resolves.toEqual(response);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/strategies/${STRATEGY_ID}`, {
      method: "PUT",
      token: TOKEN,
      body,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("updateStrategySettings는 검증된 설정 본문을 settings endpoint로 보낸다", async () => {
    const body: UpdateStrategySettingsRequest = {
      schema_version: 1,
      leverage: 3,
      margin_mode: "isolated",
      position_size_pct: 25,
      max_trigger_breach_pct: null,
      max_reversal_overshoot_ratio: null,
      fill_timing: "next_bar_open",
    };
    const response = {
      ...strategyResponse(),
      settings: body,
    };
    apiFetchMock.mockResolvedValueOnce(response);

    await expect(updateStrategySettings(STRATEGY_ID, body, TOKEN)).resolves.toEqual(response);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/strategies/${STRATEGY_ID}/settings`, {
      method: "PUT",
      token: TOKEN,
      body,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("deleteStrategy는 전략별 delete endpoint를 한 번 호출하고 undefined를 반환한다", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);

    await expect(deleteStrategy(STRATEGY_ID, TOKEN)).resolves.toBeUndefined();

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/strategies/${STRATEGY_ID}`, {
      method: "DELETE",
      token: TOKEN,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("parseStrategy는 Pine 원본을 parse endpoint로 보내고 기본 결과를 보완한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ status: "ok", pine_version: "v5" });

    await expect(parseStrategy("strategy('Parse me')", TOKEN)).resolves.toEqual({
      status: "ok",
      pine_version: "v5",
      warnings: [],
      errors: [],
      entry_count: 0,
      exit_count: 0,
      functions_used: [],
      unsupported_builtins: [],
      unsupported_calls: [],
      is_runnable: true,
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/strategies/parse", {
      method: "POST",
      token: TOKEN,
      body: { pine_source: "strategy('Parse me')" },
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("getStrategy는 ApiError의 status와 code를 감싸지 않고 그대로 전파한다", async () => {
    const error = new ApiError(409, "strategy_in_use", "strategy is referenced");
    apiFetchMock.mockRejectedValueOnce(error);

    await expect(getStrategy(STRATEGY_ID, TOKEN)).rejects.toBe(error);

    expect(error).toMatchObject({ status: 409, code: "strategy_in_use" });
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/strategies/${STRATEGY_ID}`, {
      method: "GET",
      token: TOKEN,
    });
  });

  it("getStrategy는 계약을 어긴 응답을 조용히 반환하지 않는다", async () => {
    apiFetchMock.mockResolvedValueOnce({ id: STRATEGY_ID });

    await expect(getStrategy(STRATEGY_ID, TOKEN)).rejects.toThrow();

    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("listStrategies는 선택 parse_status가 없으면 전송 URL에 undefined를 넣지 않는다", async () => {
    const { apiFetch: actualApiFetch } =
      await vi.importActual<typeof import("@/lib/api-client")>("@/lib/api-client");
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [], total: 0, page: 1, limit: 1, total_pages: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    apiFetchMock.mockImplementation(actualApiFetch);

    await expect(
      listStrategies({ limit: 1, offset: 0, parse_status: undefined }, TOKEN),
    ).resolves.toMatchObject({ items: [], total: 0, page: 1 });

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).not.toContain("parse_status");
    expect(url).not.toContain("undefined");
  });

  it.each([
    [{ limit: 0, offset: 0 }, "0 limit"],
    [{ limit: 1, offset: -1 }, "negative offset"],
  ])("listStrategies는 %s에서 요청 전에 경계값을 거절한다", async (query) => {
    await expect(listStrategies(query, TOKEN)).rejects.toThrow();

    expect(apiFetchMock).not.toHaveBeenCalled();
  });
});
