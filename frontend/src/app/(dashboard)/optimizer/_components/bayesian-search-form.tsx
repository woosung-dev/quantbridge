// Sprint 55 — Bayesian Search 제출 form (RHF + Zod, BayesianHyperparamsField row append/remove).
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { z } from "zod/v4";

import { useSubmitBayesianSearch } from "@/features/optimizer/hooks";
import {
  BayesianAcquisitionSchema,
  BayesianPriorSchema,
  OptimizationDirectionSchema,
  OptimizationObjectiveMetricSchema,
  type CreateOptimizationRunRequest,
} from "@/features/optimizer/schemas";

// Form-level schema — Bayesian field row (var_name + min/max + prior + log_scale).
const BayesianRowSchema = z
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
        message: "log_scale / log_uniform requires min > 0 (ADR-013 §2.5)",
      });
    }
  });

const FormSchema = z.object({
  backtest_id: z.uuid(),
  objective_metric: OptimizationObjectiveMetricSchema,
  direction: OptimizationDirectionSchema,
  max_evaluations: z.coerce.number().int().min(1).max(50),
  bayesian_n_initial_random: z.coerce.number().int().min(1).max(50),
  bayesian_acquisition: BayesianAcquisitionSchema,
  parameters: z.array(BayesianRowSchema).min(1).max(4),
});

type FormValues = z.infer<typeof FormSchema>;

interface Props {
  backtestId: string;
  onSuccess?: (runId: string) => void;
}

export function BayesianSearchForm({ backtestId, onSuccess }: Props) {
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const submit = useSubmitBayesianSearch();

  const form = useForm<FormValues>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      backtest_id: backtestId,
      objective_metric: "sharpe_ratio",
      direction: "maximize",
      max_evaluations: 15,
      bayesian_n_initial_random: 5,
      bayesian_acquisition: "EI",
      parameters: [
        {
          var_name: "",
          min: "5",
          max: "30",
          prior: "uniform",
          log_scale: false,
        },
      ],
    },
  });

  const fields = useFieldArray({ control: form.control, name: "parameters" });

  const handleSubmit = form.handleSubmit(async (values) => {
    setErrMsg(null);

    if (values.bayesian_n_initial_random > values.max_evaluations) {
      setErrMsg(
        `bayesian_n_initial_random (${values.bayesian_n_initial_random}) ≤ max_evaluations (${values.max_evaluations}) 강제`,
      );
      return;
    }

    const parameters: Record<string, unknown> = {};
    for (const row of values.parameters) {
      if (!row.var_name) continue;
      parameters[row.var_name] = {
        kind: "bayesian",
        min: row.min,
        max: row.max,
        prior: row.prior,
        log_scale: row.log_scale,
      };
    }

    const body: CreateOptimizationRunRequest = {
      backtest_id: values.backtest_id,
      kind: "bayesian",
      param_space: {
        schema_version: 2,
        objective_metric: values.objective_metric,
        direction: values.direction,
        max_evaluations: values.max_evaluations,
        parameters,
        bayesian_n_initial_random: values.bayesian_n_initial_random,
        bayesian_acquisition: values.bayesian_acquisition,
      } as CreateOptimizationRunRequest["param_space"],
    };

    try {
      const created = await submit.mutateAsync(body);
      onSuccess?.(created.id);
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : String(e));
    }
  });

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <label className="space-y-1 text-sm">
          <span className="font-medium">objective_metric</span>
          <select
            className="w-full rounded border border-input bg-background px-2 py-1.5"
            {...form.register("objective_metric")}
          >
            <option value="sharpe_ratio">sharpe_ratio</option>
            <option value="total_return">total_return</option>
            <option value="max_drawdown">max_drawdown</option>
          </select>
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">direction</span>
          <select
            className="w-full rounded border border-input bg-background px-2 py-1.5"
            {...form.register("direction")}
          >
            <option value="maximize">maximize</option>
            <option value="minimize">minimize</option>
          </select>
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">max_evaluations (≤ 50)</span>
          <input
            type="number"
            min={1}
            max={50}
            className="w-full rounded border border-input bg-background px-2 py-1.5"
            {...form.register("max_evaluations", { valueAsNumber: true })}
          />
        </label>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <label className="space-y-1 text-sm">
          <span className="font-medium">bayesian_n_initial_random (random warm-up)</span>
          <input
            type="number"
            min={1}
            max={50}
            className="w-full rounded border border-input bg-background px-2 py-1.5"
            {...form.register("bayesian_n_initial_random", { valueAsNumber: true })}
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">acquisition function</span>
          <select
            className="w-full rounded border border-input bg-background px-2 py-1.5"
            {...form.register("bayesian_acquisition")}
          >
            <option value="EI">EI (Expected Improvement)</option>
            <option value="UCB">UCB (Upper Confidence Bound)</option>
            <option value="PI">PI (Probability of Improvement)</option>
          </select>
        </label>
      </div>

      <fieldset className="space-y-2 rounded border border-border p-3">
        <legend className="px-1 text-sm font-medium">
          Parameters (1~4 변수, prior=normal Sprint 56+ BL-234 이연)
        </legend>
        {fields.fields.map((field, idx) => (
          <div
            key={field.id}
            className="grid grid-cols-1 gap-2 rounded bg-muted/30 p-2 sm:grid-cols-6"
          >
            <input
              placeholder="var_name (pine input)"
              className="rounded border border-input bg-background px-2 py-1 text-sm sm:col-span-2"
              {...form.register(`parameters.${idx}.var_name`)}
            />
            <input
              placeholder="min"
              className="rounded border border-input bg-background px-2 py-1 text-sm"
              {...form.register(`parameters.${idx}.min`)}
            />
            <input
              placeholder="max"
              className="rounded border border-input bg-background px-2 py-1 text-sm"
              {...form.register(`parameters.${idx}.max`)}
            />
            <select
              className="rounded border border-input bg-background px-2 py-1 text-sm"
              {...form.register(`parameters.${idx}.prior`)}
            >
              <option value="uniform">uniform</option>
              <option value="log_uniform">log_uniform (min &gt; 0)</option>
              <option value="normal" disabled>
                normal (Sprint 56+)
              </option>
            </select>
            <div className="flex items-center justify-between gap-1">
              <label className="flex items-center gap-1 text-xs">
                <input
                  type="checkbox"
                  {...form.register(`parameters.${idx}.log_scale`)}
                />
                log_scale
              </label>
              <button
                type="button"
                onClick={() => fields.remove(idx)}
                aria-label="remove parameter"
                className="rounded border border-input bg-background px-2 py-1 text-xs hover:bg-muted"
              >
                ✕
              </button>
            </div>
          </div>
        ))}
        <button
          type="button"
          onClick={() =>
            fields.append({
              var_name: "",
              min: "5",
              max: "30",
              prior: "uniform",
              log_scale: false,
            })
          }
          disabled={fields.fields.length >= 4}
          className="rounded border border-input bg-background px-3 py-1 text-sm hover:bg-muted disabled:opacity-50"
        >
          + parameter 추가
        </button>
      </fieldset>

      {errMsg && (
        <div
          role="alert"
          className="rounded border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
        >
          {errMsg}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={submit.isPending}
          className="rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {submit.isPending ? "제출 중…" : "Bayesian 제출"}
        </button>
        <p className="text-xs text-muted-foreground">
          서버 50 evaluation 강제 상한 (BL-237 Sprint 56+ = dedicated queue 활성).
          random warm-up 후 acquisition phase 진입.
        </p>
      </div>
    </form>
  );
}
