// Live sessions REST 래퍼의 경로·메서드·응답 스키마 계약을 고정한다.
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import {
  closePosition,
  deactivateLiveSession,
  getAccountPositions,
  getLiveSessionOutcomeParity,
  getLiveSessionPositions,
  getLiveSessionState,
  listLiveSessionEvents,
  listLiveSessions,
  registerLiveSession,
} from "../api";

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

const LIVE_STATE = {
  session_id: SESSION.id,
  evaluated: true,
  schema_version: 1,
  last_strategy_state_report: { open_trades: [] },
  total_closed_trades: 0,
  total_realized_pnl: "0",
  equity_curve: [],
  updated_at: "2026-08-22T00:00:00Z",
};

const EXCHANGE_POSITION = {
  side: "Buy",
  size: "0.01",
  entry_price: "100000",
  mark_price: "100100",
  unrealized_pnl: "1",
  take_profit_prices: [],
  stop_loss_prices: [],
  has_trailing_stop: false,
  liquidation_price: "80000",
  leverage: "5",
};

function makeOutcomeParityScope() {
  return {
    matched_count: 1,
    expected_gross: "10",
    actual_net: "9",
    decomposable_count: 1,
    decomposable_expected_gross: "10",
    execution_gap: "-1",
    cost: "1",
    decomposable_actual_net: "9",
    actual_gross: "10",
    round_trip_notional: "1000",
    effective_cost_pct_per_leg: "0.05",
    effective_cost_pct_round_trip: "0.1",
    edge_pct_round_trip: "1",
    cost_to_edge_ratio: "0.1",
    undecomposed_count: 0,
    undecomposed_net: "0",
    expected_only_count: 0,
    expected_only_gross: "0",
    expected_only_pending_count: 0,
    expected_only_failed_count: 0,
    expected_only_dispatched_count: 0,
    actual_only_count: 0,
    actual_only_net: "0",
    ledger_only_count: 0,
    ledger_only_net: "0",
    inferred_attribution_count: 0,
    match_coverage_pct: "100",
    decomposition_coverage_pct: "100",
    sample_n: 1,
    sample_mean_net: "9",
    sample_sd_net: null,
    sample_required_n: 30,
    sample_sufficient: false,
    ratio_sample_n: 1,
    ratio_sample_required_n: 30,
    ratio_sample_sufficient: false,
  };
}

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
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("세션 등록은 요청 body와 인증을 POST하고 응답을 파싱한다", async () => {
    const request = {
      strategy_id: SESSION.strategy_id,
      exchange_account_id: SESSION.exchange_account_id,
      symbol: SESSION.symbol,
      interval: "1h" as const,
    };
    apiFetchMock.mockResolvedValueOnce(SESSION);

    await expect(registerLiveSession(request, "jwt")).resolves.toEqual(SESSION);

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/live-sessions", {
      method: "POST",
      token: "jwt",
      body: request,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("세션 비활성화는 식별자 DELETE와 인증만 전달한다", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);

    await expect(deactivateLiveSession(SESSION.id, "jwt")).resolves.toBeUndefined();

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION.id}`, {
      method: "DELETE",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("평가된 세션 상태는 state GET 결과를 그대로 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce(LIVE_STATE);

    await expect(getLiveSessionState(SESSION.id, "jwt")).resolves.toEqual(LIVE_STATE);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION.id}/state`, {
      method: "GET",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("세션 이벤트는 events GET 응답의 목록을 파싱한다", async () => {
    const event = {
      id: "00000000-0000-4000-a000-000000000005",
      session_id: SESSION.id,
      bar_time: "2026-08-22T00:00:00Z",
      sequence_no: 1,
      action: "entry",
      direction: "long",
      trade_id: "trade-001",
      qty: "0.01",
      comment: "entry signal",
      status: "dispatched",
      order_id: null,
      error_message: null,
      retry_count: 0,
      created_at: "2026-08-22T00:00:01Z",
      dispatched_at: "2026-08-22T00:00:02Z",
    };
    apiFetchMock.mockResolvedValueOnce({ items: [event] });

    await expect(listLiveSessionEvents(SESSION.id, "jwt")).resolves.toEqual({ items: [event] });

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION.id}/events`, {
      method: "GET",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("세션 포지션은 reconciliation GET 응답을 파싱한다", async () => {
    const positions = {
      session_id: SESSION.id,
      symbol: SESSION.symbol,
      market_type: "futures",
      supported: true,
      reason: null,
      fetched_at: "2026-08-22T00:00:00Z",
      positions: [EXCHANGE_POSITION],
      local_open_trades_snapshot: [],
      diff: { verdict: "match", local_source: "strategy_state_report" },
    };
    apiFetchMock.mockResolvedValueOnce(positions);

    await expect(getLiveSessionPositions(SESSION.id, "jwt")).resolves.toEqual(positions);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION.id}/positions`, {
      method: "GET",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("성과 패리티는 outcome-parity GET 응답을 파싱한다", async () => {
    const parity = {
      session_id: SESSION.id,
      session: makeOutcomeParityScope(),
      strategy: makeOutcomeParityScope(),
      unattributed_count: 0,
      inferred_attribution_count: 0,
      ledger_supported: true,
      strategy_session_count: 1,
      assumption: {
        source: "house_default",
        taker_fee_pct: "0.05",
        slippage_pct: "0.05",
        maker_fee_pct: "0.02",
        implied_round_trip_pct: "0.2",
      },
    };
    apiFetchMock.mockResolvedValueOnce(parity);

    await expect(getLiveSessionOutcomeParity(SESSION.id, "jwt")).resolves.toEqual(parity);

    expect(apiFetchMock).toHaveBeenCalledWith(
      `/api/v1/live-sessions/${SESSION.id}/outcome-parity`,
      { method: "GET", token: "jwt" },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("계정 포지션은 exchange-account GET 응답을 파싱한다", async () => {
    const positions = {
      account_id: SESSION.exchange_account_id,
      supported: true,
      reason: null,
      fetched_at: "2026-08-22T00:00:00Z",
      rows: [
        {
          symbol: SESSION.symbol,
          position: EXCHANGE_POSITION,
          closable_session_id: SESSION.id,
          close_blocked_reason: null,
        },
      ],
      settle_coin: "USDT",
      truncated: false,
    };
    apiFetchMock.mockResolvedValueOnce(positions);

    await expect(getAccountPositions(SESSION.exchange_account_id, "jwt")).resolves.toEqual(
      positions,
    );

    expect(apiFetchMock).toHaveBeenCalledWith(
      `/api/v1/exchange-accounts/${SESSION.exchange_account_id}/positions`,
      { method: "GET", token: "jwt" },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
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
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });
});
