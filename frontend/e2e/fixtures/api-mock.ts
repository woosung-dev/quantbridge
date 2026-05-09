// Sprint 25 — API_ROUTES 단일 source of truth.
//
// codex G.0 iter 2 P2 #4 critical: 기존 trading-ui.spec.ts 가 `/api/v1/trading/...`
// prefix 사용했지만 실제 frontend api.ts 는 `trading/` 없는 `/api/v1/...` 직접 사용.
// 활성화 시 unmocked → real backend leak. 본 파일이 정확한 prefix 단일 정의.
//
// 검증 대상 (frontend/src/features/{strategy,trading,backtest}/api.ts):
//   /api/v1/strategies         (+ /parse, /:id, /:id/tags 등)
//   /api/v1/orders
//   /api/v1/kill-switch/events
//   /api/v1/exchange-accounts
//   /api/v1/backtests
//   /api/v1/stress-tests
//
// Trailing wildcard `**` 가 query param + nested path (/cancel, /:id 등) 모두 cover.

import type { Route } from "@playwright/test";

export const API_ROUTES = {
  strategies: "**/api/v1/strategies**",
  exchangeAccounts: "**/api/v1/exchange-accounts**",
  orders: "**/api/v1/orders**",
  killSwitch: "**/api/v1/kill-switch/events**",
  backtests: "**/api/v1/backtests**",
  stressTests: "**/api/v1/stress-tests**",
  liveSessions: "**/api/v1/live-sessions**",  // Sprint 26
  // Sprint 46 W2 — Tier 1 critical 신규 엔드포인트.
  // webhooks: TestOrderDialog HMAC POST 경로 (`/api/v1/webhooks/{strategy_id}?token=...`).
  // shareView: 비로그인 share token GET (`/api/v1/backtests/share/{token}`).
  webhooks: "**/api/v1/webhooks/**",
  shareView: "**/api/v1/backtests/share/**",
} as const;

export const MOCK_DEMO_ACCOUNT = {
  id: "a0000000-0000-4000-a000-000000000001",
  name: "Bybit Demo",
  exchange: "bybit_futures",
  mode: "demo",
  label: "Bybit Demo",
  api_key_masked: "***masked***",
  is_active: true,
  created_at: "2026-04-24T00:00:00Z",
} as const;

export const MOCK_KS_EVENT_ACTIVE = {
  id: "b0000000-0000-4000-b000-000000000001",
  trigger_type: "daily_loss",
  trigger_value: "600.00",
  threshold: "500.00",
  triggered_at: "2026-04-24T10:00:00Z",
  resolved_at: null,
} as const;

export const MOCK_KS_EVENT_RESOLVED = {
  id: "b0000000-0000-4000-b000-000000000001",
  trigger_type: "daily_loss",
  trigger_value: "600.00",
  threshold: "500.00",
  triggered_at: "2026-04-24T10:00:00Z",
  resolved_at: "2026-04-24T11:00:00Z",
} as const;

// Helper: JSON fulfill route — DRY.
export function fulfillJson(data: unknown, status = 200) {
  return (route: Route) =>
    route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(data),
    });
}

// ── Sprint 46 W2 — Tier 1 신규 fixture builder ────────────────────────────

// 422 unsupported_builtins payload — backtest-form FormErrorInline 표시 트리거.
// detail.detail.unsupported_builtins 가 list 일 때 `*-unsupported-card` (UL 포함) 렌더.
export function makeUnsupported422(
  builtins: readonly string[],
  friendlyMessage = "heikinashi / request.security 는 Trust Layer 위반입니다.",
) {
  return {
    detail: {
      code: "STRATEGY_NOT_RUNNABLE",
      detail: "미지원 builtin 포함",
      unsupported_builtins: builtins,
      friendly_message: friendlyMessage,
    },
  };
}

// Strategy parse preview — wizard step-2 의 ParseResultPanel 렌더 입력.
export function makeParsePreview(opts: {
  status?: "ok" | "unsupported" | "error";
  unsupported?: readonly string[];
  pineVersion?: "v4" | "v5";
}) {
  return {
    status: opts.status ?? "ok",
    pine_version: opts.pineVersion ?? "v5",
    warnings: [],
    errors: [],
    entry_count: 1,
    exit_count: 1,
    functions_used: ["ta.sma", "ta.crossover"],
    unsupported_builtins: opts.unsupported ?? [],
    is_runnable: (opts.unsupported ?? []).length === 0,
  };
}

// Backtest detail mock — completed status + minimal metrics + equity_curve.
// /backtests/{id} 페이지 렌더 트리거. metrics 안 num_trades / total_return 등 24 panel.
export function makeBacktestDetail(opts: {
  id: string;
  strategyId: string;
  status?: "queued" | "running" | "completed" | "failed";
  withMetrics?: boolean;
  withEquity?: boolean;
}) {
  const baseTs = "2026-04-01T00:00:00+00:00";
  const completedTs = "2026-04-01T00:30:00+00:00";
  return {
    id: opts.id,
    strategy_id: opts.strategyId,
    symbol: "BTC/USDT",
    timeframe: "1h",
    period_start: "2026-01-01T00:00:00+00:00",
    period_end: "2026-04-01T00:00:00+00:00",
    status: opts.status ?? "completed",
    created_at: baseTs,
    completed_at: opts.status === "completed" ? completedTs : null,
    initial_capital: "10000",
    config: {
      leverage: 1,
      fees: 0.001,
      slippage: 0.0005,
      include_funding: true,
    },
    metrics: opts.withMetrics
      ? {
          total_return: "0.1234",
          sharpe_ratio: "1.5",
          max_drawdown: "-0.0567",
          win_rate: "0.55",
          num_trades: 42,
          mdd_unit: "equity_ratio",
          mdd_exceeds_capital: false,
        }
      : null,
    equity_curve: opts.withEquity
      ? [
          { timestamp: "2026-01-01T00:00:00+00:00", value: "10000" },
          { timestamp: "2026-02-01T00:00:00+00:00", value: "10500" },
          { timestamp: "2026-04-01T00:00:00+00:00", value: "11234" },
        ]
      : null,
    error: null,
  };
}

// Backtest progress — `/backtests/{id}/progress` 응답.
export function makeBacktestProgress(opts: {
  id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
}) {
  return {
    backtest_id: opts.id,
    status: opts.status,
    started_at:
      opts.status === "running" || opts.status === "completed"
        ? "2026-04-01T00:05:00+00:00"
        : null,
    completed_at:
      opts.status === "completed" ? "2026-04-01T00:30:00+00:00" : null,
    error: null,
    stale: false,
  };
}

// Share token response — POST /backtests/{id}/share.
export function makeShareToken(backtestId: string, token = "share-token-46-w2") {
  return {
    backtest_id: backtestId,
    share_token: token,
    share_url_path: `/share/backtests/${token}`,
    revoked: false,
  };
}

// Live session state — useLiveSessionState 응답.
export function makeLiveSessionState(opts: {
  sessionId: string;
  closedTrades?: number;
  realizedPnl?: string;
  equityCurve?: Array<{ timestamp_ms: number; cumulative_pnl: string }>;
}) {
  return {
    session_id: opts.sessionId,
    schema_version: 1,
    last_strategy_state_report: {},
    last_open_trades_snapshot: {},
    total_closed_trades: opts.closedTrades ?? 0,
    total_realized_pnl: opts.realizedPnl ?? "0",
    equity_curve: opts.equityCurve ?? [],
    updated_at: "2026-05-09T00:00:00+00:00",
  };
}
