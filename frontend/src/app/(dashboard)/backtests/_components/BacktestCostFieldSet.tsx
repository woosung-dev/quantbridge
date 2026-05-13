// 백테스트 폼의 비용 필드 (initial_capital + fees + slippage) — Sprint 59 PR-E.
"use client";

import type { UseFormRegister, FieldErrors } from "react-hook-form";

import { Input } from "@/components/ui/input";

import type { BacktestFormValues } from "./useBacktestForm";

interface BacktestCostFieldSetProps {
  register: UseFormRegister<BacktestFormValues>;
  errors: FieldErrors<BacktestFormValues>;
}

export function BacktestCostFieldSet({
  register,
  errors,
}: BacktestCostFieldSetProps) {
  return (
    <>
      <div className="flex flex-col gap-1.5">
        <label htmlFor="initial_capital" className="text-sm font-medium">
          초기 자본 (USDT)
        </label>
        <Input
          id="initial_capital"
          type="number"
          step="0.01"
          {...register("initial_capital", {
            required: "초기 자본을 입력하세요",
            valueAsNumber: true,
            validate: (v) =>
              (Number.isFinite(v) && v > 0) || "0보다 큰 값을 입력하세요",
          })}
        />
        {errors.initial_capital ? (
          <p className="text-xs text-destructive">
            {errors.initial_capital.message}
          </p>
        ) : null}
      </div>

      {/* Sprint 31 BL-162a — 비용 시뮬레이션 (TradingView strategy 속성 패턴). */}
      <section
        className="border-t pt-4"
        aria-label="비용 시뮬레이션"
        data-testid="backtest-form-cost-section"
      >
        <h3 className="mb-3 text-sm font-medium">비용 시뮬레이션</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="fees_pct" className="text-sm">
              수수료 (소수, 0.001 = 0.10%)
            </label>
            <Input
              id="fees_pct"
              type="number"
              step="0.0001"
              min={0}
              max={0.01}
              {...register("fees_pct", {
                required: "수수료를 입력하세요",
                valueAsNumber: true,
                validate: (v) =>
                  (Number.isFinite(v) && v >= 0 && v <= 0.01) ||
                  "0 ~ 0.01 (1%) 범위여야 합니다",
              })}
            />
            {errors.fees_pct ? (
              <p className="text-xs text-destructive">
                {errors.fees_pct.message}
              </p>
            ) : null}
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="slippage_pct" className="text-sm">
              슬리피지 (소수, 0.0005 = 0.05%)
            </label>
            <Input
              id="slippage_pct"
              type="number"
              step="0.0001"
              min={0}
              max={0.01}
              {...register("slippage_pct", {
                required: "슬리피지를 입력하세요",
                valueAsNumber: true,
                validate: (v) =>
                  (Number.isFinite(v) && v >= 0 && v <= 0.01) ||
                  "0 ~ 0.01 (1%) 범위여야 합니다",
              })}
            />
            {errors.slippage_pct ? (
              <p className="text-xs text-destructive">
                {errors.slippage_pct.message}
              </p>
            ) : null}
          </div>
        </div>
      </section>
    </>
  );
}
