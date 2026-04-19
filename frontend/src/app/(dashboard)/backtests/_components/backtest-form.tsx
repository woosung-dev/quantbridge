"use client";

import { useRouter } from "next/navigation";
import { useForm, useWatch, type SubmitHandler } from "react-hook-form";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateBacktest } from "@/features/backtest/hooks";
import type { Timeframe } from "@/features/backtest/schemas";
import { useStrategies } from "@/features/strategy/hooks";
import type { StrategyListItem } from "@/features/strategy/schemas";

const TIMEFRAMES: readonly Timeframe[] = [
  "1m",
  "5m",
  "15m",
  "1h",
  "4h",
  "1d",
] as const;

interface FormValues {
  strategy_id: string;
  symbol: string;
  timeframe: Timeframe;
  period_start: string; // local datetime-like "YYYY-MM-DD"
  period_end: string;
  initial_capital: number;
}

function toIsoUtc(dateOnly: string): string {
  // "YYYY-MM-DD" → "YYYY-MM-DDT00:00:00Z". 경계 외 값은 Date 파싱 실패.
  return new Date(`${dateOnly}T00:00:00Z`).toISOString();
}

export function BacktestForm() {
  const router = useRouter();
  const strategies = useStrategies({ limit: 100, offset: 0, is_archived: false });

  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    defaultValues: {
      strategy_id: "",
      symbol: "BTC/USDT",
      timeframe: "1h",
      period_start: "",
      period_end: "",
      initial_capital: 10000,
    },
  });

  const create = useCreateBacktest({
    onSuccess: (data) => {
      toast.success("백테스트 요청됨");
      router.push(`/backtests/${data.backtest_id}`);
    },
    onError: (err) => {
      toast.error(`요청 실패: ${err.message}`);
    },
  });

  const onSubmit: SubmitHandler<FormValues> = (values) => {
    create.mutate({
      strategy_id: values.strategy_id,
      symbol: values.symbol,
      timeframe: values.timeframe,
      period_start: toIsoUtc(values.period_start),
      period_end: toIsoUtc(values.period_end),
      initial_capital: Number(values.initial_capital),
    });
  };

  const strategyItems: StrategyListItem[] = strategies.data?.items ?? [];
  const selectedStrategy = useWatch({ control, name: "strategy_id" });
  const selectedTimeframe = useWatch({ control, name: "timeframe" });

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="flex flex-col gap-5"
      aria-label="backtest-form"
    >
      <div className="flex flex-col gap-1.5">
        <label htmlFor="strategy_id" className="text-sm font-medium">
          전략
        </label>
        <Select
          value={selectedStrategy}
          onValueChange={(v) =>
            setValue("strategy_id", v ?? "", { shouldValidate: true })
          }
        >
          <SelectTrigger id="strategy_id" aria-label="strategy select">
            <SelectValue placeholder="전략을 선택하세요" />
          </SelectTrigger>
          <SelectContent>
            {strategyItems.length === 0 ? (
              <div className="px-2 py-1.5 text-xs text-muted-foreground">
                사용 가능한 전략이 없습니다
              </div>
            ) : (
              strategyItems.map((s) => (
                <SelectItem key={s.id} value={s.id}>
                  {s.name}
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
        <input
          type="hidden"
          {...register("strategy_id", { required: "전략을 선택하세요" })}
        />
        {errors.strategy_id ? (
          <p className="text-xs text-destructive">{errors.strategy_id.message}</p>
        ) : null}
      </div>

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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="period_start" className="text-sm font-medium">
            시작일
          </label>
          <Input
            id="period_start"
            type="date"
            {...register("period_start", { required: "시작일을 입력하세요" })}
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
            })}
          />
          {errors.period_end ? (
            <p className="text-xs text-destructive">
              {errors.period_end.message}
            </p>
          ) : null}
        </div>
      </div>

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

      <div className="flex justify-end gap-2">
        <Button
          type="submit"
          disabled={isSubmitting || create.isPending}
          data-testid="backtest-submit"
        >
          {create.isPending ? "요청 중…" : "백테스트 실행"}
        </Button>
      </div>
    </form>
  );
}
