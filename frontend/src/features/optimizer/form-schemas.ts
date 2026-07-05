// Optimizer 제출 폼(grid/bayesian/genetic) 공용 form-level zod 조각 + row→wire 매핑.
// wire-shape SSOT 는 schemas.ts — 여기는 입력 단계(string 위주) 스키마만 둔다.

import { z } from "zod/v4";

import {
  BayesianPriorSchema,
  CreateOptimizationRunRequestSchema,
  OptimizationDirectionSchema,
  OptimizationObjectiveMetricSchema,
  type CreateOptimizationRunRequest,
  type OptimizationKind,
} from "./schemas";

// ── base 필드 조각 ─────────────────────────────────────────────────────────

/** 3폼 공통 헤더 필드 — max_evaluations 상한만 알고리즘별로 다르다. */
export function makeOptimizerFormBaseFields(maxEvaluations: number) {
  return {
    backtest_id: z.uuid(),
    objective_metric: OptimizationObjectiveMetricSchema,
    direction: OptimizationDirectionSchema,
    max_evaluations: z.coerce.number().int().min(1).max(maxEvaluations),
  };
}

export interface OptimizerFormBaseValues {
  backtest_id: string;
  objective_metric: z.infer<typeof OptimizationObjectiveMetricSchema>;
  direction: z.infer<typeof OptimizationDirectionSchema>;
  max_evaluations: number;
}

// ── row 스키마 (알고리즘별 구조가 달라 통합하지 않는다) ────────────────────

/** Grid — IntegerField/DecimalField discriminated union (integer 만 숫자 coerce). */
export const GridParameterRowSchema = z.discriminatedUnion("kind", [
  z.object({
    var_name: z.string().min(1, "var_name required"),
    kind: z.literal("integer"),
    min: z.coerce.number().int(),
    max: z.coerce.number().int(),
    step: z.coerce.number().int().min(1).default(1),
  }),
  z.object({
    var_name: z.string().min(1, "var_name required"),
    kind: z.literal("decimal"),
    min: z.string().min(1, "min required"),
    max: z.string().min(1, "max required"),
    step: z.string().min(1, "step required"),
  }),
]);
export type GridParameterRow = z.infer<typeof GridParameterRowSchema>;

/** Bayesian — min/max 문자열 + prior/log_scale, min<max·log 시 min>0 검증. */
export const BayesianRowSchema = z
  .object({
    var_name: z.string().min(1, "var_name required"),
    min: z.string().min(1, "min required"),
    max: z.string().min(1, "max required"),
    prior: BayesianPriorSchema.default("uniform"),
    log_scale: z.boolean().default(false),
  })
  .superRefine((row, ctx) => {
    const minN = Number(row.min);
    const maxN = Number(row.max);
    if (Number.isFinite(minN) && Number.isFinite(maxN) && minN >= maxN) {
      ctx.addIssue({
        code: "custom",
        path: ["max"],
        message: `min < max 강제 (got ${row.min} / ${row.max})`,
      });
    }
    if ((row.log_scale || row.prior === "log_uniform") && minN <= 0) {
      ctx.addIssue({
        code: "custom",
        path: ["min"],
        message: "log_scale / log_uniform 은 min > 0 필요",
      });
    }
  });
export type BayesianRow = z.infer<typeof BayesianRowSchema>;

/** Genetic — kind+min/max/step 전부 문자열 입력, min<=max 검증. */
export const GeneticRowSchema = z
  .object({
    var_name: z.string().min(1, "var_name required"),
    kind: z.enum(["integer", "decimal"]).default("integer"),
    min: z.string().min(1, "min required"),
    max: z.string().min(1, "max required"),
    step: z.string().min(1, "step required"),
  })
  .superRefine((row, ctx) => {
    const minN = Number(row.min);
    const maxN = Number(row.max);
    if (Number.isFinite(minN) && Number.isFinite(maxN) && minN > maxN) {
      ctx.addIssue({
        code: "custom",
        path: ["max"],
        message: `min <= max 강제 (got ${row.min} / ${row.max})`,
      });
    }
  });
export type GeneticRow = z.infer<typeof GeneticRowSchema>;

/** 3폼 공통 parameters 배열 제약 (1~4개). */
export function makeParametersArraySchema<TRow extends z.ZodType>(row: TRow) {
  return z.array(row).min(1).max(4);
}

// ── row → wire 매핑 ────────────────────────────────────────────────────────

/** rows → ParamSpace parameters dict. 빈 var_name row 는 skip (기존 동작 유지). */
export function rowsToParameters<TRow extends { var_name: string }>(
  rows: readonly TRow[],
  toField: (row: TRow) => Record<string, unknown>,
): Record<string, unknown> {
  const parameters: Record<string, unknown> = {};
  for (const row of rows) {
    if (!row.var_name) continue;
    parameters[row.var_name] = toField(row);
  }
  return parameters;
}

/**
 * base + parameters + 알고리즘 고유 extras → CreateOptimizationRunRequest.
 * 무검증 `as` 캐스트 대신 request 스키마로 런타임 검증 — 형 불일치는 제출 전에
 * throw 로 드러난다(호출측 useOptimizerSubmit 의 catch 가 사용자 메시지로 변환).
 * 단, 전송은 원본 객체 그대로 — parse 산출물을 쓰면 스키마 default(null 등)가
 * 주입되어 wire-shape 이 바뀐다(characterization 고정 위반).
 */
export function buildCreateRunBody(opts: {
  kind: OptimizationKind;
  schemaVersion: 1 | 2;
  base: OptimizerFormBaseValues;
  parameters: Record<string, unknown>;
  extras?: Record<string, unknown>;
}): CreateOptimizationRunRequest {
  const body = {
    backtest_id: opts.base.backtest_id,
    kind: opts.kind,
    param_space: {
      schema_version: opts.schemaVersion,
      objective_metric: opts.base.objective_metric,
      direction: opts.base.direction,
      max_evaluations: opts.base.max_evaluations,
      parameters: opts.parameters,
      ...opts.extras,
    },
  };
  const checked = CreateOptimizationRunRequestSchema.safeParse(body);
  if (!checked.success) {
    throw checked.error;
  }
  return body as CreateOptimizationRunRequest;
}
