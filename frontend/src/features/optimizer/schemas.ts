// Optimizer 도메인 Zod schemas (Sprint 55 schema_version=2 + Bayesian discriminated union).
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

export const OptimizationKindSchema = z.enum([
  "grid_search",
  "bayesian",
  "genetic",
]);
export type OptimizationKind = z.infer<typeof OptimizationKindSchema>;

export const BayesianAcquisitionSchema = z.enum(["EI", "UCB", "PI"]);
export type BayesianAcquisition = z.infer<typeof BayesianAcquisitionSchema>;

export const BayesianPriorSchema = z.enum(["uniform", "log_uniform", "normal"]);
export type BayesianPrior = z.infer<typeof BayesianPriorSchema>;

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
  // Sprint 57 BL-234: one_hot encoding 활성 (Bayesian skopt transform="onehot").
  encoding: z.enum(["label", "one_hot"]).default("label"),
});

// Sprint 55 ADR-013 §2.1 — Bayesian executor 의 sample space field.
export const BayesianHyperparamsFieldSchema = z
  .object({
    kind: z.literal("bayesian"),
    min: strictDecimalInput,
    max: strictDecimalInput,
    prior: BayesianPriorSchema.default("uniform"),
    log_scale: z.boolean().default(false),
  })
  .superRefine((field, ctx) => {
    const minN = Number(field.min);
    const maxN = Number(field.max);
    if (minN >= maxN) {
      ctx.addIssue({
        code: "custom",
        message: `BayesianHyperparamsField.min must be < max (got ${field.min} / ${field.max})`,
      });
    }
    if ((field.log_scale || field.prior === "log_uniform") && minN <= 0) {
      ctx.addIssue({
        code: "custom",
        message:
          "log_scale=true / prior='log_uniform' requires min > 0 (ADR-013 §2.5)",
      });
    }
    // Sprint 57 BL-234 E1: prior=normal + log_scale=true 조합 미지원.
    if (field.prior === "normal" && field.log_scale) {
      ctx.addIssue({
        code: "custom",
        message:
          "prior='normal' with log_scale=true is not supported; use prior='log_uniform' for log-scale parameters",
      });
    }
  });

export const ParamSpaceFieldSchema = z.discriminatedUnion("kind", [
  IntegerFieldSchema,
  DecimalFieldSchema,
  CategoricalFieldSchema,
  BayesianHyperparamsFieldSchema,
]);
export type ParamSpaceField = z.infer<typeof ParamSpaceFieldSchema>;

// --- ParamSpace -------------------------------------------------------------

export const ParamSpaceSchema = z
  .object({
    // Sprint 55 = schema_version Literal[1, 2]. v1 = Grid Search MVP, v2 = Bayesian + Genetic reservation.
    schema_version: z.union([z.literal(1), z.literal(2)]).default(1),
    objective_metric: OptimizationObjectiveMetricSchema,
    direction: OptimizationDirectionSchema,
    max_evaluations: z.number().int().positive(),
    parameters: z.record(z.string().min(1), ParamSpaceFieldSchema),
    // Sprint 55 = Bayesian 활성 2 필드 (schema_version=2 only).
    bayesian_n_initial_random: z.number().int().min(1).max(100).optional(), // BL-237: 50→100
    bayesian_acquisition: BayesianAcquisitionSchema.optional(),
    // Sprint 56 = Genetic 4 hyperparam 활성 (ADR-013 §7 amendment, schema_version=2 only).
    population_size: z.number().int().min(2).max(200).optional(),
    n_generations: z.number().int().min(1).max(100).optional(),
    mutation_rate: strictDecimalInput.optional(),
    crossover_rate: strictDecimalInput.optional(),
    // Sprint 57 BL-234 = selection algorithm enum (null → engine default "tournament").
    genetic_selection_method: z
      .enum(["tournament", "roulette"])
      .nullable()
      .default(null),
  })
  .superRefine((space, ctx) => {
    const v2OnlyEntries: Array<[string, unknown]> = [
      ["bayesian_n_initial_random", space.bayesian_n_initial_random],
      ["bayesian_acquisition", space.bayesian_acquisition],
      ["population_size", space.population_size],
      ["n_generations", space.n_generations],
      ["mutation_rate", space.mutation_rate],
      ["crossover_rate", space.crossover_rate],
      ["genetic_selection_method", space.genetic_selection_method],
    ];
    const populated = v2OnlyEntries
      .filter(([, v]) => v !== undefined)
      .map(([k]) => k);
    const hasBayesian = Object.values(space.parameters).some(
      (p) => p.kind === "bayesian",
    );

    if (space.schema_version === 1) {
      if (populated.length > 0) {
        ctx.addIssue({
          code: "custom",
          message: `schema_version=1 forbids v2-only fields: ${populated.sort().join(", ")}`,
        });
      }
      if (hasBayesian) {
        ctx.addIssue({
          code: "custom",
          message:
            "schema_version=1 forbids BayesianHyperparamsField; set schema_version=2",
        });
      }
    }
    if (hasBayesian && space.schema_version !== 2) {
      ctx.addIssue({
        code: "custom",
        message:
          "BayesianHyperparamsField requires schema_version=2 (ADR-013 §2.2)",
      });
    }

    // Sprint 56 ADR-013 §7 amendment — mutation_rate / crossover_rate ∈ (0, 1].
    const mutN =
      space.mutation_rate !== undefined ? Number(space.mutation_rate) : null;
    if (mutN !== null && !(mutN > 0 && mutN <= 1)) {
      ctx.addIssue({
        code: "custom",
        message: `mutation_rate must be in (0, 1] (got ${space.mutation_rate})`,
      });
    }
    const crossN =
      space.crossover_rate !== undefined ? Number(space.crossover_rate) : null;
    if (crossN !== null && !(crossN > 0 && crossN <= 1)) {
      ctx.addIssue({
        code: "custom",
        message: `crossover_rate must be in (0, 1] (got ${space.crossover_rate})`,
      });
    }
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

// Sprint 55 = top-level kind/schema_version echo (FE z.discriminatedUnion 의무).
export const GridSearchResultSchema = z.object({
  schema_version: z.literal(1),
  kind: z.literal("grid_search"),
  param_names: z.array(z.string()),
  param_values: z.record(z.string(), z.array(decimalString)),
  cells: z.array(GridSearchCellSchema),
  objective_metric: OptimizationObjectiveMetricSchema,
  direction: OptimizationDirectionSchema,
  best_cell_index: z.number().int().nullable(),
});
export type GridSearchResult = z.infer<typeof GridSearchResultSchema>;

// --- Response — Bayesian result_jsonb shape (Sprint 55 신규) ----------------

export const BayesianIterationSchema = z.object({
  idx: z.number().int().nonnegative(),
  params: z.record(z.string(), decimalString),
  objective_value: decimalString.nullable(),
  best_so_far: decimalString.nullable(),
  is_degenerate: z.boolean(),
  phase: z.enum(["random", "acquisition"]),
});
export type BayesianIteration = z.infer<typeof BayesianIterationSchema>;

export const BayesianSearchResultSchema = z.object({
  schema_version: z.literal(2),
  kind: z.literal("bayesian"),
  param_names: z.array(z.string()),
  iterations: z.array(BayesianIterationSchema),
  best_params: z.record(z.string(), decimalString).nullable(),
  best_objective_value: decimalString.nullable(),
  best_iteration_idx: z.number().int().nullable(),
  objective_metric: OptimizationObjectiveMetricSchema,
  direction: OptimizationDirectionSchema,
  bayesian_acquisition: BayesianAcquisitionSchema,
  bayesian_n_initial_random: z.number().int(),
  max_evaluations: z.number().int(),
  degenerate_count: z.number().int(),
  total_iterations: z.number().int(),
});
export type BayesianSearchResult = z.infer<typeof BayesianSearchResultSchema>;

// --- Response — Genetic result_jsonb shape (Sprint 56 BL-233) ---------------

export const GeneticIterationSchema = z.object({
  idx: z.number().int().nonnegative(),
  params: z.record(z.string(), decimalString),
  objective_value: decimalString.nullable(),
  best_so_far: decimalString.nullable(),
  is_degenerate: z.boolean(),
  generation: z.number().int().nonnegative(),
});
export type GeneticIteration = z.infer<typeof GeneticIterationSchema>;

export const GeneticSearchResultSchema = z.object({
  schema_version: z.literal(2),
  kind: z.literal("genetic"),
  param_names: z.array(z.string()),
  iterations: z.array(GeneticIterationSchema),
  best_params: z.record(z.string(), decimalString).nullable(),
  best_objective_value: decimalString.nullable(),
  best_iteration_idx: z.number().int().nullable(),
  objective_metric: OptimizationObjectiveMetricSchema,
  direction: OptimizationDirectionSchema,
  population_size: z.number().int(),
  n_generations: z.number().int(),
  mutation_rate: decimalString,
  crossover_rate: decimalString,
  max_evaluations: z.number().int(),
  degenerate_count: z.number().int(),
  total_iterations: z.number().int(),
});
export type GeneticSearchResult = z.infer<typeof GeneticSearchResultSchema>;

// --- OptimizationRun detail — discriminated union by result.kind ------------

export const OptimizationResultSchema = z.discriminatedUnion("kind", [
  GridSearchResultSchema,
  BayesianSearchResultSchema,
  GeneticSearchResultSchema,
]);
export type OptimizationResult = z.infer<typeof OptimizationResultSchema>;

// OptimizationRun detail — BE OptimizationRunResponse mirror.
export const OptimizationRunResponseSchema = z.object({
  id: z.uuid(),
  user_id: z.uuid(),
  backtest_id: z.uuid(),
  kind: OptimizationKindSchema,
  status: OptimizationStatusSchema,
  param_space: ParamSpaceSchema,
  // result 는 BE 가 dict | None. COMPLETED 시 GridSearch | Bayesian shape (kind discriminator).
  result: OptimizationResultSchema.nullable().optional(),
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
