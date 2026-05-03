// Sprint 26 — Live Signal Auto-Trading 스키마.
// Zod v4 (`zod/v4`) — Decimal 필드는 string 직렬화 (backend Decimal → JSON string).

import { z } from "zod/v4";

// ── Enum schemas ────────────────────────────────────────────────────────

export const LiveSignalIntervalSchema = z.enum(["1m", "5m", "15m", "1h"]);
export type LiveSignalInterval = z.infer<typeof LiveSignalIntervalSchema>;

export const LiveSignalEventStatusSchema = z.enum([
  "pending",
  "dispatched",
  "failed",
]);
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
});
export type LiveSession = z.infer<typeof LiveSessionSchema>;

export const LiveSessionListResponseSchema = z.object({
  items: z.array(LiveSessionSchema),
  total: z.number(),
});
export type LiveSessionListResponse = z.infer<
  typeof LiveSessionListResponseSchema
>;

export const LiveSignalStateSchema = z.object({
  session_id: z.uuid(),
  schema_version: z.number(),
  last_strategy_state_report: z.record(z.string(), z.unknown()),
  last_open_trades_snapshot: z.record(z.string(), z.unknown()),
  total_closed_trades: z.number(),
  total_realized_pnl: z.string(),
  updated_at: z.string(),
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
export type LiveSignalEventListResponse = z.infer<
  typeof LiveSignalEventListResponseSchema
>;

// ── Form schema — UI input only (RHF + Zod v4 transform 불필요) ────────

export const LiveSessionFormSchema = z.object({
  strategy_id: z.uuid("Strategy 를 선택해주세요"),
  exchange_account_id: z.uuid("거래소 계정을 선택해주세요"),
  symbol: z
    .string()
    .min(1, "심볼은 필수입니다")
    .max(32, "심볼은 최대 32자입니다"),
  interval: LiveSignalIntervalSchema,
});
export type LiveSessionForm = z.infer<typeof LiveSessionFormSchema>;

// ── Register request (POST body) ────────────────────────────────────────

export const RegisterLiveSessionRequestSchema = LiveSessionFormSchema;
export type RegisterLiveSessionRequest = z.infer<
  typeof RegisterLiveSessionRequestSchema
>;
