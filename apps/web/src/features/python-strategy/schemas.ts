import { z } from "zod/v4";

const JsonScalarSchema = z.union([z.string(), z.number().finite(), z.boolean(), z.null()]);
const ParamsSchema = z.record(z.string(), JsonScalarSchema);
const ParamsJsonSchema = z.string().transform((value, ctx) => {
  try {
    const parsed = ParamsSchema.safeParse(JSON.parse(value));
    if (parsed.success) return parsed.data;
  } catch {
    // 잘못된 JSON과 지원하지 않는 값에 같은 입력 안내를 제공한다.
  }
  ctx.addIssue({
    code: "custom",
    message: "객체 형태의 JSON을 입력하세요. 값은 숫자·문자·참/거짓·null만 지원합니다.",
  });
  return z.NEVER;
});

export const PythonStrategyDraftSchema = z.object({
  name: z.string().trim().min(1, "전략 이름을 입력하세요").max(120),
  source: z
    .string()
    .min(1, "Python 코드를 입력하세요")
    .max(100_000)
    .refine((value) => value.trim().length > 0, "Python 코드를 입력하세요"),
  params_json: z.string().superRefine((value, ctx) => {
    const result = ParamsJsonSchema.safeParse(value);
    if (!result.success)
      ctx.addIssue({
        code: "custom",
        message: result.error.issues[0]?.message ?? "JSON을 확인하세요",
      });
  }),
  warmup_bars: z.coerce.number().int().min(0).max(10_000),
});
export type PythonStrategyDraft = z.infer<typeof PythonStrategyDraftSchema>;

export const PythonStrategyBodySchema = PythonStrategyDraftSchema.transform((draft) => ({
  name: draft.name,
  source: draft.source,
  params: ParamsJsonSchema.parse(draft.params_json),
  warmup_bars: draft.warmup_bars,
}));
export type PythonStrategyBody = z.infer<typeof PythonStrategyBodySchema>;

export const PythonStrategySchema = z.object({
  id: z.uuid(),
  name: z.string(),
  source: z.string(),
  params: ParamsSchema,
  warmup_bars: z.number().int(),
  version_id: z.uuid(),
  source_hash: z.string(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type PythonStrategy = z.infer<typeof PythonStrategySchema>;
export const PythonStrategyListSchema = z.object({ items: z.array(PythonStrategySchema) });
export const PythonCapabilitiesSchema = z.object({
  available: z.boolean(),
  reason: z.string().nullable(),
});

const DecimalSchema = z
  .string()
  .regex(/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/)
  .refine((value) => Number.isFinite(Number(value)), "유한한 숫자를 입력하세요");
const PositiveDecimalSchema = DecimalSchema.refine(
  (value) => Number(value) > 0 && Number(value) <= 1_000_000_000,
  "0보다 크고 1,000,000,000 이하인 값을 입력하세요",
);
const CostSchema = DecimalSchema.refine(
  (value) => Number(value) >= 0 && Number(value) <= 0.01,
  "0~0.01 사이의 비율을 입력하세요",
);

export const PythonBacktestBodySchema = z
  .object({
    expected_version_id: z.uuid().nullish(),
    symbol: z.enum(["BTC/USDT", "ETH/USDT"]),
    timeframe: z.enum(["1h", "4h", "1d"]),
    period_start: z.iso.datetime({ offset: true }),
    period_end: z.iso.datetime({ offset: true }),
    initial_capital: PositiveDecimalSchema,
    fees: CostSchema,
    slippage: CostSchema,
  })
  .refine((body) => Date.parse(body.period_end) > Date.parse(body.period_start), {
    path: ["period_end"],
    message: "종료일은 시작일 이후여야 합니다",
  });
export type PythonBacktestBody = z.infer<typeof PythonBacktestBodySchema>;

export const PythonBacktestDraftSchema = z
  .object({
    symbol: z.enum(["BTC/USDT", "ETH/USDT"]),
    timeframe: z.enum(["1h", "4h", "1d"]),
    period_start: z.iso.date("시작일을 입력하세요"),
    period_end: z.iso.date("종료일을 입력하세요"),
    initial_capital: PositiveDecimalSchema,
    fees: CostSchema,
    slippage: CostSchema,
  })
  .refine((body) => body.period_end > body.period_start, {
    path: ["period_end"],
    message: "종료일은 시작일 이후여야 합니다",
  });
export type PythonBacktestDraft = z.infer<typeof PythonBacktestDraftSchema>;
export const PythonBacktestRequestSchema = PythonBacktestDraftSchema.transform((draft) =>
  PythonBacktestBodySchema.parse({
    ...draft,
    period_start: `${draft.period_start}T00:00:00Z`,
    period_end: `${draft.period_end}T00:00:00Z`,
  }),
);

export const PythonRunStatusSchema = z.enum([
  "pending",
  "running",
  "completed",
  "failed",
  "cancelled",
]);
const MetricSchema = DecimalSchema.nullable();
const TradeSchema = z.object({
  trade_index: z.number().int(),
  direction: z.enum(["long", "short"]),
  status: z.enum(["open", "closed"]),
  entry_bar_index: z.number().int(),
  exit_bar_index: z.number().int().nullable(),
  entry_price: DecimalSchema,
  exit_price: DecimalSchema.nullable(),
  size: DecimalSchema,
  pnl: DecimalSchema,
  return_pct: DecimalSchema,
  fees: DecimalSchema,
});
export const PythonResultSchema = z.object({
  metrics: z.object({
    total_return: MetricSchema,
    max_drawdown: MetricSchema,
    profit_factor: MetricSchema,
    num_trades: z.union([z.number().int(), DecimalSchema]),
    sharpe_ratio: MetricSchema,
    total_fees: MetricSchema,
    total_slippage: MetricSchema,
    total_funding: MetricSchema.optional(),
    sharpe_convention: z.string().nullable().optional(),
  }),
  trades: z.array(TradeSchema),
  equity_curve: z.array(
    z.object({ timestamp: z.iso.datetime({ offset: true }), value: DecimalSchema }),
  ),
  provenance: z.record(z.string(), z.unknown()),
});
export type PythonResult = z.infer<typeof PythonResultSchema>;
export const PythonRunSchema = z.object({
  id: z.uuid(),
  strategy_id: z.uuid(),
  version_id: z.uuid(),
  status: PythonRunStatusSchema,
  request: PythonBacktestBodySchema,
  result: PythonResultSchema.nullable(),
  error: z.string().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  completed_at: z.iso.datetime({ offset: true }).nullable(),
});
export type PythonRun = z.infer<typeof PythonRunSchema>;
export const PythonRunListSchema = z.object({ items: z.array(PythonRunSchema) });
