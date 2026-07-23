"use client";

// Optimizer 3폼 공통 파라미터 row fieldset — var_name 셀 + append/remove(1~4 상한).
// 알고리즘별 나머지 셀(kind/step vs prior/log_scale)은 renderRowCells 로 주입받는다.
// C 디자인 언어 이식 (W3-C): .opt-fieldset/.opt-param-row/.input/.icon-btn/.btn 소비.

import { PlusIcon, XIcon } from "lucide-react";
import type { ReactNode } from "react";
import {
  useFieldArray,
  type ArrayPath,
  type Control,
  type FieldArray,
  type FieldErrors,
  type FieldValues,
  type Path,
  type UseFormRegister,
} from "react-hook-form";

import { FieldError } from "./optimizer-form-fields";

const MAX_ROWS = 4;
type ParamRowErrors = Record<string, { message?: unknown } | undefined>;

export interface ParamRowsFieldsetProps<TValues extends FieldValues> {
  control: Control<TValues>;
  register: UseFormRegister<TValues>;
  errors: FieldErrors<TValues>;
  legend: string;
  /** append 시 기본 row 값 — 호출측 row 스키마 기본형. */
  emptyRow: Record<string, unknown>;
  /**
   * var_name 다음의 알고리즘별 셀들. removeButton 을 마지막 셀 안에 배치할 것
   * (기존 3폼 레이아웃 유지 — 마지막 셀이 flex 로 버튼을 품는다).
   */
  renderRowCells: (
    index: number,
    removeButton: ReactNode,
    errors: ParamRowErrors,
    errorId: (field: string) => string,
  ) => ReactNode;
}

export function ParamRowsFieldset<TValues extends FieldValues>({
  control,
  register,
  errors,
  legend,
  emptyRow,
  renderRowCells,
}: ParamRowsFieldsetProps<TValues>) {
  // "parameters" 배열 필드는 3폼 공통 계약 — generic ArrayPath 캐스트.
  const fields = useFieldArray({
    control,
    name: "parameters" as ArrayPath<TValues>,
  });

  // 배열 레벨 오류(.min(1)/.max(4)) — 행이 0개면 행별 슬롯이 없어 여기서만 표출된다.
  // resolver 평탄 키("parameters")와 RHF 중첩(root/직접 message) 모두 흡수.
  const arrayLevelHolder = (
    errors as { parameters?: { message?: unknown; root?: { message?: unknown } } }
  ).parameters;
  const arrayLevelMessage = [
    arrayLevelHolder?.message,
    arrayLevelHolder?.root?.message,
    (errors as Record<string, { message?: unknown } | undefined>)["parameters"]?.message,
  ].find((m): m is string => typeof m === "string");

  return (
    <fieldset className="opt-fieldset">
      <legend>{legend}</legend>
      {fields.fields.map((field, idx) => {
        const nestedErrors = (errors as { parameters?: ParamRowErrors[] }).parameters?.[idx];
        const flatErrors = errors as Record<string, { message?: unknown } | undefined>;
        const rowErrors = Object.fromEntries(
          ["var_name", "min", "max", "step"].flatMap((name) => {
            const error = nestedErrors?.[name] ?? flatErrors[`parameters.${idx}.${name}`];
            return error ? [[name, error]] : [];
          }),
        ) as ParamRowErrors;
        const errorId = (name: string) => `optimizer-param-${idx}-${name}-error`;
        const errorMessage = (name: string) => {
          const message = rowErrors[name]?.message;
          return typeof message === "string" ? message : undefined;
        };

        return (
          <div key={field.id}>
            <div className="opt-param-row">
              <input
                placeholder="변수 이름 (예: length)"
                className="input"
                aria-invalid={errorMessage("var_name") ? "true" : "false"}
                aria-describedby={errorMessage("var_name") ? errorId("var_name") : undefined}
                {...register(`parameters.${idx}.var_name` as Path<TValues>)}
              />
              {renderRowCells(
                idx,
                <button
                  type="button"
                  onClick={() => fields.remove(idx)}
                  aria-label="파라미터 삭제"
                  className="icon-btn"
                >
                  <XIcon aria-hidden="true" />
                </button>,
                rowErrors,
                errorId,
              )}
            </div>
            {Object.entries(rowErrors).map(([name, error]) =>
              typeof error?.message === "string" ? (
                <FieldError key={name} id={errorId(name)} message={error.message} />
              ) : null,
            )}
          </div>
        );
      })}
      {arrayLevelMessage ? (
        <FieldError id="optimizer-parameters-error" message={arrayLevelMessage} />
      ) : null}
      <button
        type="button"
        onClick={() => fields.append(emptyRow as FieldArray<TValues, ArrayPath<TValues>>)}
        disabled={fields.fields.length >= MAX_ROWS}
        className="btn btn-ghost btn-xs"
        style={{ alignSelf: "flex-start" }}
      >
        <PlusIcon aria-hidden="true" />
        파라미터 추가
      </button>
    </fieldset>
  );
}
