// Sprint 56 BL-233 — Genetic Search 제출 폼. 공유 조각 조합 + 하이퍼파라미터 4종 + budget 검증.
"use client";

import { useForm } from "react-hook-form";
import { z } from "zod/v4";

import {
  INPUT_CLS,
  SELECT_CLS,
  FieldError,
  FormErrorAlert,
  ObjectiveFields,
  SubmitRow,
} from "@/features/optimizer/components/optimizer-form-fields";
import { ParamRowsFieldset } from "@/features/optimizer/components/param-rows-fieldset";
import { useOptimizerSubmit } from "@/features/optimizer/components/use-optimizer-submit";
import {
  buildCreateRunBody,
  GeneticRowSchema,
  makeOptimizerFormBaseFields,
  makeParametersArraySchema,
  rowsToParameters,
} from "@/features/optimizer/form-schemas";
import { useSubmitGeneticSearch } from "@/features/optimizer/hooks";
import { zodV4Resolver } from "@/lib/zod-v4-resolver";

const FormSchema = z
  .object({
    ...makeOptimizerFormBaseFields(100), // BL-237: 50→100
    population_size: z
      .coerce
      .number()
      .int("개체군 크기는 정수여야 합니다.")
      .min(2, "개체군 크기는 2 이상이어야 합니다.")
      .max(200, "개체군 크기는 200 이하여야 합니다."),
    n_generations: z
      .coerce
      .number()
      .int("세대 수는 정수여야 합니다.")
      .min(1, "세대 수는 1 이상이어야 합니다.")
      .max(100, "세대 수는 100 이하여야 합니다."),
    mutation_rate: z.string().min(1, "돌연변이율을 입력하세요."),
    crossover_rate: z.string().min(1, "교차율을 입력하세요."),
    // Sprint 57 BL-234: roulette selection method enum.
    genetic_selection_method: z
      .enum(["tournament", "roulette"])
      .default("tournament"),
    parameters: makeParametersArraySchema(GeneticRowSchema),
  })
  .superRefine((values, ctx) => {
    const mutN = Number(values.mutation_rate);
    const crossN = Number(values.crossover_rate);
    if (!(mutN > 0 && mutN <= 1)) {
      ctx.addIssue({
        code: "custom",
        path: ["mutation_rate"],
        message: "돌연변이율은 0보다 크고 1 이하여야 합니다.",
      });
    }
    if (!(crossN > 0 && crossN <= 1)) {
      ctx.addIssue({
        code: "custom",
        path: ["crossover_rate"],
        message: "교차율은 0보다 크고 1 이하여야 합니다.",
      });
    }
    // budget = pop * (gen + 1) <= max_evaluations <= 100 (BL-237).
    const budget = values.population_size * (values.n_generations + 1);
    if (budget > values.max_evaluations) {
      ctx.addIssue({
        code: "custom",
        path: ["max_evaluations"],
        message: `평가 예산(${budget}) > 최대 평가 횟수(${values.max_evaluations})입니다.`,
      });
    }
    if (budget > 100) {
      ctx.addIssue({
        code: "custom",
        path: ["population_size"],
        message: `평가 예산(${budget}) > 서버 상한(100)입니다.`,
      });
    }
  });

type FormValues = z.infer<typeof FormSchema>;

interface Props {
  backtestId: string;
  onSuccess?: (runId: string) => void;
}

const EMPTY_ROW = {
  var_name: "",
  kind: "integer",
  min: "5",
  max: "30",
  step: "1",
};

export function GeneticSearchForm({ backtestId, onSuccess }: Props) {
  const submit = useSubmitGeneticSearch();
  const { errMsg, submitBody } = useOptimizerSubmit({
    mutateAsync: submit.mutateAsync,
    logTag: "genetic search submit failed",
    onSuccess,
  });

  const form = useForm<FormValues>({
    resolver: zodV4Resolver(FormSchema),
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

  const handleSubmit = form.handleSubmit(async (values) => {
    await submitBody(
      buildCreateRunBody({
        kind: "genetic",
        schemaVersion: 2,
        base: values,
        parameters: rowsToParameters(values.parameters, (row) =>
          row.kind === "integer"
            ? {
                kind: "integer",
                min: Number.parseInt(row.min, 10),
                max: Number.parseInt(row.max, 10),
                step: Number.parseInt(row.step, 10),
              }
            : {
                kind: "decimal",
                min: row.min,
                max: row.max,
                step: row.step,
              },
        ),
        extras: {
          population_size: values.population_size,
          n_generations: values.n_generations,
          mutation_rate: values.mutation_rate,
          crossover_rate: values.crossover_rate,
          genetic_selection_method: values.genetic_selection_method,
        },
      }),
    );
  });
  const populationError = form.formState.errors.population_size?.message;
  const generationsError = form.formState.errors.n_generations?.message;
  const mutationRateError = form.formState.errors.mutation_rate?.message;
  const crossoverRateError = form.formState.errors.crossover_rate?.message;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ObjectiveFields
        register={form.register}
        errors={form.formState.errors}
        maxEvaluations={100}
      />

      <div className="opt-field-grid-4">
        <label className="field">
          <span className="field-label">개체군 크기 (population)</span>
          <input
            type="number"
            min={2}
            max={200}
            className={INPUT_CLS}
            aria-invalid={populationError ? "true" : "false"}
            aria-describedby={populationError ? "optimizer-population-size-error" : undefined}
            {...form.register("population_size", { valueAsNumber: true })}
          />
          {populationError && (
            <FieldError id="optimizer-population-size-error" message={populationError} />
          )}
        </label>
        <label className="field">
          <span className="field-label">세대 수 (generations)</span>
          <input
            type="number"
            min={1}
            max={100}
            className={INPUT_CLS}
            aria-invalid={generationsError ? "true" : "false"}
            aria-describedby={generationsError ? "optimizer-generations-error" : undefined}
            {...form.register("n_generations", { valueAsNumber: true })}
          />
          {generationsError && (
            <FieldError id="optimizer-generations-error" message={generationsError} />
          )}
        </label>
        <label className="field">
          <span className="field-label">돌연변이율 (mutation)</span>
          <input
            type="text"
            placeholder="0.2"
            className={INPUT_CLS}
            aria-invalid={mutationRateError ? "true" : "false"}
            aria-describedby={mutationRateError ? "optimizer-mutation-rate-error" : undefined}
            {...form.register("mutation_rate")}
          />
          {mutationRateError && (
            <FieldError id="optimizer-mutation-rate-error" message={mutationRateError} />
          )}
        </label>
        <label className="field">
          <span className="field-label">교차율 (crossover)</span>
          <input
            type="text"
            placeholder="0.8"
            className={INPUT_CLS}
            aria-invalid={crossoverRateError ? "true" : "false"}
            aria-describedby={crossoverRateError ? "optimizer-crossover-rate-error" : undefined}
            {...form.register("crossover_rate")}
          />
          {crossoverRateError && (
            <FieldError id="optimizer-crossover-rate-error" message={crossoverRateError} />
          )}
        </label>
      </div>

      {/* Sprint 57 BL-234: selection method */}
      <div className="opt-field-grid-2">
        <label className="field">
          <span className="field-label">선택 방식 (selection)</span>
          <select className={SELECT_CLS} {...form.register("genetic_selection_method")}>
            <option value="tournament">토너먼트 (k=3)</option>
            <option value="roulette">룰렛 (순위 기반)</option>
          </select>
        </label>
      </div>

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
        submitLabel="유전 알고리즘 탐색 실행"
        helper="서버 평가 예산 상한 = 개체군 크기 × (세대 수 + 1). 토너먼트 선택 + 단일점 교차 + 가우시안 돌연변이를 사용합니다."
      />
    </form>
  );
}
