// 백테스트 폼의 세션 필드 (Symbol + Timeframe + DatePresetPills + 기간) — Sprint 59 PR-E.
"use client";

import { useWatch, type Control, type UseFormRegister, type UseFormSetValue, type FieldErrors } from "react-hook-form";

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Timeframe } from "@/features/backtest/schemas";

import { DatePresetPills, type DatePreset } from "./date-preset-pills";
import type { BacktestFormValues } from "./useBacktestForm";

const TIMEFRAMES: readonly Timeframe[] = [
  "1m",
  "5m",
  "15m",
  "1h",
  "4h",
  "1d",
] as const;

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
  control,
  register,
  setValue,
  errors,
  datePreset,
  setDatePreset,
  onDatePreset,
}: BacktestSessionFieldSetProps) {
  const selectedTimeframe = useWatch({ control, name: "timeframe" });

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="symbol" className="text-sm font-medium">
            심볼
          </label>
          <Input
            id="symbol"
            placeholder="BTC/USDT"
            {...register("symbol", {
              required: "심볼을 입력하세요",
              minLength: { value: 3, message: "최소 3자" },
              maxLength: { value: 32, message: "최대 32자" },
            })}
          />
          {errors.symbol ? (
            <p className="text-xs text-destructive">{errors.symbol.message}</p>
          ) : null}
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="timeframe" className="text-sm font-medium">
            Timeframe
          </label>
          <Select
            value={selectedTimeframe}
            onValueChange={(v) => {
              if (v == null) return;
              setValue("timeframe", v as Timeframe, { shouldValidate: true });
            }}
          >
            <SelectTrigger id="timeframe" aria-label="timeframe select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIMEFRAMES.map((tf) => (
                <SelectItem key={tf} value={tf}>
                  {tf}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <input type="hidden" {...register("timeframe")} />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium">기간 프리셋</span>
        <DatePresetPills value={datePreset} onSelect={onDatePreset} />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="period_start" className="text-sm font-medium">
            시작일
          </label>
          <Input
            id="period_start"
            type="date"
            {...register("period_start", {
              required: "시작일을 입력하세요",
              onChange: () => setDatePreset("custom"),
            })}
          />
          {errors.period_start ? (
            <p className="text-xs text-destructive">
              {errors.period_start.message}
            </p>
          ) : null}
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="period_end" className="text-sm font-medium">
            종료일
          </label>
          <Input
            id="period_end"
            type="date"
            {...register("period_end", {
              required: "종료일을 입력하세요",
              validate: (v, all) =>
                !all.period_start || new Date(v) > new Date(all.period_start) ||
                "종료일은 시작일 이후여야 합니다",
              onChange: () => setDatePreset("custom"),
            })}
          />
          {errors.period_end ? (
            <p className="text-xs text-destructive">
              {errors.period_end.message}
            </p>
          ) : null}
        </div>
      </div>
    </>
  );
}
