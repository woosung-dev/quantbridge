// Sprint 55 — Bayesian Search 제출 form (RHF + Zod, BayesianHyperparamsField row append/remove).
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, X } from "lucide-react";
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
        message: "log_scale / log_uniform 은 min > 0 필요",
      });
    }
  });

const FormSchema = z.object({
  backtest_id: z.uuid(),
  objective_metric: OptimizationObjectiveMetricSchema,
  direction: OptimizationDirectionSchema,
  max_evaluations: z.coerce.number().int().min(1).max(100),
  bayesian_n_initial_random: z.coerce.number().int().min(1).max(100),
  bayesian_acquisition: BayesianAcquisitionSchema,
  parameters: z.array(BayesianRowSchema).min(1).max(4),
});

type FormValues = z.infer<typeof FormSchema>;

interface Props {
  backtestId: string;
  onSuccess?: (runId: string) => void;
}

const FIELD_CLS =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

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
        `초기 랜덤 탐색 횟수(${values.bayesian_n_initial_random})는 최대 평가 횟수(${values.max_evaluations})보다 클 수 없습니다.`,
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
      // raw 백엔드 에러를 그대로 노출하지 않음 (내부 용어 유출 차단) — 콘솔에만 기술 상세.
      console.error("bayesian search submit failed", e);
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

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <label className="space-y-1.5 text-sm">
          <span className="font-medium text-foreground">초기 랜덤 탐색 횟수 (워밍업)</span>
          <input
            type="number"
            min={1}
            max={100}
            className={FIELD_CLS}
            {...form.register("bayesian_n_initial_random", { valueAsNumber: true })}
          />
        </label>
        <label className="space-y-1.5 text-sm">
          <span className="font-medium text-foreground">획득 함수 (acquisition)</span>
          <select className={FIELD_CLS} {...form.register("bayesian_acquisition")}>
            <option value="EI">EI (기대 개선량)</option>
            <option value="UCB">UCB (신뢰상한)</option>
            <option value="PI">PI (개선 확률)</option>
          </select>
        </label>
      </div>

      <fieldset className="space-y-2 rounded-lg border border-border p-3">
        <legend className="px-1 text-sm font-medium text-foreground">
          파라미터 (1~4개, 정규분포 prior 준비 중)
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
            <select
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              {...form.register(`parameters.${idx}.prior`)}
            >
              <option value="uniform">균등 (uniform)</option>
              <option value="log_uniform">로그균등 (min &gt; 0)</option>
              <option value="normal" disabled>
                정규분포 (준비 중)
              </option>
            </select>
            <div className="flex items-center justify-between gap-1">
              <label className="flex items-center gap-1.5 text-xs">
                <input
                  type="checkbox"
                  {...form.register(`parameters.${idx}.log_scale`)}
                />
                로그 스케일
              </label>
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
              min: "5",
              max: "30",
              prior: "uniform",
              log_scale: false,
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
          {submit.isPending ? "실행 중…" : "베이지안 탐색 실행"}
        </button>
        <p className="text-xs text-muted-foreground">
          서버에서 최대 평가 횟수 상한이 적용됩니다. 초기 랜덤 탐색 후 베이지안 탐색
          단계로 진입합니다.
        </p>
      </div>
    </form>
  );
}
