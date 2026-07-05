"use client";

// Optimizer 3폼 공통 파라미터 row fieldset — var_name 셀 + append/remove(1~4 상한).
// 알고리즘별 나머지 셀(kind/step vs prior/log_scale)은 renderRowCells 로 주입받는다.

import { Plus, X } from "lucide-react";
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
    <fieldset className="space-y-2 rounded-lg border border-border p-3">
      <legend className="px-1 text-sm font-medium text-foreground">
        {legend}
      </legend>
      {fields.fields.map((field, idx) => (
        <div
          key={field.id}
          className="grid grid-cols-1 gap-2 rounded-md bg-muted/40 p-2 sm:grid-cols-6"
        >
          <input
            placeholder="변수 이름 (예: length)"
            className="rounded-md border border-input bg-background px-3 py-2 text-sm sm:col-span-2"
            {...register(`parameters.${idx}.var_name` as Path<TValues>)}
          />
          {renderRowCells(
            idx,
            <button
              type="button"
              onClick={() => fields.remove(idx)}
              aria-label="파라미터 삭제"
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-input bg-background text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>,
          )}
        </div>
      ))}
      <button
        type="button"
        onClick={() =>
          fields.append(emptyRow as FieldArray<TValues, ArrayPath<TValues>>)
        }
        disabled={fields.fields.length >= MAX_ROWS}
        className="inline-flex items-center gap-1.5 rounded-md border border-input bg-background px-3 py-2 text-sm font-medium transition-colors hover:bg-muted disabled:opacity-50"
      >
        <Plus className="h-4 w-4" aria-hidden="true" />
        파라미터 추가
      </button>
    </fieldset>
  );
}
