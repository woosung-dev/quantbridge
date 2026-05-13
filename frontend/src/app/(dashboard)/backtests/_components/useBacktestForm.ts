// 백테스트 폼의 form state machine + 비즈니스 로직 훅 (Sprint 59 PR-E split).
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useForm, useWatch, type SubmitHandler } from "react-hook-form";
import { toast } from "sonner";

import { useCreateBacktest } from "@/features/backtest/hooks";
import type {
  ConvertIndicatorResponse,
  Timeframe,
  TradingSession,
} from "@/features/backtest/schemas";
import { useStrategy } from "@/features/strategy/hooks";

import { calcDateRange, type DatePreset } from "./date-preset-pills";
import { type SizingSource } from "./live-settings-badge";

export interface BacktestFormValues {
  strategy_id: string;
  symbol: string;
  timeframe: Timeframe;
  period_start: string;
  period_end: string;
  initial_capital: number;
  leverage: number;
  fees_pct: number;
  slippage_pct: number;
  include_funding: boolean;
  default_qty_type:
    | "strategy.percent_of_equity"
    | "strategy.cash"
    | "strategy.fixed";
  default_qty_value: number;
  sizing_source: SizingSource;
  position_size_pct: number | null;
  trading_sessions: TradingSession[];
}

// Sprint 38 BL-188 v3 — Pine declaration optional probe (BE A2 후 활성).
type StrategyWithPine = {
  pine_declared_qty?: { type?: string | null; value?: number | null } | null;
};

// Sprint 31 BL-167 — date default helper. 6개월 default (180일) UX 마찰 제거.
function toYmd(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function defaultPeriodEnd(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return toYmd(d);
}

function defaultPeriodStart(): string {
  const d = new Date();
  d.setDate(d.getDate() - 181);
  return toYmd(d);
}

function detectSizingSource(
  pineDeclared: boolean,
  liveLeverage: number | null,
  livePct: number | null,
): SizingSource {
  if (pineDeclared) return "pine";
  if (liveLeverage != null && liveLeverage !== 1) return "live_blocked_leverage";
  if (livePct != null) return "live";
  return "manual";
}

function toIsoUtc(dateOnly: string): string {
  return new Date(`${dateOnly}T00:00:00Z`).toISOString();
}

export function useBacktestForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialStrategyId = searchParams.get("strategy_id") ?? "";

  const form = useForm<BacktestFormValues>({
    mode: "onChange",
    defaultValues: {
      strategy_id: initialStrategyId,
      symbol: "BTC/USDT",
      timeframe: "1h",
      period_start: defaultPeriodStart(),
      period_end: defaultPeriodEnd(),
      initial_capital: 10000,
      leverage: 1,
      fees_pct: 0.001,
      slippage_pct: 0.0005,
      include_funding: true,
      default_qty_type: "strategy.percent_of_equity",
      default_qty_value: 10,
      sizing_source: "manual",
      position_size_pct: null,
      trading_sessions: [],
    },
  });

  const { control, setValue, reset, getValues, handleSubmit } = form;

  const [submitError, setSubmitError] = useState<unknown>(null);
  const [convertResult, setConvertResult] =
    useState<ConvertIndicatorResponse | null>(null);
  const [datePreset, setDatePreset] = useState<DatePreset>("6m");

  const create = useCreateBacktest({
    onSuccess: (data) => {
      toast.success("백테스트 요청됨");
      router.push(`/backtests/${data.backtest_id}`);
    },
    onError: (err) => {
      const status = (err as { status?: number }).status;
      if (status === 422) {
        setSubmitError(err);
        return;
      }
      setSubmitError(null);
      if (status != null && status >= 500) {
        const apiErr = err as { detail?: { detail?: unknown } | unknown };
        let detailMsg = err.message;
        if (
          apiErr.detail &&
          typeof apiErr.detail === "object" &&
          "detail" in apiErr.detail &&
          typeof apiErr.detail.detail === "string"
        ) {
          detailMsg = apiErr.detail.detail;
        }
        toast.error(
          `백테스트 실행 중 오류 발생: ${detailMsg}. 지원 함수 목록 참조 후 strategy 를 변경해 주세요.`,
        );
      } else {
        toast.error(`요청 실패: ${err.message}`);
      }
    },
  });

  const onSubmit: SubmitHandler<BacktestFormValues> = (values) => {
    setSubmitError(null);
    const isLive = values.sizing_source === "live";
    create.mutate({
      strategy_id: values.strategy_id,
      symbol: values.symbol,
      timeframe: values.timeframe,
      period_start: toIsoUtc(values.period_start),
      period_end: toIsoUtc(values.period_end),
      initial_capital: Number(values.initial_capital),
      leverage: Number(values.leverage),
      fees_pct: Number(values.fees_pct),
      slippage_pct: Number(values.slippage_pct),
      include_funding: Boolean(values.include_funding),
      ...(isLive
        ? {
            position_size_pct:
              values.position_size_pct != null
                ? Number(values.position_size_pct)
                : undefined,
          }
        : {
            default_qty_type: values.default_qty_type,
            default_qty_value: Number(values.default_qty_value),
          }),
      trading_sessions: values.trading_sessions ?? [],
    });
  };

  // Sprint 38 BL-188 v3 — strategy detail fetch (settings + trading_sessions prefill).
  const selectedStrategy = useWatch({ control, name: "strategy_id" });
  const { data: strategy } = useStrategy(selectedStrategy || undefined);

  const pineDeclared = Boolean(
    (strategy as StrategyWithPine | undefined)?.pine_declared_qty?.type,
  );
  const liveLeverage = strategy?.settings?.leverage ?? null;
  const livePct = strategy?.settings?.position_size_pct ?? null;
  const strategyId = strategy?.id ?? null;
  const sessionsKey = strategy?.trading_sessions?.join("|") ?? "";

  // LESSON-004 H-1: dep 는 5 scalar primitive + RHF stable callback. strategy object 직접 참조 금지.
  useEffect(() => {
    if (!strategyId) return;
    const computedSource = detectSizingSource(pineDeclared, liveLeverage, livePct);
    const allowedSessions: TradingSession[] = sessionsKey
      ? sessionsKey
          .split("|")
          .filter((s): s is TradingSession =>
            s === "asia" || s === "london" || s === "ny",
          )
      : [];
    const current = getValues();
    reset(
      {
        ...current,
        sizing_source: computedSource,
        position_size_pct:
          computedSource === "live" && livePct != null ? livePct : null,
        trading_sessions: allowedSessions,
      },
      { keepDirtyValues: false },
    );
  }, [
    strategyId,
    livePct,
    liveLeverage,
    sessionsKey,
    pineDeclared,
    reset,
    getValues,
  ]);

  const handleDatePreset = useCallback(
    (preset: DatePreset) => {
      setDatePreset(preset);
      const range = calcDateRange(preset);
      if (range) {
        setValue("period_start", range.startDate, { shouldDirty: true });
        setValue("period_end", range.endDate, { shouldDirty: true });
      }
    },
    [setValue],
  );

  return {
    form,
    handleSubmit,
    onSubmit,
    submitError,
    setSubmitError,
    convertResult,
    setConvertResult,
    datePreset,
    setDatePreset,
    handleDatePreset,
    strategy,
    pineDeclared,
    liveLeverage,
    livePct,
    create,
  };
}
