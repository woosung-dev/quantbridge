"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
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
import {
  getUnsupportedBuiltinHints,
  type UnsupportedBuiltinHint,
} from "@/lib/unsupported-builtin-hints";

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
  // Sprint 31 BL-162a — TradingView strategy 속성 패턴 (비용 시뮬레이션 + 마진).
  // 기본값 = Bybit Perpetual taker 표준 (1x 현물 / 0.10% 수수료 / 0.05% 슬리피지 / 펀딩 ON).
  leverage: number;
  fees_pct: number;
  slippage_pct: number;
  include_funding: boolean;
}

function toIsoUtc(dateOnly: string): string {
  // "YYYY-MM-DD" → "YYYY-MM-DDT00:00:00Z". 경계 외 값은 Date 파싱 실패.
  return new Date(`${dateOnly}T00:00:00Z`).toISOString();
}

export function BacktestForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialStrategyId = searchParams.get("strategy_id") ?? "";
  const strategies = useStrategies({ limit: 100, offset: 0, is_archived: false });

  const {
    register,
    handleSubmit,
    setValue,
    setError,
    clearErrors,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    // Sprint 13 Phase C: 첫 제출 전에도 필드 단위 에러 노출 (시작일/종료일 누락 등)
    mode: "onChange",
    defaultValues: {
      strategy_id: initialStrategyId,
      symbol: "BTC/USDT",
      timeframe: "1h",
      period_start: "",
      period_end: "",
      initial_capital: 10000,
      // Sprint 31 BL-162a — Bybit Perpetual taker 표준 default.
      leverage: 1,
      fees_pct: 0.001,
      slippage_pct: 0.0005,
      include_funding: true,
    },
  });

  // Sprint 21 BL-095 — 422 응답의 unsupported_builtins (구조화 list) 가 있을 때
  // form-level error message 가 아닌 inline 카드로 친절 표시. 빈 list 면 fallback.
  const [unsupportedHints, setUnsupportedHints] = useState<
    UnsupportedBuiltinHint[]
  >([]);

  const create = useCreateBacktest({
    onSuccess: (data) => {
      toast.success("백테스트 요청됨");
      router.push(`/backtests/${data.backtest_id}`);
    },
    onError: (err) => {
      // 매 호출 reset.
      setUnsupportedHints([]);
      // Sprint 13 Phase C: 422 백엔드 응답은 form-level inline 에러로 표시.
      // ApiError 는 numeric `status` 를 보존하므로 안전하게 narrow 한다.
      const status = (err as { status?: number }).status;
      if (status === 422) {
        // Sprint 21 BL-095: ApiError.detail = readErrorBody 결과 =
        // {detail: {code, detail, unsupported_builtins}} (FastAPI HTTPException 표준).
        // backend Phase A.0 가 list 추가. FE 는 string split 안 하고 list 직접 접근.
        const apiErr = err as {
          detail?: {
            detail?: { unsupported_builtins?: unknown };
          };
        };
        const list = apiErr.detail?.detail?.unsupported_builtins;
        if (
          Array.isArray(list) &&
          list.every((x) => typeof x === "string") &&
          list.length > 0
        ) {
          setUnsupportedHints(getUnsupportedBuiltinHints(list as string[]));
          return;
        }
        setError("root.serverError", {
          type: "manual",
          message: err.message || "입력값이 유효하지 않습니다",
        });
      } else {
        toast.error(`요청 실패: ${err.message}`);
      }
    },
  });

  const onSubmit: SubmitHandler<FormValues> = (values) => {
    // 재제출 시 직전 422 form-level 에러 메시지 + unsupported list 클리어.
    clearErrors("root.serverError");
    setUnsupportedHints([]);
    create.mutate({
      strategy_id: values.strategy_id,
      symbol: values.symbol,
      timeframe: values.timeframe,
      period_start: toIsoUtc(values.period_start),
      period_end: toIsoUtc(values.period_end),
      initial_capital: Number(values.initial_capital),
      // Sprint 31 BL-162a — 사용자 입력 비용/마진 4 필드.
      leverage: Number(values.leverage),
      fees_pct: Number(values.fees_pct),
      slippage_pct: Number(values.slippage_pct),
      include_funding: Boolean(values.include_funding),
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

      {/* Sprint 31 BL-162a — 비용 시뮬레이션 (TradingView strategy 속성 패턴).
          기본값 = Bybit Perpetual taker 표준. 사용자가 자기 strategy 환경에 맞게 변경. */}
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

      {/* Sprint 31 BL-162a — 마진 / 레버리지 (TradingView strategy 속성 패턴).
          leverage=1 = 현물, >1 = Perpetual 선물. Bybit max 125x. */}
      <section
        className="border-t pt-4"
        aria-label="마진 / 레버리지"
        data-testid="backtest-form-margin-section"
      >
        <h3 className="mb-3 text-sm font-medium">마진 / 레버리지</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="leverage" className="text-sm">
              레버리지 (배, 1 = 현물)
            </label>
            <Input
              id="leverage"
              type="number"
              step="0.5"
              min={1}
              max={125}
              {...register("leverage", {
                required: "레버리지를 입력하세요",
                valueAsNumber: true,
                validate: (v) =>
                  (Number.isFinite(v) && v >= 1 && v <= 125) ||
                  "1 ~ 125 범위여야 합니다",
              })}
            />
            {errors.leverage ? (
              <p className="text-xs text-destructive">
                {errors.leverage.message}
              </p>
            ) : null}
          </div>
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="include_funding"
              className="text-sm flex items-center gap-2"
            >
              <input
                id="include_funding"
                type="checkbox"
                className="h-4 w-4"
                {...register("include_funding")}
              />
              펀딩비 반영 (8h 무기한 선물)
            </label>
          </div>
        </div>
      </section>

      {unsupportedHints.length > 0 ? (
        <div
          role="alert"
          data-testid="backtest-form-unsupported-card"
          className="rounded border border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950 p-3 text-sm"
        >
          <p className="font-semibold text-amber-900 dark:text-amber-200 mb-1">
            ⚠️ 이 strategy 는 미지원 builtin 을 포함합니다
          </p>
          <ul className="list-disc list-inside space-y-1 text-amber-800 dark:text-amber-300 text-xs">
            {unsupportedHints.map((h) => (
              <li key={h.name}>
                <span className="font-mono">{h.name}</span> — {h.hint}
              </li>
            ))}
          </ul>
          {selectedStrategy ? (
            <Link
              href={`/strategies/${selectedStrategy}/edit?tab=parse`}
              className="mt-2 inline-block text-xs underline text-amber-900 dark:text-amber-200"
              data-testid="backtest-form-edit-strategy-link"
            >
              strategy 편집 →
            </Link>
          ) : null}
        </div>
      ) : errors.root?.serverError?.message ? (
        <p
          className="text-sm text-destructive"
          role="alert"
          data-testid="backtest-form-server-error"
        >
          {errors.root.serverError.message}
        </p>
      ) : null}

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
