// Sprint 56 BL-233 — Genetic Search 제출 form (Bayesian form 1:1 mirror, 4 hyperparam).
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { z } from "zod/v4";

import { useSubmitGeneticSearch } from "@/features/optimizer/hooks";
import {
  OptimizationDirectionSchema,
  OptimizationObjectiveMetricSchema,
  type CreateOptimizationRunRequest,
} from "@/features/optimizer/schemas";

// Form-level schema — Genetic 은 variable level distribution 차이 없음.
// IntegerField / DecimalField / CategoricalField 재사용 (kind discriminator).
const GeneticRowSchema = z
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

const FormSchema = z
  .object({
    backtest_id: z.uuid(),
    objective_metric: OptimizationObjectiveMetricSchema,
    direction: OptimizationDirectionSchema,
    max_evaluations: z.coerce.number().int().min(1).max(100), // BL-237: 50→100
    population_size: z.coerce.number().int().min(2).max(200),
    n_generations: z.coerce.number().int().min(1).max(100),
    mutation_rate: z.string().min(1, "mutation_rate required"),
    crossover_rate: z.string().min(1, "crossover_rate required"),
    // Sprint 57 BL-234: roulette selection method enum.
    genetic_selection_method: z
      .enum(["tournament", "roulette"])
      .default("tournament"),
    parameters: z.array(GeneticRowSchema).min(1).max(4),
  })
  .superRefine((values, ctx) => {
    const mutN = Number(values.mutation_rate);
    const crossN = Number(values.crossover_rate);
    if (!(mutN > 0 && mutN <= 1)) {
      ctx.addIssue({
        code: "custom",
        path: ["mutation_rate"],
        message: "mutation_rate must be in (0, 1]",
      });
    }
    if (!(crossN > 0 && crossN <= 1)) {
      ctx.addIssue({
        code: "custom",
        path: ["crossover_rate"],
        message: "crossover_rate must be in (0, 1]",
      });
    }
    // budget = pop * (gen + 1) <= max_evaluations <= 100 (BL-237).
    const budget = values.population_size * (values.n_generations + 1);
    if (budget > values.max_evaluations) {
      ctx.addIssue({
        code: "custom",
        path: ["max_evaluations"],
        message: `evaluation budget ${budget} > max_evaluations ${values.max_evaluations} (population_size × (n_generations + 1)).`,
      });
    }
    if (budget > 100) {
      ctx.addIssue({
        code: "custom",
        path: ["population_size"],
        message: `evaluation budget ${budget} > 100 server cap.`,
      });
    }
  });

type FormValues = z.infer<typeof FormSchema>;

interface Props {
  backtestId: string;
  onSuccess?: (runId: string) => void;
}

export function GeneticSearchForm({ backtestId, onSuccess }: Props) {
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const submit = useSubmitGeneticSearch();

  const form = useForm<FormValues>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      backtest_id: backtestId,
      objective_metric: "sharpe_ratio",
      direction: "maximize",
      max_evaluations: 25,
      population_size: 5,
      n_generations: 4,
      mutation_rate: "0.2",
      crossover_rate: "0.8",
      genetic_selection_method: "tournament" as const,
      parameters: [
        {
          var_name: "",
          kind: "integer",
          min: "5",
          max: "30",
          step: "1",
        },
      ],
    },
  });

  const fields = useFieldArray({ control: form.control, name: "parameters" });

  const handleSubmit = form.handleSubmit(async (values) => {
    setErrMsg(null);

    const parameters: Record<string, unknown> = {};
    for (const row of values.parameters) {
      if (!row.var_name) continue;
      if (row.kind === "integer") {
        parameters[row.var_name] = {
          kind: "integer",
          min: Number.parseInt(row.min, 10),
          max: Number.parseInt(row.max, 10),
          step: Number.parseInt(row.step, 10),
        };
      } else {
        parameters[row.var_name] = {
          kind: "decimal",
          min: row.min,
          max: row.max,
          step: row.step,
        };
      }
    }

    const body: CreateOptimizationRunRequest = {
      backtest_id: values.backtest_id,
      kind: "genetic",
      param_space: {
        schema_version: 2,
        objective_metric: values.objective_metric,
        direction: values.direction,
        max_evaluations: values.max_evaluations,
        parameters,
        population_size: values.population_size,
        n_generations: values.n_generations,
        mutation_rate: values.mutation_rate,
        crossover_rate: values.crossover_rate,
        genetic_selection_method: values.genetic_selection_method,
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
          <span className="font-medium">max_evaluations (≤ 100)</span>
          <input
            type="number"
            min={1}
            max={100}
            className="w-full rounded border border-input bg-background px-2 py-1.5"
            {...form.register("max_evaluations", { valueAsNumber: true })}
          />
        </label>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <label className="space-y-1 text-sm">
          <span className="font-medium">population_size</span>
          <input
            type="number"
            min={2}
            max={200}
            className="w-full rounded border border-input bg-background px-2 py-1.5"
            {...form.register("population_size", { valueAsNumber: true })}
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">n_generations</span>
          <input
            type="number"
            min={1}
            max={100}
            className="w-full rounded border border-input bg-background px-2 py-1.5"
            {...form.register("n_generations", { valueAsNumber: true })}
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">mutation_rate</span>
          <input
            type="text"
            placeholder="0.2"
            className="w-full rounded border border-input bg-background px-2 py-1.5"
            {...form.register("mutation_rate")}
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">crossover_rate</span>
          <input
            type="text"
            placeholder="0.8"
            className="w-full rounded border border-input bg-background px-2 py-1.5"
            {...form.register("crossover_rate")}
          />
        </label>
      </div>

      {/* Sprint 57 BL-234: selection method */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <label className="space-y-1 text-sm">
          <span className="font-medium">selection_method</span>
          <select
            className="w-full rounded border border-input bg-background px-2 py-1.5"
            {...form.register("genetic_selection_method")}
          >
            <option value="tournament">Tournament (k=3)</option>
            <option value="roulette">Roulette (rank-based)</option>
          </select>
        </label>
      </div>

      <fieldset className="space-y-2 rounded border border-border p-3">
        <legend className="px-1 text-sm font-medium">
          Parameters (1~4 변수, GA = uniform sampling + gaussian mutation)
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
            <select
              className="rounded border border-input bg-background px-2 py-1 text-sm"
              {...form.register(`parameters.${idx}.kind`)}
            >
              <option value="integer">integer</option>
              <option value="decimal">decimal</option>
            </select>
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
            <div className="flex items-center justify-between gap-1">
              <input
                placeholder="step"
                className="w-full rounded border border-input bg-background px-2 py-1 text-sm"
                {...form.register(`parameters.${idx}.step`)}
              />
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
              kind: "integer",
              min: "5",
              max: "30",
              step: "1",
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
          {submit.isPending ? "제출 중…" : "Genetic 제출"}
        </button>
        <p className="text-xs text-muted-foreground">
          서버 100 evaluation budget = population_size × (n_generations + 1) 상한.
          tournament size=3 + single-point crossover + gaussian mutation.
        </p>
      </div>
    </form>
  );
}
