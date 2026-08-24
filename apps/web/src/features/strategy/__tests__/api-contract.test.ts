// Strategy REST 래퍼의 현재 경로·요청·응답 스키마 계약을 고정한다.
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

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

const TOKEN = "strategy-contract-token";
const STRATEGY_ID = "00000000-0000-4000-a000-000000000001";

const SETTINGS = {
  schema_version: 1,
  leverage: 5,
  margin_mode: "isolated" as const,
  position_size_pct: 25,
  max_trigger_breach_pct: null,
  max_reversal_overshoot_ratio: null,
  fill_timing: "next_bar_open" as const,
};

const STRATEGY = {
  id: STRATEGY_ID,
  name: "Breakout",
  description: "BTC breakout strategy",
  pine_source: "strategy('Breakout')",
  pine_version: "v5",
  parse_status: "ok",
  parse_errors: null,
  timeframe: "1h",
  symbol: "BTCUSDT",
  tags: ["trend"],
  trading_sessions: ["asia"],
  settings: SETTINGS,
  is_archived: false,
  created_at: "2026-08-24T00:00:00Z",
  updated_at: "2026-08-24T01:00:00Z",
};

const STRATEGY_LIST_ITEM = {
  id: STRATEGY.id,
  name: STRATEGY.name,
  pine_version: STRATEGY.pine_version,
  parse_status: STRATEGY.parse_status,
  parse_errors: STRATEGY.parse_errors,
  timeframe: STRATEGY.timeframe,
  symbol: STRATEGY.symbol,
  tags: STRATEGY.tags,
  trading_sessions: STRATEGY.trading_sessions,
  settings: STRATEGY.settings,
  is_archived: STRATEGY.is_archived,
  created_at: STRATEGY.created_at,
  updated_at: STRATEGY.updated_at,
  backtest_count: 1,
  latest_backtest: null,
  param_count: 2,
  lifecycle: "validated",
};

const LIST_RESPONSE = {
  items: [STRATEGY_LIST_ITEM],
  total: 1,
  page: 3,
  limit: 25,
  total_pages: 3,
};

const CREATE_REQUEST = {
  name: STRATEGY.name,
  description: STRATEGY.description,
  pine_source: STRATEGY.pine_source,
  timeframe: STRATEGY.timeframe,
  symbol: STRATEGY.symbol,
  tags: STRATEGY.tags,
};

const CREATE_RESPONSE = {
  ...STRATEGY,
  webhook_secret: "new-webhook-secret",
};

const WEBHOOK_ROTATE_RESPONSE = {
  secret: "rotated-webhook-secret",
  webhook_url: `/api/v1/webhooks/${STRATEGY_ID}?token={HMAC}`,
};

const UPDATE_REQUEST = {
  name: "Updated breakout",
  trading_sessions: ["london"],
  is_archived: true,
};

const PARSE_PREVIEW_RESPONSE = {
  status: "ok",
  pine_version: "v5",
  warnings: ["degraded Pine result"],
  errors: [],
  entry_count: 1,
  exit_count: 1,
  functions_used: ["strategy.entry"],
  unsupported_builtins: [],
  unsupported_calls: [],
  dogfood_only_warning: "request.security result may differ from TradingView",
  is_runnable: true,
};

const PARSED_PARSE_PREVIEW_RESPONSE = {
  status: PARSE_PREVIEW_RESPONSE.status,
  pine_version: PARSE_PREVIEW_RESPONSE.pine_version,
  warnings: PARSE_PREVIEW_RESPONSE.warnings,
  errors: PARSE_PREVIEW_RESPONSE.errors,
  entry_count: PARSE_PREVIEW_RESPONSE.entry_count,
  exit_count: PARSE_PREVIEW_RESPONSE.exit_count,
  functions_used: PARSE_PREVIEW_RESPONSE.functions_used,
  unsupported_builtins: PARSE_PREVIEW_RESPONSE.unsupported_builtins,
  unsupported_calls: PARSE_PREVIEW_RESPONSE.unsupported_calls,
  is_runnable: PARSE_PREVIEW_RESPONSE.is_runnable,
};

afterEach(() => {
  apiFetchMock.mockReset();
});

describe("strategy API contract", () => {
  it("현재 계약: 목록 조회는 필터·정렬 query와 GET 인증을 전달하고 목록 응답을 파싱한다", async () => {
    const query = {
      limit: 25,
      offset: 50,
      parse_status: "ok" as const,
      is_archived: true,
      order_by: "name" as const,
      order: "asc" as const,
    };
    apiFetchMock.mockResolvedValueOnce(LIST_RESPONSE);

    await expect(listStrategies(query, TOKEN)).resolves.toEqual(LIST_RESPONSE);

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/strategies", {
      method: "GET",
      token: TOKEN,
      params: query,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("현재 계약: 상세 조회는 strategy 식별자를 GET 경로에 넣고 응답을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce(STRATEGY);

    await expect(getStrategy(STRATEGY_ID, TOKEN)).resolves.toEqual(STRATEGY);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/strategies/${STRATEGY_ID}`, {
      method: "GET",
      token: TOKEN,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("현재 계약: 전략 생성은 검증된 본문을 POST하고 webhook 응답을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce(CREATE_RESPONSE);

    await expect(createStrategy(CREATE_REQUEST, TOKEN)).resolves.toEqual(CREATE_RESPONSE);

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/strategies", {
      method: "POST",
      token: TOKEN,
      body: CREATE_REQUEST,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("현재 계약: webhook secret 회전은 strategy 식별자 POST 경로와 응답을 보존한다", async () => {
    apiFetchMock.mockResolvedValueOnce(WEBHOOK_ROTATE_RESPONSE);

    await expect(rotateWebhookSecret(STRATEGY_ID, TOKEN)).resolves.toEqual(WEBHOOK_ROTATE_RESPONSE);

    expect(apiFetchMock).toHaveBeenCalledWith(
      `/api/v1/strategies/${STRATEGY_ID}/rotate-webhook-secret`,
      { method: "POST", token: TOKEN },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("현재 계약: 전략 수정은 부분 본문을 식별자 PUT 경로로 보내고 응답을 파싱한다", async () => {
    const updatedStrategy = { ...STRATEGY, ...UPDATE_REQUEST };
    apiFetchMock.mockResolvedValueOnce(updatedStrategy);

    await expect(updateStrategy(STRATEGY_ID, UPDATE_REQUEST, TOKEN)).resolves.toEqual(
      updatedStrategy,
    );

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/strategies/${STRATEGY_ID}`, {
      method: "PUT",
      token: TOKEN,
      body: UPDATE_REQUEST,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("현재 계약: 거래 설정 수정은 설정 본문을 settings PUT 경로로 보내고 응답을 파싱한다", async () => {
    const updatedStrategy = { ...STRATEGY, settings: SETTINGS };
    apiFetchMock.mockResolvedValueOnce(updatedStrategy);

    await expect(updateStrategySettings(STRATEGY_ID, SETTINGS, TOKEN)).resolves.toEqual(
      updatedStrategy,
    );

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/strategies/${STRATEGY_ID}/settings`, {
      method: "PUT",
      token: TOKEN,
      body: SETTINGS,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("현재 계약: 전략 삭제는 식별자 DELETE와 인증만 전달하고 빈 응답을 반환한다", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);

    await expect(deleteStrategy(STRATEGY_ID, TOKEN)).resolves.toBeUndefined();

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/strategies/${STRATEGY_ID}`, {
      method: "DELETE",
      token: TOKEN,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("현재 계약: parse preview는 Pine 본문을 POST하고 FE 스키마가 보존하는 응답만 반환한다", async () => {
    apiFetchMock.mockResolvedValueOnce(PARSE_PREVIEW_RESPONSE);

    await expect(parseStrategy(STRATEGY.pine_source, TOKEN)).resolves.toEqual(
      PARSED_PARSE_PREVIEW_RESPONSE,
    );

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/strategies/parse", {
      method: "POST",
      token: TOKEN,
      body: { pine_source: STRATEGY.pine_source },
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });
});
