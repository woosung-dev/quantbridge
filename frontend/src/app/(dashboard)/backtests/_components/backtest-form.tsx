"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm, useWatch, type SubmitHandler } from "react-hook-form";
import { toast } from "sonner";

import { FormErrorInline } from "@/components/form-error-inline";
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
import type {
  ConvertIndicatorResponse,
  Timeframe,
  TradingSession,
} from "@/features/backtest/schemas";
import { useStrategies, useStrategy } from "@/features/strategy/hooks";
import type { StrategyListItem } from "@/features/strategy/schemas";

import {
  DatePresetPills,
  calcDateRange,
  type DatePreset,
} from "./date-preset-pills";
import {
  LiveSettingsBadge,
  type SizingSource,
} from "./live-settings-badge";
import { PositionSizeSlider } from "./position-size-slider";
import { SetupSummaryAside } from "./setup-summary-aside";

const TIMEFRAMES: readonly Timeframe[] = [
  "1m",
  "5m",
  "15m",
  "1h",
  "4h",
  "1d",
] as const;

// Sprint 31 BL-167 — date default helper. 6개월 default (180일) UX 마찰 제거.
function toYmd(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function defaultPeriodEnd(): string {
  // 어제 (오늘 미완성 일봉 회피, ts.ohlcv backfill 정합)
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return toYmd(d);
}

function defaultPeriodStart(): string {
  // -180일 (6개월) — 충분한 trade 발생 + monthly_returns heatmap 의미 있음
  const d = new Date();
  d.setDate(d.getDate() - 181);
  return toYmd(d);
}

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
  // Sprint 37 BL-188a — 폼 default_qty_type/value (Pine 미명시 시 사용).
  default_qty_type:
    | "strategy.percent_of_equity"
    | "strategy.cash"
    | "strategy.fixed";
  default_qty_value: number;
  // Sprint 38 BL-188 v3 — D2 manual override toggle + Live mirror canonical.
  // sizing_source 가 "live" 일 때 position_size_pct 만 submit, "manual" 일 때
  // default_qty_type/value 만 submit (canonical 1개 강제). pine / live_blocked_leverage
  // 는 read-only 상태 — toggle UI disabled.
  sizing_source: SizingSource;
  position_size_pct: number | null;
  trading_sessions: TradingSession[];
}

// Sprint 38 BL-188 v3 — strategy detail 의 Pine declaration optional. BE A2 가
// `pine_declared_qty` 추가 예정. 그 전까지는 undefined → manual fallback (4-state
// 배지의 "pine" 상태는 future-ready, 본 sprint 에선 stub 으로 테스트만 검증).
type StrategyWithPine = {
  pine_declared_qty?: { type?: string | null; value?: number | null } | null;
};

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
    control,
    reset,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    // Sprint 13 Phase C: 첫 제출 전에도 필드 단위 에러 노출 (시작일/종료일 누락 등)
    mode: "onChange",
    defaultValues: {
      strategy_id: initialStrategyId,
      symbol: "BTC/USDT",
      timeframe: "1h",
      // Sprint 31 BL-167 — UX 개선: default 6개월 (180일). 사용자 의향 = 매번
      // 입력 마찰 제거. period_end = 어제 (오늘 미완성 일봉 회피), period_start
      // = -180일.
      period_start: defaultPeriodStart(),
      period_end: defaultPeriodEnd(),
      initial_capital: 10000,
      // Sprint 31 BL-162a — Bybit Perpetual taker 표준 default.
      leverage: 1,
      fees_pct: 0.001,
      slippage_pct: 0.0005,
      include_funding: true,
      // Sprint 37 BL-188a — default 주문 크기 percent_of_equity 10%.
      // Pine 명시 시 그게 우선 (override). 사용자가 dropdown 변경 가능.
      default_qty_type: "strategy.percent_of_equity",
      default_qty_value: 10,
      // Sprint 38 BL-188 v3 — D2 sizing source canonical 기본 manual (strategy
      // detail fetch 전). useStrategy 데이터 도착 시 reset() 으로 prefill.
      sizing_source: "manual",
      position_size_pct: null,
      trading_sessions: [],
    },
  });

  // Sprint 41 E — 단일 submitError state. FormErrorInline 가 422 unsupported_builtins
  // / friendly_message / general fallback 분기 처리. (이전: 3개 분리 state + RHF root.serverError)
  const [submitError, setSubmitError] = useState<unknown>(null);
  // pine-compat-experiment — AI 변환 결과 state. unsupported 케이스에서 CTA 클릭 시 채워짐.
  const [convertResult, setConvertResult] =
    useState<ConvertIndicatorResponse | null>(null);

  const create = useCreateBacktest({
    onSuccess: (data) => {
      toast.success("백테스트 요청됨");
      router.push(`/backtests/${data.backtest_id}`);
    },
    onError: (err) => {
      const status = (err as { status?: number }).status;
      // 422 만 inline 카드. 5xx / 기타는 toast 단독 (이전 동작 보존).
      if (status === 422) {
        setSubmitError(err);
        return;
      }
      setSubmitError(null);
      if (status != null && status >= 500) {
        // Sprint 32 E (BL-163): 500+ 표준화 toast — backend `{detail: <msg>}` 정규화.
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
          `백테스트 실행 중 오류 발생: ${detailMsg}. ADR-003 supported list 의 indicator 로 strategy 를 변경해 주세요.`,
        );
      } else {
        toast.error(`요청 실패: ${err.message}`);
      }
    },
  });

  const onSubmit: SubmitHandler<FormValues> = (values) => {
    // 재제출 시 직전 422 form-level 에러 메시지 + unsupported list 클리어.
    setSubmitError(null);
    // Sprint 38 BL-188 v3 — D2 canonical 1개 강제. sizing_source 에 따라 BE 로
    // 한쪽만 보냄. BE `_no_double_sizing` 422 회피 + Zod `.refine()` parity.
    const isLive = values.sizing_source === "live";
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
      // Sprint 38 BL-188 v3 — sizing canonical: live → position_size_pct,
      // manual/pine/blocked → default_qty_type/value (manual fallback).
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

  const strategyItems: StrategyListItem[] = strategies.data?.items ?? [];
  const selectedStrategy = useWatch({ control, name: "strategy_id" });
  const selectedTimeframe = useWatch({ control, name: "timeframe" });
  const sizingSource = useWatch({ control, name: "sizing_source" });
  const watchedSessions = useWatch({ control, name: "trading_sessions" });

  // Sprint 42-polish W4 — date preset pill 활성 상태 (custom = 직접 입력 또는
  // preset 매칭 안 됨). preset 클릭 시 startDate / endDate 자동 update.
  const [datePreset, setDatePreset] = useState<DatePreset>("6m");

  // Sprint 42-polish W4 — sizing source 가 live / pine 이 아닐 때 슬라이더로
  // default_qty_value 조작. percent_of_equity 가 아니면 슬라이더 hide (수량/USDT
  // 는 input 에 그대로 위임).
  const watchedQtyType = useWatch({ control, name: "default_qty_type" });
  const watchedQtyValue = useWatch({ control, name: "default_qty_value" });
  const watchedSymbol = useWatch({ control, name: "symbol" });
  const watchedTfReady = useWatch({ control, name: "timeframe" });
  const watchedPeriodStart = useWatch({ control, name: "period_start" });
  const watchedPeriodEnd = useWatch({ control, name: "period_end" });
  const watchedCapital = useWatch({ control, name: "initial_capital" });
  const watchedPositionPct = useWatch({ control, name: "position_size_pct" });
  const watchedLeverage = useWatch({ control, name: "leverage" });
  const watchedFees = useWatch({ control, name: "fees_pct" });
  const watchedSlippage = useWatch({ control, name: "slippage_pct" });
  const selectedStrategyName = strategyItems.find(
    (s) => s.id === selectedStrategy,
  )?.name;

  const handleDatePreset = (preset: DatePreset) => {
    setDatePreset(preset);
    const range = calcDateRange(preset);
    if (range) {
      setValue("period_start", range.startDate, { shouldDirty: true });
      setValue("period_end", range.endDate, { shouldDirty: true });
    }
  };

  // Sprint 38 BL-188 v3 — strategy detail fetch (settings + trading_sessions
  // prefill 용). 기존 useStrategy 훅 재사용 (queryKey factory + userId scoping).
  const { data: strategy } = useStrategy(selectedStrategy || undefined);

  // Sprint 38 BL-188 v3 — Pine declaration optional probe (BE A2 후 활성).
  const pineDeclared = Boolean(
    (strategy as StrategyWithPine | undefined)?.pine_declared_qty?.type,
  );
  const liveLeverage = strategy?.settings?.leverage ?? null;
  const livePct = strategy?.settings?.position_size_pct ?? null;

  // Sprint 38 BL-188 v3 — strategy detail 도착 시 reset() 으로 prefill.
  // LESSON-004: dep 는 5 scalar primitive (strategyId / livePct / liveLeverage /
  // sessionsKey / pineDeclared) + react-hook-form stable callback (reset, getValues).
  // closure 내부에서 strategy object 자체를 직접 참조하지 않음 — 모든 read 는
  // 위 scalar 추출값 기준. react-hooks/exhaustive-deps 자연 정합 (disable X).
  const strategyId = strategy?.id ?? null;
  const sessionsKey = strategy?.trading_sessions?.join("|") ?? "";
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

      {/* Sprint 42-polish W4 — date preset pills (1M/3M/6M/1Y/3Y/5Y + 커스텀). */}
      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium">기간 프리셋</span>
        <DatePresetPills value={datePreset} onSelect={handleDatePreset} />
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

      {/* Sprint 38 BL-188 v3 — D2 sizing source canonical 1개 (Live mirror /
          Manual). Pine 명시 시 read-only badge + 폼 disabled. Live Nx 시 mirror
          차단 + manual 입력만 가능. 사용자 토글 가능 시 select 활성화. */}
      <section
        className="border-t pt-4"
        aria-label="주문 크기 source"
        data-testid="backtest-form-sizing-source-section"
      >
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-medium">주문 크기 source</h3>
          <LiveSettingsBadge
            source={sizingSource}
            liveLeverage={liveLeverage}
            livePct={livePct}
          />
        </div>

        {sizingSource === "pine" ? (
          <p className="mb-3 text-xs text-muted-foreground">
            Pine code <code>strategy(default_qty_type=...)</code> 명시 — Pine
            override 가 우선 적용됩니다. 폼 입력 비활성화.
          </p>
        ) : sizingSource === "live_blocked_leverage" ? (
          <p className="mb-3 text-xs text-muted-foreground">
            Live leverage {liveLeverage ?? 0}x — backtest 1x equity-basis 와
            비대칭으로 mirror 차단. Manual 입력만 가능 (BL-186 후 unlock).
          </p>
        ) : (
          <div className="mb-3 flex flex-col gap-1.5">
            <label htmlFor="sizing_source" className="text-xs">
              source 선택
            </label>
            <select
              id="sizing_source"
              data-testid="sizing-source-select"
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={sizingSource}
              onChange={(e) => {
                const next = e.target.value as SizingSource;
                if (next === "live") {
                  setValue("sizing_source", "live", { shouldDirty: true });
                  setValue(
                    "position_size_pct",
                    livePct ?? null,
                    { shouldDirty: true },
                  );
                } else {
                  setValue("sizing_source", "manual", { shouldDirty: true });
                  setValue("position_size_pct", null, { shouldDirty: true });
                }
              }}
            >
              <option value="manual">Manual 입력 (form 우선)</option>
              {livePct != null && liveLeverage === 1 ? (
                <option value="live">Live mirror (Strategy.settings)</option>
              ) : null}
            </select>
          </div>
        )}

        {sizingSource === "live" ? (
          <div className="flex flex-col gap-1.5">
            <label htmlFor="position_size_pct" className="text-sm">
              Live position_size_pct (%, Live mirror)
            </label>
            <Input
              id="position_size_pct"
              type="number"
              step="any"
              min={0}
              max={100}
              readOnly
              data-testid="position-size-pct-input"
              {...register("position_size_pct", {
                valueAsNumber: true,
              })}
            />
            <p className="text-xs text-muted-foreground">
              Strategy.settings.position_size_pct 와 동일. 변경하려면 Manual 로
              전환 또는 Strategy 편집.
            </p>
            {errors.position_size_pct ? (
              <p className="text-xs text-destructive">
                {errors.position_size_pct.message}
              </p>
            ) : null}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="default_qty_type" className="text-sm">
                type
              </label>
              <select
                id="default_qty_type"
                className="h-10 rounded-md border bg-background px-3 text-sm disabled:opacity-50"
                disabled={sizingSource === "pine"}
                data-testid="default-qty-type-select"
                {...register("default_qty_type", {
                  required:
                    sizingSource === "pine"
                      ? false
                      : "주문 크기 type 을 선택하세요",
                })}
              >
                <option value="strategy.percent_of_equity">
                  자기자본 % (percent_of_equity)
                </option>
                <option value="strategy.cash">고정 USDT (cash)</option>
                <option value="strategy.fixed">고정 수량 (fixed)</option>
              </select>
              {errors.default_qty_type ? (
                <p className="text-xs text-destructive">
                  {errors.default_qty_type.message}
                </p>
              ) : null}
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="default_qty_value" className="text-sm">
                value
              </label>
              <Input
                id="default_qty_value"
                type="number"
                step="any"
                min={0}
                disabled={sizingSource === "pine"}
                data-testid="default-qty-value-input"
                {...register("default_qty_value", {
                  required:
                    sizingSource === "pine"
                      ? false
                      : "주문 크기 값을 입력하세요",
                  valueAsNumber: true,
                  validate: (v) =>
                    sizingSource === "pine" ||
                    (Number.isFinite(v) && v > 0) ||
                    "양수여야 합니다",
                })}
              />
              {errors.default_qty_value ? (
                <p className="text-xs text-destructive">
                  {errors.default_qty_value.message}
                </p>
              ) : null}
            </div>
          </div>
        )}

        {/* Sprint 42-polish W4 — percent_of_equity 일 때 슬라이더로 직접 조작.
            sizing_source = pine / live 일 때는 hide (read-only / live mirror). */}
        {sizingSource !== "pine" &&
        sizingSource !== "live" &&
        watchedQtyType === "strategy.percent_of_equity" ? (
          <div className="mt-4">
            <PositionSizeSlider
              value={
                Number.isFinite(watchedQtyValue) && watchedQtyValue > 0
                  ? Math.min(100, Math.max(1, Number(watchedQtyValue)))
                  : 10
              }
              onChange={(v) =>
                setValue("default_qty_value", v, { shouldDirty: true })
              }
              capitalUsd={
                Number.isFinite(watchedCapital) ? Number(watchedCapital) : null
              }
              label="포지션 사이즈"
              unit="%"
              min={1}
              max={100}
              step={1}
            />
          </div>
        ) : null}
      </section>

      {/* Sprint 38 BL-188 v3 — Live Sessions mirror (asia/london/ny). 빈 list
          = 24h. Strategy.trading_sessions 자동 prefill. 사용자가 checkbox
          토글로 override 가능. */}
      <section
        className="border-t pt-4"
        aria-label="trading sessions"
        data-testid="backtest-form-trading-sessions-section"
      >
        <h3 className="mb-3 text-sm font-medium">Trading Sessions</h3>
        <p className="mb-2 text-xs text-muted-foreground">
          Live Strategy.trading_sessions mirror. 빈 선택 = 24시간 거래.
        </p>
        <div className="flex flex-wrap gap-3">
          {(["asia", "london", "ny"] as const).map((s) => {
            const checked = (watchedSessions ?? []).includes(s);
            return (
              <label
                key={s}
                className="flex items-center gap-1.5 text-sm"
                data-testid={`session-checkbox-${s}`}
              >
                <input
                  type="checkbox"
                  className="h-4 w-4"
                  checked={checked}
                  onChange={(e) => {
                    const current = (watchedSessions ?? []).filter(
                      (x): x is TradingSession => x !== s,
                    );
                    const next: TradingSession[] = e.target.checked
                      ? [...current, s]
                      : current;
                    setValue("trading_sessions", next, {
                      shouldDirty: true,
                    });
                  }}
                />
                <span className="capitalize">{s}</span>
              </label>
            );
          })}
        </div>
      </section>

      {/* Sprint 37 BL-187 → BL-187a: 라벨 simplify (사용자 오해 회피).
          "Spot-equivalent" 단어가 "현물 = 롱만" 오해 유발 — 실제는 롱/숏 모두 가능.
          레버리지 멘션 자체 minimize (사용자 명시). BL-186 후속 도래 시 재노출 검토. */}
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

      {/* pine-compat-experiment — AI 변환 결과 표시 (code textarea + 경고). */}
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

    {/* Sprint 42-polish W4 — 우측 1fr summary aside (mobile 시 stack 아래로). */}
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
