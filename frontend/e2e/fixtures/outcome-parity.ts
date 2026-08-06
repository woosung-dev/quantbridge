// outcome-parity e2e 가 라우팅하는 응답 본문 — **순수 데이터만** 둔다.
//
// ★`@playwright/test` 를 import 하지 않는다. 그래야 vitest 가 이 파일을 그대로 읽어
// 실제 Zod 스키마(`StrategyListResponseSchema` 등)에 대입할 수 있다
// (`src/features/live-sessions/__tests__/outcome-parity-e2e-fixtures.test.ts`).
//
// ★왜 분리했나 — r1 의 mock 은 전략 목록을 `{id, name, tags, parse_status, updated_at}` +
// `page_size` 로 줄여 썼는데, 클라이언트는 `StrategyListResponseSchema.parse(raw)` 를
// 호출한다(`src/features/strategy/api.ts`). 필수 필드와 `limit`/`total_pages` 가 없어
// **그 query 는 parse 에서 죽고 있었다.** 화면은 폴백으로 진행하므로 e2e 는 초록이었다 —
// 즉 그 spec 은 "유효한 API 응답"을 한 번도 검증하지 않았다(codex 적대 리뷰 P1).
// 이제 대입 자체를 단위테스트가 매번 돌린다.
//
// 값은 2026-08-06 소크 실측 응답의 형태 그대로다 — 세션 축 매칭 0 + 커버리지 `null`,
// 전략 축 매칭 41 + 51자리 Decimal.

export const STRATEGY_ID = "c0000000-0000-4000-8000-000000000001";
export const SESSION_ID = "e0000000-0000-4000-8000-0000000000a6";
export const EXCHANGE_ACCOUNT_ID = "a0000000-0000-4000-b000-000000000001";
export const USER_ID = "a0000000-0000-4000-a000-000000000001";

/** 51자리 — qa 증거(`overflow.json`)의 최악 사례. scrollWidth 551px vs clientWidth 66px. */
export const LONG_SD_NET = "1.2713870047249048479614767686509482542467350726347";
export const LONG_NOTIONAL = "153223.9543200000000000";

export const MOCK_STRATEGY_LIST = {
  items: [
    {
      id: STRATEGY_ID,
      name: "BTC RSI Mean Reversion",
      pine_version: "v5",
      parse_status: "ok",
      parse_errors: null,
      timeframe: "1m",
      symbol: "BTC/USDT",
      tags: [],
      trading_sessions: [],
      settings: null,
      is_archived: false,
      created_at: "2026-08-06T00:00:00Z",
      updated_at: "2026-08-06T00:00:00Z",
    },
  ],
  total: 1,
  page: 0,
  limit: 20,
  total_pages: 1,
};

export const MOCK_EXCHANGE_ACCOUNT_LIST = {
  items: [
    {
      id: EXCHANGE_ACCOUNT_ID,
      exchange: "bybit",
      mode: "demo",
      label: "Bybit Demo",
      api_key_masked: "***masked***",
      exchange_uid: null,
      read_only: false,
      created_at: "2026-08-06T00:00:00Z",
    },
  ],
};

export const MOCK_LIVE_SESSION_LIST = {
  items: [
    {
      id: SESSION_ID,
      user_id: USER_ID,
      strategy_id: STRATEGY_ID,
      exchange_account_id: EXCHANGE_ACCOUNT_ID,
      symbol: "BTC/USDT",
      interval: "1m",
      is_active: false,
      last_evaluated_bar_time: "2026-08-06T01:03:00Z",
      created_at: "2026-08-06T00:06:00Z",
      deactivated_at: "2026-08-06T01:04:00Z",
      deactivated_reason: "user_stopped",
      equity_baseline_usdt: "1000",
    },
  ],
  total: 1,
};

export const MOCK_LIVE_SESSION_STATE = {
  session_id: SESSION_ID,
  evaluated: true,
  schema_version: 1,
  last_strategy_state_report: {},
  total_closed_trades: 0,
  total_realized_pnl: "0",
  equity_curve: [],
  updated_at: "2026-08-06T01:04:00Z",
};

export const MOCK_LIVE_SESSION_EVENTS = { items: [] };

const EMPTY_SESSION_SCOPE = {
  matched_count: 0,
  expected_gross: "0",
  actual_net: "0",
  decomposable_count: 0,
  decomposable_expected_gross: null,
  execution_gap: null,
  cost: null,
  decomposable_actual_net: null,
  actual_gross: null,
  round_trip_notional: null,
  effective_cost_pct_per_leg: null,
  effective_cost_pct_round_trip: null,
  edge_pct_round_trip: null,
  cost_to_edge_ratio: null,
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
  match_coverage_pct: null,
  decomposition_coverage_pct: null,
  sample_n: 0,
  sample_mean_net: null,
  sample_sd_net: null,
  sample_required_n: null,
  sample_sufficient: false,
  ratio_sample_n: 0,
  ratio_sample_required_n: null,
  ratio_sample_sufficient: false,
};

const LIVE_STRATEGY_SCOPE = {
  ...EMPTY_SESSION_SCOPE,
  matched_count: 41,
  expected_gross: "30.72856076",
  actual_net: "-73.55319202",
  decomposable_count: 41,
  decomposable_expected_gross: "30.72856076",
  execution_gap: "-19.9238407600000000",
  cost: "-84.3579120200000000",
  decomposable_actual_net: "-73.55319202",
  actual_gross: "10.8047200000000000",
  round_trip_notional: LONG_NOTIONAL,
  effective_cost_pct_per_leg: "0.0551",
  effective_cost_pct_round_trip: "0.1101",
  edge_pct_round_trip: "-0.0960",
  cost_to_edge_ratio: "1.1468966839272191793043545467600224483092392650181",
  expected_only_count: 68,
  expected_only_gross: "20",
  expected_only_dispatched_count: 68,
  match_coverage_pct: "36.607142857142857142857142857",
  decomposition_coverage_pct: "100",
  sample_n: 41,
  sample_mean_net: "-1.7939802931707317073170731707317073170731707317073",
  sample_sd_net: LONG_SD_NET,
  sample_required_n: 30,
  sample_sufficient: true,
  ratio_sample_n: 41,
  ratio_sample_required_n: 30,
  ratio_sample_sufficient: true,
};

export const MOCK_OUTCOME_PARITY = {
  session_id: SESSION_ID,
  session: EMPTY_SESSION_SCOPE,
  strategy: LIVE_STRATEGY_SCOPE,
  unattributed_count: 3,
  inferred_attribution_count: 0,
  ledger_supported: true,
  strategy_session_count: 31,
  assumption: {
    source: "house_default",
    taker_fee_pct: "0.055",
    slippage_pct: "0.05",
    maker_fee_pct: "0.02",
    implied_round_trip_pct: "0.21",
  },
};
