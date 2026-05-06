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
    },
  });

  // Sprint 21 BL-095 — 422 응답의 unsupported_builtins (구조화 list) 가 있을 때
  // form-level error message 가 아닌 inline 카드로 친절 표시. 빈 list 면 fallback.
  const [unsupportedHints, setUnsupportedHints] = useState<
    UnsupportedBuiltinHint[]
  >([]);
  // Sprint 32 E (BL-163) — backend 422 의 friendly_message (사용자 친화 단일 요약)
  // 가 있으면 카드 헤더에 노출. backend 가 coverage workaround SSOT 기반으로 합성.
  const [friendlyMessage, setFriendlyMessage] = useState<string | null>(null);

  const create = useCreateBacktest({
    onSuccess: (data) => {
      toast.success("백테스트 요청됨");
      router.push(`/backtests/${data.backtest_id}`);
    },
    onError: (err) => {
      // 매 호출 reset.
      setUnsupportedHints([]);
      setFriendlyMessage(null);
      // Sprint 13 Phase C: 422 백엔드 응답은 form-level inline 에러로 표시.
      // ApiError 는 numeric `status` 를 보존하므로 안전하게 narrow 한다.
      const status = (err as { status?: number }).status;
      if (status === 422) {
        // Sprint 21 BL-095: ApiError.detail = readErrorBody 결과 =
        // {detail: {code, detail, unsupported_builtins}} (FastAPI HTTPException 표준).
        // backend Phase A.0 가 list 추가. FE 는 string split 안 하고 list 직접 접근.
        // Sprint 32 E (BL-163): friendly_message 도 함께 추출 — 카드 헤더 노출.
        const apiErr = err as {
          detail?: {
            detail?: {
              unsupported_builtins?: unknown;
              degraded_calls?: unknown;
              friendly_message?: unknown;
            };
          };
        };
        const inner = apiErr.detail?.detail;
        const list = inner?.unsupported_builtins ?? inner?.degraded_calls;
        const fm = inner?.friendly_message;
        if (typeof fm === "string" && fm.length > 0) {
          setFriendlyMessage(fm);
        }
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
      } else if ((status ?? 500) >= 500) {
        // Sprint 32 E (BL-163): 500+ 표준화 toast — backend unhandled_exc_handler 가
        // `{detail: <human-readable>}` 정규화 응답을 반환. ADR-003 supported list 안내.
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
    clearErrors("root.serverError");
    setUnsupportedHints([]);
    setFriendlyMessage(null);
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
      // Sprint 37 BL-188a — 폼 default_qty (Pine 미명시 시 사용).
      default_qty_type: values.default_qty_type,
      default_qty_value: Number(values.default_qty_value),
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

      {/* Sprint 37 BL-188a: 기본 주문 크기 (default_qty_type/value).
          Pine strategy(default_qty_type=...) 명시 시 그게 우선 (override).
          미명시 시 폼 입력 사용 → silent qty=1.0 fallback 차단 (image 12 의 -249% 회귀 방지). */}
      <section
        className="border-t pt-4"
        aria-label="기본 주문 크기"
        data-testid="backtest-form-default-qty-section"
      >
        <h3 className="mb-3 text-sm font-medium">기본 주문 크기</h3>
        <p className="mb-2 text-xs text-muted-foreground">
          Pine code 의 <code>strategy(default_qty_type=...)</code> 명시 시 그게
          우선. 미명시 시 아래 입력값 사용.
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="default_qty_type" className="text-sm">
              type
            </label>
            <select
              id="default_qty_type"
              className="h-10 rounded-md border bg-background px-3 text-sm"
              {...register("default_qty_type", {
                required: "주문 크기 type 을 선택하세요",
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
              {...register("default_qty_value", {
                required: "주문 크기 값을 입력하세요",
                valueAsNumber: true,
                validate: (v) =>
                  (Number.isFinite(v) && v > 0) || "양수여야 합니다",
              })}
            />
            {errors.default_qty_value ? (
              <p className="text-xs text-destructive">
                {errors.default_qty_value.message}
              </p>
            ) : null}
          </div>
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

      {unsupportedHints.length > 0 ? (
        <div
          role="alert"
          data-testid="backtest-form-unsupported-card"
          className="rounded border border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950 p-3 text-sm"
        >
          <p className="font-semibold text-amber-900 dark:text-amber-200 mb-1">
            이 strategy 는 미지원 builtin 을 포함합니다
          </p>
          {/* Sprint 32 E (BL-163): backend friendly_message 가 있으면 카드 헤더 아래
              한 줄 요약으로 우선 노출 (사용자가 list 를 읽기 전 결정 가능). */}
          {friendlyMessage ? (
            <p
              className="text-xs text-amber-900 dark:text-amber-200 mb-2"
              data-testid="backtest-form-friendly-message"
            >
              {friendlyMessage}
            </p>
          ) : null}
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
              ADR-003 supported list 참조 — strategy 편집 →
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
