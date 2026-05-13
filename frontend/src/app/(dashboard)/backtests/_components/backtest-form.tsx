// 백테스트 폼 — Sprint 59 PR-E 5-split shell (Sizing/Cost/Session/TradingSessions fieldset + useBacktestForm hook).
"use client";

import { toast } from "sonner";

import { FormErrorInline } from "@/components/form-error-inline";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useStrategies } from "@/features/strategy/hooks";
import type { StrategyListItem } from "@/features/strategy/schemas";

import { BacktestCostFieldSet } from "./BacktestCostFieldSet";
import { BacktestSessionFieldSet } from "./BacktestSessionFieldSet";
import { BacktestSizingFieldSet } from "./BacktestSizingFieldSet";
import { BacktestTradingSessionsFieldSet } from "./BacktestTradingSessionsFieldSet";
import { SetupSummaryAside } from "./setup-summary-aside";
import { useBacktestForm } from "./useBacktestForm";

export function BacktestForm() {
  const strategies = useStrategies({ limit: 100, offset: 0, is_archived: false });
  const {
    form,
    handleSubmit,
    onSubmit,
    submitError,
    convertResult,
    setConvertResult,
    datePreset,
    setDatePreset,
    handleDatePreset,
    strategy,
    liveLeverage,
    livePct,
    create,
  } = useBacktestForm();

  const {
    register,
    setValue,
    control,
    formState: { errors, isSubmitting },
  } = form;

  const strategyItems: StrategyListItem[] = strategies.data?.items ?? [];
  // useWatch via control 은 자식 FieldSet 안에서 호출 (LESSON-004 H-1 정합 — 각 자식이 자체 watch).
  // Aside 와 strategy select 만 form-level watch 가 필요하므로 form.watch() 사용 (RHF stable getter).
  const watchedSymbol = form.watch("symbol");
  const watchedTfReady = form.watch("timeframe");
  const watchedPeriodStart = form.watch("period_start");
  const watchedPeriodEnd = form.watch("period_end");
  const watchedCapital = form.watch("initial_capital");
  const watchedPositionPct = form.watch("position_size_pct");
  const watchedLeverage = form.watch("leverage");
  const watchedFees = form.watch("fees_pct");
  const watchedSlippage = form.watch("slippage_pct");
  const watchedQtyType = form.watch("default_qty_type");
  const watchedQtyValue = form.watch("default_qty_value");
  const sizingSource = form.watch("sizing_source");
  const selectedStrategy = form.watch("strategy_id");
  const selectedStrategyName = strategyItems.find(
    (s) => s.id === selectedStrategy,
  )?.name;

  return (
    <div
      className="grid grid-cols-1 gap-6 md:grid-cols-[2fr_1fr]"
      data-testid="backtest-form-layout"
    >
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="flex flex-col gap-5 rounded-[14px] border bg-card p-7 shadow-[var(--card-shadow)]"
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

        <BacktestSessionFieldSet
          control={control}
          register={register}
          setValue={setValue}
          errors={errors}
          datePreset={datePreset}
          setDatePreset={setDatePreset}
          onDatePreset={handleDatePreset}
        />

        <BacktestCostFieldSet register={register} errors={errors} />

        <BacktestSizingFieldSet
          control={control}
          register={register}
          setValue={setValue}
          errors={errors}
          liveLeverage={liveLeverage}
          livePct={livePct}
        />

        <BacktestTradingSessionsFieldSet control={control} setValue={setValue} />

        {/* Sprint 37 BL-187 → BL-187a: 모델 정보 (1x · 롱/숏). */}
        <section
          className="border-t pt-4"
          aria-label="시뮬레이션 모델"
          data-testid="backtest-form-model-section"
        >
          <div className="rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
            <p className="mb-1 font-medium text-foreground">
              모델: 1x · 롱/숏
            </p>
            <p>
              1x 비레버리지. 롱/숏 모두 가능 (자기자본 한도 내).{" "}
              <span className="text-muted-foreground/80">
                funding rate / 강제 청산 / 유지 증거금 미반영 (BL-186 후속).
              </span>
            </p>
          </div>
        </section>

        <FormErrorInline
          error={submitError}
          editStrategyHref={
            selectedStrategy
              ? `/strategies/${selectedStrategy}/edit?tab=parse`
              : null
          }
          testIdPrefix="backtest-form"
          indicatorCode={strategy?.pine_source ?? null}
          onConverted={setConvertResult}
        />

        {/* pine-compat-experiment — AI 변환 결과 표시. */}
        {convertResult ? (
          <div className="rounded-md border border-violet-300 bg-violet-50 p-3 text-sm dark:border-violet-700 dark:bg-violet-950">
            <p className="mb-1 font-semibold text-violet-900 dark:text-violet-200">
              AI 변환 결과 — 검토 후 새 strategy 로 저장하세요.
            </p>
            {convertResult.warnings.length > 0 ? (
              <ul className="mb-2 list-inside list-disc space-y-0.5 text-xs text-violet-800 dark:text-violet-300">
                {convertResult.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            ) : null}
            <textarea
              readOnly
              value={convertResult.converted_code}
              rows={12}
              className="w-full rounded border border-violet-200 bg-white p-2 font-mono text-xs leading-relaxed text-gray-900 dark:border-violet-700 dark:bg-gray-900 dark:text-gray-100"
            />
            <button
              type="button"
              className="mt-2 text-xs text-violet-700 underline hover:opacity-80 dark:text-violet-300"
              onClick={() => {
                void navigator.clipboard.writeText(convertResult.converted_code);
                toast.success("클립보드에 복사됨");
              }}
            >
              클립보드에 복사
            </button>
          </div>
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

      <SetupSummaryAside
        strategyName={selectedStrategyName}
        formValues={{
          symbol: watchedSymbol,
          timeframe: watchedTfReady,
          period_start: watchedPeriodStart,
          period_end: watchedPeriodEnd,
          initial_capital: watchedCapital,
          position_size_pct: watchedPositionPct,
          default_qty_type: watchedQtyType,
          default_qty_value: watchedQtyValue,
          sizing_source: sizingSource,
          leverage: watchedLeverage,
          fees_pct: watchedFees,
          slippage_pct: watchedSlippage,
        }}
      />
    </div>
  );
}
