// Sprint 56 BL-233 — Genetic Search 제출 form (Bayesian form 1:1 mirror, 4 hyperparam).
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, X } from "lucide-react";
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

const FIELD_CLS =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

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
      // raw 백엔드 에러를 그대로 노출하지 않음 (내부 용어 유출 차단) — 콘솔에만 기술 상세.
      console.error("genetic search submit failed", e);
      setErrMsg(
        "최적화 실행에 실패했습니다. 입력값을 확인하거나 잠시 후 다시 시도해 주세요.",
      );
    }
  });

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <label className="space-y-1.5 text-sm">
          <span className="font-medium text-foreground">목표 지표</span>
          <select className={FIELD_CLS} {...form.register("objective_metric")}>
            <option value="sharpe_ratio">샤프 비율</option>
            <option value="total_return">총 수익률</option>
            <option value="max_drawdown">최대 낙폭</option>
          </select>
        </label>
        <label className="space-y-1.5 text-sm">
          <span className="font-medium text-foreground">최적화 방향</span>
          <select className={FIELD_CLS} {...form.register("direction")}>
            <option value="maximize">최대화</option>
            <option value="minimize">최소화</option>
          </select>
        </label>
        <label className="space-y-1.5 text-sm">
          <span className="font-medium text-foreground">최대 평가 횟수 (≤ 100)</span>
          <input
            type="number"
            min={1}
            max={100}
            className={FIELD_CLS}
            {...form.register("max_evaluations", { valueAsNumber: true })}
          />
        </label>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <label className="space-y-1.5 text-sm">
          <span className="font-medium text-foreground">개체군 크기 (population)</span>
          <input
            type="number"
            min={2}
            max={200}
            className={FIELD_CLS}
            {...form.register("population_size", { valueAsNumber: true })}
          />
        </label>
        <label className="space-y-1.5 text-sm">
          <span className="font-medium text-foreground">세대 수 (generations)</span>
          <input
            type="number"
            min={1}
            max={100}
            className={FIELD_CLS}
            {...form.register("n_generations", { valueAsNumber: true })}
          />
        </label>
        <label className="space-y-1.5 text-sm">
          <span className="font-medium text-foreground">돌연변이율 (mutation)</span>
          <input
            type="text"
            placeholder="0.2"
            className={FIELD_CLS}
            {...form.register("mutation_rate")}
          />
        </label>
        <label className="space-y-1.5 text-sm">
          <span className="font-medium text-foreground">교차율 (crossover)</span>
          <input
            type="text"
            placeholder="0.8"
            className={FIELD_CLS}
            {...form.register("crossover_rate")}
          />
        </label>
      </div>

      {/* Sprint 57 BL-234: selection method */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <label className="space-y-1.5 text-sm">
          <span className="font-medium text-foreground">선택 방식 (selection)</span>
          <select
            className={FIELD_CLS}
            {...form.register("genetic_selection_method")}
          >
            <option value="tournament">토너먼트 (k=3)</option>
            <option value="roulette">룰렛 (순위 기반)</option>
          </select>
        </label>
      </div>

      <fieldset className="space-y-2 rounded-lg border border-border p-3">
        <legend className="px-1 text-sm font-medium text-foreground">
          파라미터 (1~4개)
        </legend>
        {fields.fields.map((field, idx) => (
          <div
            key={field.id}
            className="grid grid-cols-1 gap-2 rounded-md bg-muted/40 p-2 sm:grid-cols-6"
          >
            <input
              placeholder="변수 이름 (예: length)"
              className="rounded-md border border-input bg-background px-3 py-2 text-sm sm:col-span-2"
              {...form.register(`parameters.${idx}.var_name`)}
            />
            <select
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              {...form.register(`parameters.${idx}.kind`)}
            >
              <option value="integer">정수</option>
              <option value="decimal">실수</option>
            </select>
            <input
              placeholder="최소"
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              {...form.register(`parameters.${idx}.min`)}
            />
            <input
              placeholder="최대"
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              {...form.register(`parameters.${idx}.max`)}
            />
            <div className="flex items-center gap-1">
              <input
                placeholder="간격"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                {...form.register(`parameters.${idx}.step`)}
              />
              <button
                type="button"
                onClick={() => fields.remove(idx)}
                aria-label="파라미터 삭제"
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-input bg-background text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <X className="h-4 w-4" aria-hidden="true" />
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
          className="inline-flex items-center gap-1.5 rounded-md border border-input bg-background px-3 py-2 text-sm font-medium transition-colors hover:bg-muted disabled:opacity-50"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          파라미터 추가
        </button>
      </fieldset>

      {errMsg && (
        <div
          role="alert"
          className="rounded-md border border-destructive/40 bg-destructive-subtle p-3 text-sm text-destructive"
        >
          {errMsg}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={submit.isPending}
          className="inline-flex h-11 items-center rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-btn-primary transition-all hover:bg-primary-hover disabled:opacity-50"
        >
          {submit.isPending ? "실행 중…" : "유전 알고리즘 탐색 실행"}
        </button>
        <p className="text-xs text-muted-foreground">
          서버 평가 예산 상한 = 개체군 크기 × (세대 수 + 1). 토너먼트 선택 + 단일점
          교차 + 가우시안 돌연변이를 사용합니다.
        </p>
      </div>
    </form>
  );
}
