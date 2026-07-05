"use client";

// Optimizer 제출 폼 3종의 공통 프레젠테이션 조각 — 헤더 3필드 / 에러 alert / 제출 행.
// 폼 로직(스키마·매핑)은 form-schemas.ts, 상태는 use-optimizer-submit.ts 담당.

import type { FieldValues, Path, UseFormRegister } from "react-hook-form";

import type { OptimizerFormBaseValues } from "../form-schemas";

export const FIELD_CLS =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

/**
 * 목표 지표 / 최적화 방향 / 최대 평가 횟수 — 3폼 공통 헤더.
 * TValues 는 OptimizerFormBaseValues 를 구조적으로 포함해야 한다(호출측 스키마 계약).
 */
export function ObjectiveFields<TValues extends FieldValues>({
  register,
  maxEvaluations,
}: {
  register: UseFormRegister<TValues>;
  maxEvaluations: number;
}) {
  // base 필드 경로는 OptimizerFormBaseValues 부분집합 계약 — generic Path 캐스트.
  const path = (p: keyof OptimizerFormBaseValues) => p as Path<TValues>;
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <label className="space-y-1.5 text-sm">
        <span className="font-medium text-foreground">목표 지표</span>
        <select className={FIELD_CLS} {...register(path("objective_metric"))}>
          <option value="sharpe_ratio">샤프 비율</option>
          <option value="total_return">총 수익률</option>
          <option value="max_drawdown">최대 낙폭</option>
        </select>
      </label>
      <label className="space-y-1.5 text-sm">
        <span className="font-medium text-foreground">최적화 방향</span>
        <select className={FIELD_CLS} {...register(path("direction"))}>
          <option value="maximize">최대화</option>
          <option value="minimize">최소화</option>
        </select>
      </label>
      <label className="space-y-1.5 text-sm">
        <span className="font-medium text-foreground">
          최대 평가 횟수 (≤ {maxEvaluations})
        </span>
        <input
          type="number"
          min={1}
          max={maxEvaluations}
          className={FIELD_CLS}
          {...register(path("max_evaluations"), { valueAsNumber: true })}
        />
      </label>
    </div>
  );
}

export function FormErrorAlert({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div
      role="alert"
      className="rounded-md border border-destructive/40 bg-destructive-subtle p-3 text-sm text-destructive"
    >
      {message}
    </div>
  );
}

export function SubmitRow({
  isPending,
  submitLabel,
  pendingLabel = "실행 중…",
  helper,
}: {
  isPending: boolean;
  submitLabel: string;
  pendingLabel?: string;
  helper: string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        type="submit"
        disabled={isPending}
        className="inline-flex h-11 items-center rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-btn-primary transition-all hover:bg-primary-hover disabled:opacity-50"
      >
        {isPending ? pendingLabel : submitLabel}
      </button>
      <p className="text-xs text-muted-foreground">{helper}</p>
    </div>
  );
}
