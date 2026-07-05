// Sprint 55 — Bayesian Search 제출 폼. 공유 조각 조합 + 고유 필드(n_initial_random/acquisition).
"use client";

import { useForm } from "react-hook-form";
import { z } from "zod/v4";

import {
  FIELD_CLS,
  FormErrorAlert,
  ObjectiveFields,
  SubmitRow,
} from "@/features/optimizer/components/optimizer-form-fields";
import { ParamRowsFieldset } from "@/features/optimizer/components/param-rows-fieldset";
import { useOptimizerSubmit } from "@/features/optimizer/components/use-optimizer-submit";
import {
  BayesianRowSchema,
  buildCreateRunBody,
  makeOptimizerFormBaseFields,
  makeParametersArraySchema,
  rowsToParameters,
} from "@/features/optimizer/form-schemas";
import { useSubmitBayesianSearch } from "@/features/optimizer/hooks";
import { BayesianAcquisitionSchema } from "@/features/optimizer/schemas";
import { zodV4Resolver } from "@/lib/zod-v4-resolver";

const FormSchema = z.object({
  ...makeOptimizerFormBaseFields(100),
  bayesian_n_initial_random: z.coerce.number().int().min(1).max(100),
  bayesian_acquisition: BayesianAcquisitionSchema,
  parameters: makeParametersArraySchema(BayesianRowSchema),
});

type FormValues = z.infer<typeof FormSchema>;

interface Props {
  backtestId: string;
  onSuccess?: (runId: string) => void;
}

const EMPTY_ROW = {
  var_name: "",
  min: "5",
  max: "30",
  prior: "uniform",
  log_scale: false,
};

export function BayesianSearchForm({ backtestId, onSuccess }: Props) {
  const submit = useSubmitBayesianSearch();
  const { errMsg, setErrMsg, submitBody } = useOptimizerSubmit({
    mutateAsync: submit.mutateAsync,
    logTag: "bayesian search submit failed",
    onSuccess,
  });

  const form = useForm<FormValues>({
    resolver: zodV4Resolver(FormSchema),
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

  const handleSubmit = form.handleSubmit(async (values) => {
    // cross-field 검증 — 폼이 field-level 에러를 렌더하지 않으므로 alert 로 노출 유지.
    if (values.bayesian_n_initial_random > values.max_evaluations) {
      setErrMsg(
        `초기 랜덤 탐색 횟수(${values.bayesian_n_initial_random})는 최대 평가 횟수(${values.max_evaluations})보다 클 수 없습니다.`,
      );
      return;
    }

    await submitBody(
      buildCreateRunBody({
        kind: "bayesian",
        schemaVersion: 2,
        base: values,
        parameters: rowsToParameters(values.parameters, (row) => ({
          kind: "bayesian",
          min: row.min,
          max: row.max,
          prior: row.prior,
          log_scale: row.log_scale,
        })),
        extras: {
          bayesian_n_initial_random: values.bayesian_n_initial_random,
          bayesian_acquisition: values.bayesian_acquisition,
        },
      }),
    );
  });

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ObjectiveFields register={form.register} maxEvaluations={100} />

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

      <ParamRowsFieldset
        control={form.control}
        register={form.register}
        legend="파라미터 (1~4개, 정규분포 prior 준비 중)"
        emptyRow={EMPTY_ROW}
        renderRowCells={(idx, removeButton) => (
          <>
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
              {removeButton}
            </div>
          </>
        )}
      />

      <FormErrorAlert message={errMsg} />

      <SubmitRow
        isPending={submit.isPending}
        submitLabel="베이지안 탐색 실행"
        helper="서버에서 최대 평가 횟수 상한이 적용됩니다. 초기 랜덤 탐색 후 베이지안 탐색 단계로 진입합니다."
      />
    </form>
  );
}
