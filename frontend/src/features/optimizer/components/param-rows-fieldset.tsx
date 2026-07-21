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
  type FieldValues,
  type Path,
  type UseFormRegister,
} from "react-hook-form";

const MAX_ROWS = 4;

export interface ParamRowsFieldsetProps<TValues extends FieldValues> {
  control: Control<TValues>;
  register: UseFormRegister<TValues>;
  legend: string;
  /** append 시 기본 row 값 — 호출측 row 스키마 기본형. */
  emptyRow: Record<string, unknown>;
  /**
   * var_name 다음의 알고리즘별 셀들. removeButton 을 마지막 셀 안에 배치할 것
   * (기존 3폼 레이아웃 유지 — 마지막 셀이 flex 로 버튼을 품는다).
   */
  renderRowCells: (index: number, removeButton: ReactNode) => ReactNode;
}

export function ParamRowsFieldset<TValues extends FieldValues>({
  control,
  register,
  legend,
  emptyRow,
  renderRowCells,
}: ParamRowsFieldsetProps<TValues>) {
  // "parameters" 배열 필드는 3폼 공통 계약 — generic ArrayPath 캐스트.
  const fields = useFieldArray({
    control,
    name: "parameters" as ArrayPath<TValues>,
  });

  return (
    <fieldset className="opt-fieldset">
      <legend>{legend}</legend>
      {fields.fields.map((field, idx) => (
        <div key={field.id} className="opt-param-row">
          <input
            placeholder="변수 이름 (예: length)"
            className="input"
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
          )}
        </div>
      ))}
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
