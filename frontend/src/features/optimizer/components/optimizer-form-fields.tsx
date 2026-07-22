"use client";

// Optimizer 제출 폼 3종의 공통 프레젠테이션 조각 — 헤더 3필드 / 에러 alert / 제출 행.
// C 디자인 언어 이식 (W3-C): 공용 .field/.field-label/.input/.select/.btn 소비.
// 자체 focus ring 제거 — 전역 카퍼 :focus-visible 링을 소비한다.
// 라벨은 W1 용어 SSOT(OBJECTIVE_*_LABEL) 경유 (샤프 지수 등 표기 통일).

import type { FieldValues, Path, UseFormRegister } from "react-hook-form";

import { AlertTriangleIcon } from "lucide-react";

import {
  OBJECTIVE_DIRECTION_HINT,
  OBJECTIVE_DIRECTION_LABEL,
  OBJECTIVE_METRIC_LABEL,
} from "@/features/optimizer/labels";
import type { OptimizerFormBaseValues } from "../form-schemas";

// C 공용 입력/셀렉트 클래스 — 자체 focus ring 없음(전역 :focus-visible 카퍼 링 소비).
export const INPUT_CLS = "input";
export const SELECT_CLS = "select";

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
    <div className="opt-field-grid">
      <label className="field">
        <span className="field-label">목표 지표</span>
        <select className={SELECT_CLS} {...register(path("objective_metric"))}>
          <option value="sharpe_ratio">{OBJECTIVE_METRIC_LABEL.sharpe_ratio}</option>
          <option value="total_return">{OBJECTIVE_METRIC_LABEL.total_return}</option>
          <option value="max_drawdown">{OBJECTIVE_METRIC_LABEL.max_drawdown}</option>
        </select>
      </label>
      <label className="field">
        <span className="field-label">최적화 방향</span>
        <select className={SELECT_CLS} {...register(path("direction"))}>
          <option value="maximize">
            {OBJECTIVE_DIRECTION_LABEL.maximize} ({OBJECTIVE_DIRECTION_HINT.maximize})
          </option>
          <option value="minimize">
            {OBJECTIVE_DIRECTION_LABEL.minimize} ({OBJECTIVE_DIRECTION_HINT.minimize})
          </option>
        </select>
      </label>
      <label className="field">
        <span className="field-label">최대 평가 횟수 (최대 {maxEvaluations})</span>
        <input
          type="number"
          min={1}
          max={maxEvaluations}
          className={INPUT_CLS}
          {...register(path("max_evaluations"), { valueAsNumber: true })}
        />
      </label>
    </div>
  );
}

export function FormErrorAlert({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="notice-inline">
      <AlertTriangleIcon aria-hidden="true" />
      <span>{message}</span>
    </p>
  );
}

export function SubmitRow({
  isPending,
  submitLabel,
  pendingLabel = "실행 중",
  helper,
}: {
  isPending: boolean;
  submitLabel: string;
  pendingLabel?: string;
  helper: string;
}) {
  return (
    <div className="opt-form-actions">
      <button type="submit" disabled={isPending} className="btn btn-primary">
        {isPending ? pendingLabel : submitLabel}
      </button>
      <p className="opt-form-helper">{helper}</p>
    </div>
  );
}
