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
  // BL-484 — 세션이 왜 죽었는지. 코드→한국어 변환은 `deactivation-reason.ts` 가 SSOT.
  // `.optional()` 인 이유는 `equity_baseline_usdt` 와 같다 — 마이그레이션 이전에 종료된
  // 행은 null 이고, 구 응답/픽스처에는 키 자체가 없다. 둘 다 "사유 미기록" 으로 읽는다.
  deactivated_reason: z.string().nullable().optional(),
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
  order_state: z.string().nullable().optional(),
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

// ── 청산 ───────────────────────────────────────────────────────────────
// 서버는 잔여 미체결 진입을 **두 경로**로 말한다. 둘은 같은 화면인데 뜻이 다르다.
//   409 `resting_conditional_entries` — 포지션이 0이라 청산 주문을 **안 냈다** (CLI rc 3)
//   202 `resting_entries[]`           — 청산은 **접수했고** 진입이 남아 있다 (CLI rc 4)
// `qty`·`trigger_price` 는 백엔드에서 `Decimal` 이지만 와이어에서는 문자열이다
// (409 는 `model_dump(mode="json")`, 202 는 Pydantic 직렬화). `ExchangePositionSchema`
// 와 같은 규약이다.

export const RestingEntryOrderSchema = z.object({
  order_id: z.string(),
  side: z.string(),
  qty: z.string().nullable(),
  trigger_price: z.string().nullable(),
  order_link_id: z.string().nullable(),
});
export type RestingEntryOrder = z.infer<typeof RestingEntryOrderSchema>;

export const ClosePositionResponseSchema = z.object({
  order_id: z.string(),
  state: z.string(),
  detail: z.string().nullable(),
  // ★`.default()` 가 필수다. 이 두 필드가 없던 시절의 픽스처·구 응답이 파싱을 통과해야
  //   하는데, 없다고 `undefined` 로 두면 소비자가 매번 방어해야 한다. 기본값은 서버
  //   모델의 기본값과 같다(`ClosePositionResponse` = `[]` / `False`).
  resting_entries: z.array(RestingEntryOrderSchema).default([]),
  // 빈 목록만으로는 "잔량 없음"과 "거래소에 못 물어봤다"를 구분할 수 없다.
  resting_entries_unknown: z.boolean().default(false),
});
export type ClosePositionResponse = z.infer<typeof ClosePositionResponseSchema>;

/**
 * 409 `{"detail": {...}}` 의 **안쪽** dict.
 *
 * ★같은 엔드포인트의 다른 409 는 `detail` 이 **평문 문자열**이다
 * (`no_open_position` · `hedge_unsupported` · `position_side_unsupported`).
 * 그래서 `code` 를 `z.literal` 로 못 박아 `safeParse` 가 그 셋을 **거부**하게 한다 —
 * 이 스키마가 통과하는 것은 잔량 409 하나뿐이다.
 */
export const RestingEntriesConflictSchema = z.object({
  code: z.literal("resting_conditional_entries"),
  count: z.number(),
  detail: z.string(),
  orders: z.array(RestingEntryOrderSchema).default([]),
});
export type RestingEntriesConflict = z.infer<typeof RestingEntriesConflictSchema>;

// ── Outcome parity response ───────────────────────────────────────────

export const OutcomeParityScopeSchema = z.object({
  matched_count: z.number(),
  expected_gross: z.string(),
  actual_net: z.string(),
  decomposable_count: z.number(),
  decomposable_expected_gross: z.string().nullable(),
  execution_gap: z.string().nullable(),
  cost: z.string().nullable(),
  decomposable_actual_net: z.string().nullable(),
  actual_gross: z.string().nullable(),
  round_trip_notional: z.string().nullable(),
  effective_cost_pct_per_leg: z.string().nullable(),
  effective_cost_pct_round_trip: z.string().nullable(),
  edge_pct_round_trip: z.string().nullable(),
  cost_to_edge_ratio: z.string().nullable(),
  undecomposed_count: z.number(),
  undecomposed_net: z.string(),
  expected_only_count: z.number(),
  expected_only_gross: z.string(),
  expected_only_pending_count: z.number(),
  expected_only_failed_count: z.number(),
  expected_only_dispatched_count: z.number(),
  actual_only_count: z.number(),
  actual_only_net: z.string(),
  ledger_only_count: z.number(),
  ledger_only_net: z.string(),
  inferred_attribution_count: z.number(),
  match_coverage_pct: z.string().nullable(),
  decomposition_coverage_pct: z.string().nullable(),
  sample_n: z.number(),
  sample_mean_net: z.string().nullable(),
  sample_sd_net: z.string().nullable(),
  sample_required_n: z.number().nullable(),
  sample_sufficient: z.boolean(),
  ratio_sample_n: z.number(),
  ratio_sample_required_n: z.number().nullable(),
  ratio_sample_sufficient: z.boolean(),
});
export type OutcomeParityScope = z.infer<typeof OutcomeParityScopeSchema>;

export const OutcomeParityAssumptionSchema = z.object({
  source: z.literal("house_default"),
  taker_fee_pct: z.string(),
  slippage_pct: z.string(),
  maker_fee_pct: z.string(),
  implied_round_trip_pct: z.string(),
});
export type OutcomeParityAssumption = z.infer<typeof OutcomeParityAssumptionSchema>;

export const OutcomeParityResponseSchema = z.object({
  session_id: z.uuid(),
  session: OutcomeParityScopeSchema,
  strategy: OutcomeParityScopeSchema,
  unattributed_count: z.number(),
  inferred_attribution_count: z.number(),
  ledger_supported: z.boolean(),
  strategy_session_count: z.number(),
  assumption: OutcomeParityAssumptionSchema,
});
export type OutcomeParityResponse = z.infer<typeof OutcomeParityResponseSchema>;

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
