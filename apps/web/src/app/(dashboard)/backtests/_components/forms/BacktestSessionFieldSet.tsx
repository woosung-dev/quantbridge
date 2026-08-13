// 백테스트 폼의 시장과 기간 필드 (심볼 + 타임프레임 + 기간 프리셋 + 시작/종료일) — C 디자인 언어 이식(W3-A).
"use client";

import {
  type Control,
  type UseFormRegister,
  type UseFormSetValue,
  type FieldErrors,
} from "react-hook-form";

import type { Timeframe } from "@/features/backtest/schemas";

import { DatePresetPills, type DatePreset } from "@/app/(dashboard)/backtests/_components/forms/date-preset-pills";
import type { BacktestFormValues } from "@/app/(dashboard)/backtests/_components/forms/useBacktestForm";

const SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"] as const;
const TIMEFRAMES: readonly Timeframe[] = ["15m", "1h", "4h", "1d"] as const;

interface BacktestSessionFieldSetProps {
  control: Control<BacktestFormValues>;
  register: UseFormRegister<BacktestFormValues>;
  setValue: UseFormSetValue<BacktestFormValues>;
  errors: FieldErrors<BacktestFormValues>;
  datePreset: DatePreset;
  setDatePreset: (preset: DatePreset) => void;
  onDatePreset: (preset: DatePreset) => void;
}

export function BacktestSessionFieldSet({
  register,
  errors,
  datePreset,
  setDatePreset,
  onDatePreset,
}: BacktestSessionFieldSetProps) {
  return (
    <>
      <div className="field-grid">
        <div className="field">
          <span className="field-reqline">
            <label className="field-label" htmlFor="symbol">
              심볼
            </label>
            <span className="field-req" aria-hidden="true">필수</span>
          </span>
          <select
            className="select"
            id="symbol"
            {...register("symbol", {
              required: "심볼을 입력하세요",
              minLength: { value: 3, message: "최소 3자" },
              maxLength: { value: 32, message: "최대 32자" },
            })}
          >
            {SYMBOLS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          {errors.symbol ? (
            <p className="field-error" role="alert">
              {errors.symbol.message}
            </p>
          ) : null}
        </div>

        <div className="field">
          <span className="field-reqline">
            <label className="field-label" htmlFor="timeframe">
              타임프레임
            </label>
            <span className="field-req" aria-hidden="true">필수</span>
          </span>
          <select className="select" id="timeframe" {...register("timeframe")}>
            {TIMEFRAMES.map((tf) => (
              <option key={tf} value={tf}>
                {tf}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label className="field-label" htmlFor="period_start">
            시작일
          </label>
          <span className="date-wrap">
            <input
              className="input"
              id="period_start"
              type="date"
              {...register("period_start", {
                required: "시작일을 입력하세요",
                onChange: () => setDatePreset("custom"),
              })}
            />
          </span>
          {errors.period_start ? (
            <p className="field-error" role="alert">
              {errors.period_start.message}
            </p>
          ) : null}
        </div>

        <div className="field">
          <label className="field-label" htmlFor="period_end">
            종료일
          </label>
          <span className="date-wrap">
            <input
              className="input"
              id="period_end"
              type="date"
              {...register("period_end", {
                required: "종료일을 입력하세요",
                validate: (v, all) =>
                  !all.period_start ||
                  new Date(v) > new Date(all.period_start) ||
                  "종료일은 시작일 이후여야 합니다",
                onChange: () => setDatePreset("custom"),
              })}
            />
          </span>
          {errors.period_end ? (
            <p className="field-error" role="alert">
              {errors.period_end.message}
            </p>
          ) : null}
        </div>

        <div className="field span-2">
          <span className="field-label">기간 프리셋</span>
          <DatePresetPills value={datePreset} onSelect={onDatePreset} />
          <p className="field-hint">
            프리셋을 고르면 시작일과 종료일이 함께 채워집니다. 직접 날짜를 바꾸면
            커스텀으로 전환됩니다.
          </p>
        </div>

        <div className="field span-2">
          <span className="field-label">거래소</span>
          <p className="field-static">
            <svg
              className="lock"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <rect x="4.5" y="10.5" width="15" height="10" rx="2" />
              <path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" />
            </svg>
            Bybit
          </p>
          <p className="field-hint">
            현재 연결된 거래소는 Bybit 하나입니다. 바꾸려면 연결 설정에서 다른
            거래소 API 키를 먼저 등록해야 합니다.
          </p>
        </div>
      </div>
    </>
  );
}
