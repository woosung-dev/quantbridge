// 그리드 탐색 제출 폼 (RHF + Zod, 파라미터 row append/remove)
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, X } from "lucide-react";
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

const FIELD_CLS =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

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
      // raw 백엔드 에러를 그대로 노출하지 않음 (내부 용어 유출 차단) — 콘솔에만 기술 상세.
      console.error("grid search submit failed", e);
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
          <span className="font-medium text-foreground">최대 평가 횟수 (≤ 9)</span>
          <input
            type="number"
            min={1}
            max={9}
            className={FIELD_CLS}
            {...form.register("max_evaluations", { valueAsNumber: true })}
          />
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
              min: 10,
              max: 20,
              step: 5,
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
          {submit.isPending ? "실행 중…" : "그리드 탐색 실행"}
        </button>
        <p className="text-xs text-muted-foreground">
          전체 조합 수가 9개를 넘지 않도록 변수 범위를 조정해 주세요.
        </p>
      </div>
    </form>
  );
}
