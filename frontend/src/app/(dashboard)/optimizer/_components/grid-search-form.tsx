// Sprint 54 — Grid Search 제출 form (RHF + Zod, IntegerField/DecimalField row append/remove).
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { z } from "zod/v4";

import { useSubmitGridSearch } from "@/features/optimizer/hooks";
import {
  OptimizationDirectionSchema,
  OptimizationObjectiveMetricSchema,
  type CreateOptimizationRunRequest,
} from "@/features/optimizer/schemas";

// Form-level schema — discriminated union for IntegerField/DecimalField (categorical Sprint 55+).
// var_name + kind + min/max/step 각 row.
const ParameterRowSchema = z.discriminatedUnion("kind", [
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

const FormSchema = z.object({
  backtest_id: z.uuid(),
  objective_metric: OptimizationObjectiveMetricSchema,
  direction: OptimizationDirectionSchema,
  max_evaluations: z.coerce.number().int().min(1).max(9),
  parameters: z.array(ParameterRowSchema).min(1).max(4),
});

type FormValues = z.infer<typeof FormSchema>;

interface Props {
  backtestId: string;
  onSuccess?: (runId: string) => void;
}

export function GridSearchForm({ backtestId, onSuccess }: Props) {
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const submit = useSubmitGridSearch();

  const form = useForm<FormValues>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      backtest_id: backtestId,
      objective_metric: "sharpe_ratio",
      direction: "maximize",
      max_evaluations: 9,
      parameters: [
        { var_name: "", kind: "integer", min: 10, max: 30, step: 5 },
      ],
    },
  });

  const fields = useFieldArray({ control: form.control, name: "parameters" });

  const handleSubmit = form.handleSubmit(async (values) => {
    setErrMsg(null);

    // form rows → ParamSpace parameters dict (var_name → ParamSpaceField).
    const parameters: Record<string, unknown> = {};
    for (const row of values.parameters) {
      if (!row.var_name) continue;
      if (row.kind === "integer") {
        parameters[row.var_name] = {
          kind: "integer",
          min: row.min,
          max: row.max,
          step: row.step,
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
      kind: "grid_search",
      param_space: {
        schema_version: 1,
        objective_metric: values.objective_metric,
        direction: values.direction,
        max_evaluations: values.max_evaluations,
        parameters,
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
          <span className="font-medium">max_evaluations (≤ 9)</span>
          <input
            type="number"
            min={1}
            max={9}
            className="w-full rounded border border-input bg-background px-2 py-1.5"
            {...form.register("max_evaluations", { valueAsNumber: true })}
          />
        </label>
      </div>

      <fieldset className="space-y-2 rounded border border-border p-3">
        <legend className="px-1 text-sm font-medium">Parameters (1~4 변수)</legend>
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
            <div className="flex items-center gap-1">
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
              min: 10,
              max: 20,
              step: 5,
            })
          }
          disabled={fields.fields.length >= 4}
          className="rounded border border-input bg-background px-3 py-1 text-sm hover:bg-muted disabled:opacity-50"
        >
          + parameter 추가
        </button>
      </fieldset>

      {errMsg && (
        <div role="alert" className="rounded border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
          {errMsg}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={submit.isPending}
          className="rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {submit.isPending ? "제출 중…" : "Grid Search 제출"}
        </button>
        <p className="text-xs text-muted-foreground">
          서버 9 cell 강제 제한 — 변수별 expansion 결과 cardinality 곱 ≤ 9.
        </p>
      </div>
    </form>
  );
}
