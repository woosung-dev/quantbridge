// 그리드 탐색 제출 폼 — 공유 조각(form-schemas/optimizer-form-fields/param-rows-fieldset) 조합.
"use client";

import { useForm } from "react-hook-form";
import { z } from "zod/v4";

import {
  FormErrorAlert,
  ObjectiveFields,
  SubmitRow,
} from "@/features/optimizer/components/optimizer-form-fields";
import { ParamRowsFieldset } from "@/features/optimizer/components/param-rows-fieldset";
import { useOptimizerSubmit } from "@/features/optimizer/components/use-optimizer-submit";
import {
  buildCreateRunBody,
  GridParameterRowSchema,
  makeOptimizerFormBaseFields,
  makeParametersArraySchema,
  rowsToParameters,
} from "@/features/optimizer/form-schemas";
import { useSubmitGridSearch } from "@/features/optimizer/hooks";
import { zodV4Resolver } from "@/lib/zod-v4-resolver";

const FormSchema = z.object({
  ...makeOptimizerFormBaseFields(9),
  parameters: makeParametersArraySchema(GridParameterRowSchema),
});

type FormValues = z.infer<typeof FormSchema>;

interface Props {
  backtestId: string;
  onSuccess?: (runId: string) => void;
}

const EMPTY_ROW = { var_name: "", kind: "integer", min: 10, max: 20, step: 5 };

export function GridSearchForm({ backtestId, onSuccess }: Props) {
  const submit = useSubmitGridSearch();
  const { errMsg, submitBody } = useOptimizerSubmit({
    mutateAsync: submit.mutateAsync,
    logTag: "grid search submit failed",
    onSuccess,
  });

  const form = useForm<FormValues>({
    resolver: zodV4Resolver(FormSchema),
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

  const handleSubmit = form.handleSubmit(async (values) => {
    await submitBody(
      buildCreateRunBody({
        kind: "grid_search",
        schemaVersion: 1,
        base: values,
        parameters: rowsToParameters(values.parameters, (row) => ({
          kind: row.kind,
          min: row.min,
          max: row.max,
          step: row.step,
        })),
      }),
    );
  });

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ObjectiveFields
        register={form.register}
        errors={form.formState.errors}
        maxEvaluations={9}
      />

      <ParamRowsFieldset
        control={form.control}
        register={form.register}
        errors={form.formState.errors}
        legend="파라미터 (1~4개)"
        emptyRow={EMPTY_ROW}
        renderRowCells={(idx, removeButton, errors, errorId) => (
          <>
            <select className="select" {...form.register(`parameters.${idx}.kind`)}>
              <option value="integer">정수</option>
              <option value="decimal">실수</option>
            </select>
            <input
              placeholder="최소"
              className="input"
              aria-invalid={errors.min ? "true" : "false"}
              aria-describedby={errors.min ? errorId("min") : undefined}
              {...form.register(`parameters.${idx}.min`)}
            />
            <input
              placeholder="최대"
              className="input"
              aria-invalid={errors.max ? "true" : "false"}
              aria-describedby={errors.max ? errorId("max") : undefined}
              {...form.register(`parameters.${idx}.max`)}
            />
            <div className="opt-param-row-tail">
              <input
                placeholder="간격"
                className="input"
                aria-invalid={errors.step ? "true" : "false"}
                aria-describedby={errors.step ? errorId("step") : undefined}
                {...form.register(`parameters.${idx}.step`)}
              />
              {removeButton}
            </div>
          </>
        )}
      />

      <FormErrorAlert message={errMsg} />

      <SubmitRow
        isPending={submit.isPending}
        submitLabel="그리드 탐색 실행"
        helper="전체 조합 수가 9개를 넘지 않도록 변수 범위를 조정해 주세요."
      />
    </form>
  );
}
