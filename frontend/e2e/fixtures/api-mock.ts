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
