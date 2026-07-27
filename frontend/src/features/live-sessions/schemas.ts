// Sprint 26 — Live Signal Auto-Trading 스키마.
// Zod v4 (`zod/v4`) — Decimal 필드는 string 직렬화 (backend Decimal → JSON string).

import { z } from "zod/v4";

// ── Enum schemas ────────────────────────────────────────────────────────

export const LiveSignalIntervalSchema = z.enum(["1m", "5m", "15m", "1h"]);
export type LiveSignalInterval = z.infer<typeof LiveSignalIntervalSchema>;

export const LiveSignalEventStatusSchema = z.enum(["pending", "dispatched", "failed"]);
export type LiveSignalEventStatus = z.infer<typeof LiveSignalEventStatusSchema>;

// ── Response schemas ────────────────────────────────────────────────────

export const LiveSessionSchema = z.object({
  id: z.uuid(),
  user_id: z.uuid(),
  strategy_id: z.uuid(),
  exchange_account_id: z.uuid(),
  symbol: z.string(),
  interval: LiveSignalIntervalSchema,
  is_active: z.boolean(),
  last_evaluated_bar_time: z.string().nullable(),
  created_at: z.string(),
  deactivated_at: z.string().nullable(),
  // 세션 시작 시 1회 스냅샷한 자본 기준선. 주문 수량이 이 값에서 나온다.
  equity_baseline_usdt: z.string().nullable().optional(),
});
export type LiveSession = z.infer<typeof LiveSessionSchema>;

export const LiveSessionListResponseSchema = z.object({
  items: z.array(LiveSessionSchema),
  total: z.number(),
});
export type LiveSessionListResponse = z.infer<typeof LiveSessionListResponseSchema>;

// Sprint 28 Slice 3 (BL-140b) — equity_curve datapoint (BE 정합)
export const EquityCurvePointSchema = z.object({
  timestamp_ms: z.number(),
  cumulative_pnl: z.string(), // Decimal as string (precision 보존)
  // BL-458 — 그 시점 델타(주문 1건)의 출처. 누적값의 출처가 아니다 — 첫 혼재 거래
  // 이후의 누적은 구조상 혼재다. `.optional()` 인 이유는 `.default()` 가 추론 출력
  // 타입에서 필수가 되어 기존 픽스처 전부를 깨기 때문이다. 부재는 "추정" 으로 읽는다
  // (증거 부재가 "확정" 이 되면 안 된다).
  source: z.enum(["confirmed", "estimated"]).optional(),
});
export type EquityCurvePoint = z.infer<typeof EquityCurvePointSchema>;

/** 커브 포인트 출처 — 부재는 추정으로 폴백한다(fail-safe 방향). */
export function curvePointSource(
  point: Pick<EquityCurvePoint, "source">,
): "confirmed" | "estimated" {
  return point.source ?? "estimated";
}

export const LiveSignalStateSchema = z.object({
  session_id: z.uuid(),
  evaluated: z.boolean().default(true),
  schema_version: z.number(),
  last_strategy_state_report: z.record(z.string(), z.unknown()),
  total_closed_trades: z.number(),
  total_realized_pnl: z.string(),
  // BL-458 — 출처 소계. `total_realized_pnl` 은 여전히 둘을 합친 값이다.
  // `.optional()` — 구 응답 호환 + 부분 분할을 "0" 으로 위장하지 않기 위해.
  confirmed_realized_pnl: z.string().optional(),
  estimated_realized_pnl: z.string().optional(),
  confirmed_closed_trades: z.number().optional(),
  estimated_closed_trades: z.number().optional(),
  // Sprint 28 Slice 3 (BL-140b) — cumulative realized PnL timeseries.
  // 형식: [{"timestamp_ms": 1700000000000, "cumulative_pnl": "0.123"}, ...]
  // 빈 array default (legacy session 호환).
  equity_curve: z.array(EquityCurvePointSchema).default([]),
  updated_at: z.string().nullable(),
});
export type LiveSignalState = z.infer<typeof LiveSignalStateSchema>;

export const LiveSignalEventSchema = z.object({
  id: z.uuid(),
  session_id: z.uuid(),
  bar_time: z.string(),
  sequence_no: z.number(),
  action: z.string(),
  direction: z.string(),
  trade_id: z.string(),
  qty: z.string(),
  comment: z.string(),
  status: LiveSignalEventStatusSchema,
  order_id: z.uuid().nullable(),
  error_message: z.string().nullable(),
  retry_count: z.number(),
  created_at: z.string(),
  dispatched_at: z.string().nullable(),
});
export type LiveSignalEvent = z.infer<typeof LiveSignalEventSchema>;

export const LiveSignalEventListResponseSchema = z.object({
  items: z.array(LiveSignalEventSchema),
});
export type LiveSignalEventListResponse = z.infer<typeof LiveSignalEventListResponseSchema>;

// ── Position reconciliation response ───────────────────────────────────

export const ExchangePositionSchema = z.object({
  side: z.string(),
  size: z.string(),
  entry_price: z.string().nullable(),
  mark_price: z.string().nullable(),
  unrealized_pnl: z.string().nullable(),
  take_profit_prices: z.array(z.string()),
  stop_loss_prices: z.array(z.string()),
  has_trailing_stop: z.boolean(),
  liquidation_price: z.string().nullable(),
  leverage: z.string().nullable(),
});
export type ExchangePosition = z.infer<typeof ExchangePositionSchema>;

export const PositionDiffSchema = z.object({
  verdict: z.enum([
    "match",
    "qty_mismatch",
    "side_mismatch",
    "exchange_only",
    "local_only",
    "unknown",
  ]),
  local_source: z.enum(["strategy_state_report", "none"]),
});
export type PositionDiff = z.infer<typeof PositionDiffSchema>;

export const LiveSessionPositionsResponseSchema = z.object({
  session_id: z.uuid(),
  symbol: z.string(),
  market_type: z.enum(["futures", "spot"]),
  supported: z.boolean(),
  reason: z
    .enum([
      "live_mode_stub",
      "exchange_unsupported",
      "spot_position_api_unsupported",
      "settings_unset",
    ])
    .nullable(),
  fetched_at: z.string().nullable(),
  positions: z.array(ExchangePositionSchema),
  local_open_trades_snapshot: z.array(z.record(z.string(), z.unknown())),
  diff: PositionDiffSchema,
});
export type LiveSessionPositions = z.infer<typeof LiveSessionPositionsResponseSchema>;

// ── BL-498 계정 스코프 포지션 ──────────────────────────────────────────
// 세션 스코프 대조와 용도가 다르다 — 그쪽은 발산 감지, 이쪽은 **잔여 노출 관리**다.
// fail-closed 종료가 주문만 걷고 포지션은 남기는 것은 설계이므로 활성 세션이 0건인
// 상태가 반복된다. 그때도 보이고 닫을 수 있어야 한다.
// ★계약이 `live-sessions` 에 사는 이유 — `ExchangePositionSchema` 와 청산 훅이 여기
//   있고, 행의 핵심 필드가 `closable_session_id` 다. 계정 id 는 조회 파라미터일 뿐이라
//   `features/trading` 으로 옮기면 두 feature 사이에 새 순환 의존이 생긴다.

export const AccountPositionRowSchema = z.object({
  symbol: z.string(),
  position: ExchangePositionSchema,
  closable_session_id: z.uuid().nullable(),
  close_blocked_reason: z
    .enum(["no_owning_session", "hedge_unsupported", "read_only_key"])
    .nullable(),
});
export type AccountPositionRow = z.infer<typeof AccountPositionRowSchema>;

export const AccountPositionsResponseSchema = z.object({
  account_id: z.uuid(),
  supported: z.boolean(),
  reason: z.enum(["live_mode_stub", "exchange_unsupported"]).nullable(),
  fetched_at: z.string().nullable(),
  rows: z.array(AccountPositionRowSchema),
  settle_coin: z.string(),
  truncated: z.boolean(),
});
export type AccountPositions = z.infer<typeof AccountPositionsResponseSchema>;

export const ClosePositionResponseSchema = z.object({
  order_id: z.string(),
  state: z.string(),
  detail: z.string().nullable(),
});
export type ClosePositionResponse = z.infer<typeof ClosePositionResponseSchema>;

// ── Form schema — UI input only (RHF + Zod v4 transform 불필요) ────────

export const LiveSessionFormSchema = z.object({
  strategy_id: z.uuid("Strategy 를 선택해주세요"),
  exchange_account_id: z.uuid("거래소 계정을 선택해주세요"),
  symbol: z.string().min(1, "심볼은 필수입니다").max(32, "심볼은 최대 32자입니다"),
  interval: LiveSignalIntervalSchema,
});
export type LiveSessionForm = z.infer<typeof LiveSessionFormSchema>;

// ── Register request (POST body) ────────────────────────────────────────

export const RegisterLiveSessionRequestSchema = LiveSessionFormSchema;
export type RegisterLiveSessionRequest = z.infer<typeof RegisterLiveSessionRequestSchema>;
