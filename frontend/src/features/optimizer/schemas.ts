// Optimizer 도메인 Zod schemas (Sprint 54 Phase 3 BE schemas.py 1:1 mirror).
// BE Decimal → str 직렬화 (json_encoders={Decimal: str}) → FE decimalString helper 변환.

import { z } from "zod/v4";

// --- Decimal 문자열 → finite number 변환 (backtest schemas.ts 패턴 mirror) -----

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

// --- StrictDecimalInput parity (BL-226 / BL-229) ----------------------------
// BE _STRICT_DECIMAL_RE = ^-?\d+(\.\d+)?$ + Number.isFinite(Number(s)).
// FE 요청 시점에 동일 검증.

const STRICT_DECIMAL_RE = /^-?\d+(\.\d+)?$/;

const strictDecimalInput = z
  .string()
  .refine((s) => STRICT_DECIMAL_RE.test(s), {
    message: "decimal string must match ^-?\\d+(\\.\\d+)?$ (no exponent / NaN / empty)",
  })
  .refine((s) => Number.isFinite(Number(s)), {
    message: "decimal string must be finite when converted to JavaScript Number (BL-226 parity)",
  });

// --- Enums ------------------------------------------------------------------

export const OptimizationKindSchema = z.enum(["grid_search"]);
export type OptimizationKind = z.infer<typeof OptimizationKindSchema>;

export const OptimizationStatusSchema = z.enum([
  "queued",
  "running",
  "completed",
  "failed",
]);
export type OptimizationStatus = z.infer<typeof OptimizationStatusSchema>;

export const OptimizationDirectionSchema = z.enum(["maximize", "minimize"]);
export type OptimizationDirection = z.infer<typeof OptimizationDirectionSchema>;

// Sprint 54 MVP whitelist — BE _SUPPORTED_OBJECTIVE_METRICS 와 정확 일치.
export const OptimizationObjectiveMetricSchema = z.enum([
  "sharpe_ratio",
  "total_return",
  "max_drawdown",
]);
export type OptimizationObjectiveMetric = z.infer<
  typeof OptimizationObjectiveMetricSchema
>;

// --- ParamSpaceField discriminated union ------------------------------------

export const IntegerFieldSchema = z.object({
  kind: z.literal("integer"),
  min: z.number().int(),
  max: z.number().int(),
  step: z.number().int().min(1).default(1),
});

export const DecimalFieldSchema = z.object({
  kind: z.literal("decimal"),
  min: strictDecimalInput,
  max: strictDecimalInput,
  step: strictDecimalInput,
});

export const CategoricalFieldSchema = z.object({
  kind: z.literal("categorical"),
  values: z.array(z.string()).min(1),
});

export const ParamSpaceFieldSchema = z.discriminatedUnion("kind", [
  IntegerFieldSchema,
  DecimalFieldSchema,
  CategoricalFieldSchema,
]);
export type ParamSpaceField = z.infer<typeof ParamSpaceFieldSchema>;

// --- ParamSpace -------------------------------------------------------------

export const ParamSpaceSchema = z.object({
  schema_version: z.literal(1).default(1),
  objective_metric: OptimizationObjectiveMetricSchema,
  direction: OptimizationDirectionSchema,
  max_evaluations: z.number().int().positive(),
  parameters: z.record(z.string().min(1), ParamSpaceFieldSchema),
});
export type ParamSpace = z.infer<typeof ParamSpaceSchema>;

// --- Request ----------------------------------------------------------------

export const CreateOptimizationRunRequestSchema = z.object({
  backtest_id: z.uuid(),
  kind: OptimizationKindSchema,
  param_space: ParamSpaceSchema,
});
export type CreateOptimizationRunRequest = z.infer<
  typeof CreateOptimizationRunRequestSchema
>;

// --- Response — GridSearch result_jsonb shape -------------------------------

export const GridSearchCellSchema = z.object({
  param_values: z.record(z.string(), decimalString),
  sharpe: decimalString.nullable(),
  total_return: decimalString,
  max_drawdown: decimalString,
  num_trades: z.number().int(),
  is_degenerate: z.boolean(),
  objective_value: decimalString.nullable(),
});
export type GridSearchCell = z.infer<typeof GridSearchCellSchema>;

export const GridSearchResultSchema = z.object({
  param_names: z.array(z.string()),
  param_values: z.record(z.string(), z.array(decimalString)),
  cells: z.array(GridSearchCellSchema),
  objective_metric: OptimizationObjectiveMetricSchema,
  direction: OptimizationDirectionSchema,
  best_cell_index: z.number().int().nullable(),
});
export type GridSearchResult = z.infer<typeof GridSearchResultSchema>;

// OptimizationRun detail — BE OptimizationRunResponse mirror.
export const OptimizationRunResponseSchema = z.object({
  id: z.uuid(),
  user_id: z.uuid(),
  backtest_id: z.uuid(),
  kind: OptimizationKindSchema,
  status: OptimizationStatusSchema,
  param_space: ParamSpaceSchema,
  // result 는 BE 가 dict | None. COMPLETED 시 GridSearchResult shape.
  result: GridSearchResultSchema.nullable().optional(),
  error_message: z.string().nullable().optional(),
  created_at: z.iso.datetime({ offset: true }),
  started_at: z.iso.datetime({ offset: true }).nullable().optional(),
  completed_at: z.iso.datetime({ offset: true }).nullable().optional(),
});
export type OptimizationRunResponse = z.infer<typeof OptimizationRunResponseSchema>;

// Pagination — common Page<T> shape.
export const OptimizationRunListResponseSchema = z.object({
  items: z.array(OptimizationRunResponseSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});
export type OptimizationRunListResponse = z.infer<
  typeof OptimizationRunListResponseSchema
>;
