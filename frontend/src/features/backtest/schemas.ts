// Sprint FE-04: Backtest domain Zod schemas.
// BE는 Decimal 필드를 @field_serializer로 **문자열** 로 직렬화 (backend/src/backtest/schemas.py).
// 따라서 응답 파싱 시 str → number transform + Number.isFinite 가드가 필수.
// 요청은 BE가 Pydantic Decimal 파싱을 지원하므로 number 그대로 전송.

import { z } from "zod/v4";

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

// Sprint 38 BL-188 v3 — trading_sessions FE enum (Live `is_allowed` parity).
// 빈 list = 24h. 비어있지 않으면 BE v2_adapter 가 placement+fill gate 적용.
export const TradingSessionSchema = z.enum(["asia", "london", "ny"]);
export type TradingSession = z.infer<typeof TradingSessionSchema>;

// --- Request --------------------------------------------------------------

// Sprint 31 BL-162a — TradingView strategy 속성 패턴 비용/마진 사용자 입력.
// BE Pydantic Field ge/le 정합:
//   leverage    : 1 ~ 125 (Bybit 표준)
//   fees_pct    : 0 ~ 0.01 (1%)
//   slippage_pct: 0 ~ 0.01 (1%)
// 기본값 (Bybit Perpetual taker 표준): 1x 현물 / 0.10% 수수료 / 0.05% 슬리피지 /
// 펀딩 ON. 사용자가 BacktestForm 에서 자기 strategy 에 맞게 변경.
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
    leverage: z
      .number()
      .min(1)
      .max(125)
      .refine(Number.isFinite, { message: "leverage must be finite" })
      .default(1),
    fees_pct: z
      .number()
      .min(0)
      .max(0.01)
      .refine(Number.isFinite, { message: "fees_pct must be finite" })
      .default(0.001),
    slippage_pct: z
      .number()
      .min(0)
      .max(0.01)
      .refine(Number.isFinite, { message: "slippage_pct must be finite" })
      .default(0.0005),
    include_funding: z.boolean().default(true),
    // Sprint 37 BL-188a — 폼 default_qty_type/value (Pine 미명시 시 사용).
    // priority chain: Pine strategy(default_qty_type=...) > 폼 입력 > None.
    default_qty_type: z
      .enum([
        "strategy.percent_of_equity",
        "strategy.cash",
        "strategy.fixed",
      ])
      .optional(),
    default_qty_value: z.number().positive().refine(Number.isFinite).optional(),
    // Sprint 38 BL-188 v3 — Live mirror canonical 입력 (1x equity-basis 한정).
    // BE `CreateBacktestRequest.position_size_pct` 와 동일 spec (gt 0 / le 100).
    // default_qty_type/value 와 동시 명시 시 422 reject — 본 schema `.refine()`
    // 가 client-side 1차 차단 (BE `_no_double_sizing` parity).
    position_size_pct: z
      .number()
      .gt(0)
      .lte(100)
      .refine(Number.isFinite, { message: "position_size_pct must be finite" })
      .nullish(),
    // Sprint 38 BL-188 v3 — Live Sessions mirror (asia/london/ny). 빈 list = 24h.
    // BE v2_adapter 가 entry placement + fill 양쪽 gate 적용. optional —
    // 기존 caller (rerun-button / onboarding step-3) 호환 + BE Pydantic
    // `Field(default_factory=list)` 가 누락 시 [] 로 처리.
    trading_sessions: z.array(TradingSessionSchema).optional(),
  })
  .refine((v) => new Date(v.period_end) > new Date(v.period_start), {
    message: "period_end must be after period_start",
    path: ["period_end"],
  })
  .refine(
    (v) =>
      (v.default_qty_type == null) === (v.default_qty_value == null),
    {
      message: "default_qty_type 와 default_qty_value 는 함께 명시 또는 함께 None",
      path: ["default_qty_value"],
    },
  )
  // Sprint 38 BL-188 v3 — double-sizing reject (BE `_no_double_sizing` parity).
  // position_size_pct (Live mirror) 와 default_qty_type/value (manual) 동시
  // 명시 = client-side 422 회피. canonical 1개 강제 — D2 toggle UI 가 한쪽만 fill.
  .refine(
    (v) =>
      !(
        v.position_size_pct != null &&
        (v.default_qty_type != null || v.default_qty_value != null)
      ),
    {
      message:
        "position_size_pct (Live mirror) 와 default_qty_type/value (manual) 동시 명시 불가",
      path: ["position_size_pct"],
    },
  );
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

// Sprint 30-γ-FE: BacktestMetrics PRD spec 24 필드 정합. 신규 12 필드는 모두
// Optional — γ-BE 머지 전 BE 응답에 미포함 시 null/undefined → UI "—" fallback.
// monthly_returns / drawdown_curve 는 list[tuple[str, Decimal]] BE 직렬화를
// list[list[str]] 으로 받음 → 각 항목 [timestamp, decimalString] tuple.
const monthlyReturnEntry = z.tuple([z.string(), decimalString]);
const drawdownPoint = z.tuple([z.string(), decimalString]);

export const BacktestMetricsOutSchema = z.object({
  total_return: decimalString,
  sharpe_ratio: decimalString,
  max_drawdown: decimalString,
  win_rate: decimalString,
  num_trades: z.number().int(),
  // Sprint 8b 확장 지표 (구 완료 백테스트 null)
  sortino_ratio: decimalString.nullable().optional(),
  calmar_ratio: decimalString.nullable().optional(),
  profit_factor: decimalString.nullable().optional(),
  avg_win: decimalString.nullable().optional(),
  avg_loss: decimalString.nullable().optional(),
  long_count: z.number().int().nullable().optional(),
  short_count: z.number().int().nullable().optional(),
  // Sprint 30-γ PRD JSONB 24 필드 정합 (12 신규 Optional)
  avg_holding_hours: decimalString.nullable().optional(),
  consecutive_wins_max: z.number().int().nullable().optional(),
  consecutive_losses_max: z.number().int().nullable().optional(),
  long_win_rate_pct: decimalString.nullable().optional(),
  short_win_rate_pct: decimalString.nullable().optional(),
  monthly_returns: z.array(monthlyReturnEntry).nullable().optional(),
  drawdown_duration: z.number().int().nullable().optional(),
  annual_return_pct: decimalString.nullable().optional(),
  total_trades: z.number().int().nullable().optional(),
  avg_trade_pct: decimalString.nullable().optional(),
  best_trade_pct: decimalString.nullable().optional(),
  worst_trade_pct: decimalString.nullable().optional(),
  drawdown_curve: z.array(drawdownPoint).nullable().optional(),
  // Sprint 32-D BL-156 — MDD 수학 정합 메타. mdd_unit = "equity_ratio" (현재
  // 유일 단위), mdd_exceeds_capital = MDD < -100% 여부 (자본 초과 손실 시
  // FE 가 leverage 가정 inline 표시).
  mdd_unit: z.string().nullable().optional(),
  mdd_exceeds_capital: z.boolean().nullable().optional(),
  // Sprint 34 BL-175 — Buy & Hold curve (BE OHLCV 첫/끝 close 기반 정확 계산).
  // [(ISO ts, decimalString)] tuple. drawdown_curve 와 동일 직렬화 패턴.
  // null 시 EquityChartV2 가 BH series 미렌더 + ChartLegend BH 항목 자동 hide
  // (Sprint 33 BL-175 hotfix 동작 보존, Surface Trust ADR-019 정합).
  buy_and_hold_curve: z.array(drawdownPoint).nullable().optional(),
});
export type BacktestMetricsOut = z.infer<typeof BacktestMetricsOutSchema>;

export const EquityPointSchema = z.object({
  timestamp: z.iso.datetime({ offset: true }),
  value: decimalString,
});
export type EquityPoint = z.infer<typeof EquityPointSchema>;

// PRD `backtests.config` JSONB 5 필드 (Sprint 30-α). BE 가 아직 응답에
// 포함하지 않을 수 있어 모두 nullable + optional. Sprint 30-γ-BE 에서 BE
// 응답 추가 후 graceful upgrade.
export const BacktestConfigSchema = z.object({
  leverage: z.number().nullable().optional(),
  fees: z.number().nullable().optional(),
  slippage: z.number().nullable().optional(),
  include_funding: z.boolean().nullable().optional(),
});
export type BacktestConfig = z.infer<typeof BacktestConfigSchema>;

export const BacktestDetailSchema = BacktestSummarySchema.extend({
  initial_capital: decimalString,
  config: BacktestConfigSchema.nullable().optional(),
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

// ---------------------------------------------------------------------------
// Stress Test (Phase C)
// ---------------------------------------------------------------------------

export const StressTestKindSchema = z.enum(["monte_carlo", "walk_forward"]);
export type StressTestKind = z.infer<typeof StressTestKindSchema>;

export const StressTestStatusSchema = z.enum([
  "queued",
  "running",
  "completed",
  "failed",
]);
export type StressTestStatus = z.infer<typeof StressTestStatusSchema>;

// Monte Carlo result — BE Decimal → str 직렬화에 대해 transform 적용.
// `equity_percentiles` 는 "5"/"25"/"50"/"75"/"95" 키를 가진 dict; 각 시계열은 number 배열로 변환.
export const MonteCarloResultSchema = z.object({
  samples: z.number().int(),
  ci_lower_95: decimalString,
  ci_upper_95: decimalString,
  median_final_equity: decimalString,
  max_drawdown_mean: decimalString,
  max_drawdown_p95: decimalString,
  equity_percentiles: z.record(z.string(), z.array(decimalString)),
});
export type MonteCarloResult = z.infer<typeof MonteCarloResultSchema>;

// Walk-Forward fold — oos_sharpe 는 null 허용.
export const WalkForwardFoldSchema = z.object({
  fold_index: z.number().int(),
  train_start: z.iso.datetime({ offset: true }),
  train_end: z.iso.datetime({ offset: true }),
  test_start: z.iso.datetime({ offset: true }),
  test_end: z.iso.datetime({ offset: true }),
  in_sample_return: decimalString,
  out_of_sample_return: decimalString,
  oos_sharpe: decimalString.nullable(),
  num_trades_oos: z.number().int(),
});
export type WalkForwardFold = z.infer<typeof WalkForwardFoldSchema>;

// Walk-Forward result — degradation_ratio 는 문자열 유지 (Decimal or "Infinity").
// UI 는 valid_positive_regime === false 시 "N/A" 로 렌더.
export const WalkForwardResultSchema = z.object({
  folds: z.array(WalkForwardFoldSchema),
  aggregate_oos_return: decimalString,
  degradation_ratio: z.string(),
  valid_positive_regime: z.boolean(),
  total_possible_folds: z.number().int(),
  was_truncated: z.boolean(),
});
export type WalkForwardResult = z.infer<typeof WalkForwardResultSchema>;

// Detail — BE StressTestDetail 을 그대로 미러. `result` 단일 union 대신 kind 별 개별 필드.
export const StressTestDetailSchema = z.object({
  id: z.uuid(),
  backtest_id: z.uuid(),
  kind: StressTestKindSchema,
  status: StressTestStatusSchema,
  params: z.record(z.string(), z.unknown()),
  monte_carlo_result: MonteCarloResultSchema.nullable().optional(),
  walk_forward_result: WalkForwardResultSchema.nullable().optional(),
  error: z.string().nullable().optional(),
  created_at: z.iso.datetime({ offset: true }),
  started_at: z.iso.datetime({ offset: true }).nullable().optional(),
  completed_at: z.iso.datetime({ offset: true }).nullable().optional(),
});
export type StressTestDetail = z.infer<typeof StressTestDetailSchema>;

export const StressTestCreatedResponseSchema = z.object({
  stress_test_id: z.uuid(),
  kind: StressTestKindSchema,
  status: StressTestStatusSchema,
  created_at: z.iso.datetime({ offset: true }),
});
export type StressTestCreatedResponse = z.infer<
  typeof StressTestCreatedResponseSchema
>;

// Requests — BE 는 `{backtest_id, params: {...}}` 중첩 구조.
export const MonteCarloParamsSchema = z.object({
  n_samples: z.number().int().min(10).max(10_000).default(1000),
  seed: z.number().int().min(0).default(42),
});
export type MonteCarloParams = z.infer<typeof MonteCarloParamsSchema>;

export const CreateMonteCarloRequestSchema = z.object({
  backtest_id: z.uuid(),
  params: MonteCarloParamsSchema.default({ n_samples: 1000, seed: 42 }),
});
export type CreateMonteCarloRequest = z.infer<
  typeof CreateMonteCarloRequestSchema
>;

export const WalkForwardParamsSchema = z.object({
  train_bars: z.number().int().min(1),
  test_bars: z.number().int().min(1),
  step_bars: z.number().int().min(1).nullable().optional(),
  max_folds: z.number().int().min(1).max(100).default(20),
});
export type WalkForwardParams = z.infer<typeof WalkForwardParamsSchema>;

export const CreateWalkForwardRequestSchema = z.object({
  backtest_id: z.uuid(),
  params: WalkForwardParamsSchema,
});
export type CreateWalkForwardRequest = z.infer<
  typeof CreateWalkForwardRequestSchema
>;
