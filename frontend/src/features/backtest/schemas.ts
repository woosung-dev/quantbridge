// Sprint FE-04: Backtest domain Zod schemas.
// BE는 Decimal 필드를 @field_serializer로 **문자열** 로 직렬화 (backend/src/backtest/schemas.py).
// 따라서 응답 파싱 시 str → number transform + Number.isFinite 가드가 필수.
// 요청은 BE가 Pydantic Decimal 파싱을 지원하므로 number 그대로 전송.

import { z } from "zod";

// --- Decimal 문자열 → finite number 변환 ----------------------------------

const decimalString = z.string().transform((s, ctx) => {
  const n = Number.parseFloat(s);
  if (!Number.isFinite(n)) {
    ctx.addIssue({
      code: "custom",
      message: `non-finite decimal string: ${s}`,
    });
    return z.NEVER;
  }
  return n;
});

// --- Enums ---------------------------------------------------------------

export const BacktestStatusSchema = z.enum([
  "queued",
  "running",
  "cancelling",
  "completed",
  "failed",
  "cancelled",
]);
export type BacktestStatus = z.infer<typeof BacktestStatusSchema>;

export const TimeframeSchema = z.enum(["1m", "5m", "15m", "1h", "4h", "1d"]);
export type Timeframe = z.infer<typeof TimeframeSchema>;

export const TradeDirectionSchema = z.enum(["long", "short"]);
export type TradeDirection = z.infer<typeof TradeDirectionSchema>;

export const TradeStatusSchema = z.enum(["open", "closed"]);
export type TradeStatus = z.infer<typeof TradeStatusSchema>;

// --- Request --------------------------------------------------------------

export const CreateBacktestRequestSchema = z
  .object({
    strategy_id: z.uuid(),
    symbol: z.string().min(3).max(32),
    timeframe: TimeframeSchema,
    period_start: z.iso.datetime({ offset: true }),
    period_end: z.iso.datetime({ offset: true }),
    initial_capital: z.number().positive().refine(Number.isFinite, {
      message: "initial_capital must be finite",
    }),
  })
  .refine((v) => new Date(v.period_end) > new Date(v.period_start), {
    message: "period_end must be after period_start",
    path: ["period_end"],
  });
export type CreateBacktestRequest = z.infer<typeof CreateBacktestRequestSchema>;

// --- Response: base -------------------------------------------------------

export const BacktestCreatedResponseSchema = z.object({
  backtest_id: z.uuid(),
  status: BacktestStatusSchema,
  created_at: z.iso.datetime({ offset: true }),
});
export type BacktestCreatedResponse = z.infer<
  typeof BacktestCreatedResponseSchema
>;

export const BacktestProgressResponseSchema = z.object({
  backtest_id: z.uuid(),
  status: BacktestStatusSchema,
  started_at: z.iso.datetime({ offset: true }).nullable(),
  completed_at: z.iso.datetime({ offset: true }).nullable(),
  error: z.string().nullable(),
  stale: z.boolean().default(false),
});
export type BacktestProgressResponse = z.infer<
  typeof BacktestProgressResponseSchema
>;

export const BacktestCancelResponseSchema = z.object({
  backtest_id: z.uuid(),
  status: BacktestStatusSchema,
  message: z.string(),
});
export type BacktestCancelResponse = z.infer<
  typeof BacktestCancelResponseSchema
>;

// --- Summary + Detail -----------------------------------------------------

export const BacktestSummarySchema = z.object({
  id: z.uuid(),
  strategy_id: z.uuid(),
  symbol: z.string(),
  timeframe: z.string(),
  period_start: z.iso.datetime({ offset: true }),
  period_end: z.iso.datetime({ offset: true }),
  status: BacktestStatusSchema,
  created_at: z.iso.datetime({ offset: true }),
  completed_at: z.iso.datetime({ offset: true }).nullable(),
});
export type BacktestSummary = z.infer<typeof BacktestSummarySchema>;

export const BacktestMetricsOutSchema = z.object({
  total_return: decimalString,
  sharpe_ratio: decimalString,
  max_drawdown: decimalString,
  win_rate: decimalString,
  num_trades: z.number().int(),
});
export type BacktestMetricsOut = z.infer<typeof BacktestMetricsOutSchema>;

export const EquityPointSchema = z.object({
  timestamp: z.iso.datetime({ offset: true }),
  value: decimalString,
});
export type EquityPoint = z.infer<typeof EquityPointSchema>;

export const BacktestDetailSchema = BacktestSummarySchema.extend({
  initial_capital: decimalString,
  metrics: BacktestMetricsOutSchema.nullable().optional(),
  equity_curve: z.array(EquityPointSchema).nullable().optional(),
  error: z.string().nullable().optional(),
});
export type BacktestDetail = z.infer<typeof BacktestDetailSchema>;

// --- Trade ---------------------------------------------------------------

export const TradeItemSchema = z.object({
  trade_index: z.number().int(),
  direction: TradeDirectionSchema,
  status: TradeStatusSchema,
  entry_time: z.iso.datetime({ offset: true }),
  exit_time: z.iso.datetime({ offset: true }).nullable(),
  entry_price: decimalString,
  exit_price: decimalString.nullable(),
  size: decimalString,
  pnl: decimalString,
  return_pct: decimalString,
  fees: decimalString,
});
export type TradeItem = z.infer<typeof TradeItemSchema>;

// --- Pagination ----------------------------------------------------------

export function pageSchema<T extends z.ZodTypeAny>(item: T) {
  return z.object({
    items: z.array(item),
    total: z.number().int(),
    limit: z.number().int(),
    offset: z.number().int(),
  });
}

export const BacktestListResponseSchema = pageSchema(BacktestSummarySchema);
export type BacktestListResponse = z.infer<typeof BacktestListResponseSchema>;

export const TradeListResponseSchema = pageSchema(TradeItemSchema);
export type TradeListResponse = z.infer<typeof TradeListResponseSchema>;
