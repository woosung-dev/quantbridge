"use client";

import { useForm } from "react-hook-form";
import { zodV4Resolver } from "@/lib/zod-v4-resolver";
import { ApiError, describeApiError } from "@/lib/api-client";
import { backtestDraft } from "../defaults";
import { PythonBacktestDraftSchema, type PythonBacktestDraft } from "../schemas";

const NUMERIC_FIELDS = [
  {
    name: "initial_capital",
    label: "초기 자본 (USDT)",
    help: "레버리지 1배 · 단일 포지션 · 최대 투자 비중 100%",
  },
  { name: "fees", label: "편도 수수료 비율", help: "0.00055 = 0.055%" },
  { name: "slippage", label: "슬리피지 비율", help: "0.00014 = 0.014%" },
] as const;

export function BacktestForm({
  canRun,
  disabledReason,
  isStarting,
  error,
  onRun,
}: {
  canRun: boolean;
  disabledReason: string | null;
  isStarting: boolean;
  error: Error | null;
  onRun: (draft: PythonBacktestDraft) => void;
}) {
  const form = useForm<PythonBacktestDraft>({
    resolver: zodV4Resolver(PythonBacktestDraftSchema),
    defaultValues: backtestDraft(),
  });
  const errors = form.formState.errors;
  return (
    <section className="card" aria-label="Python 백테스트 설정">
      <div className="card-head">
        <div>
          <h2 className="card-title">백테스트 조건</h2>
          <p className="card-sub">
            Bybit USDT 무기한 · 확정 봉 · 다음 봉 시가 체결 · 실제 펀딩 반영
          </p>
        </div>
      </div>
      <form onSubmit={form.handleSubmit(onRun)} className="card-body space-y-4">
        <div className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="field">
            <label className="field-label" htmlFor="python-symbol">
              종목
            </label>
            <select className="select w-full" id="python-symbol" {...form.register("symbol")}>
              <option value="BTC/USDT">BTC/USDT 무기한</option>
              <option value="ETH/USDT">ETH/USDT 무기한</option>
            </select>
          </div>
          <div className="field">
            <label className="field-label" htmlFor="python-timeframe">
              시간봉
            </label>
            <select className="select w-full" id="python-timeframe" {...form.register("timeframe")}>
              <option value="1h">1시간봉</option>
              <option value="4h">4시간봉</option>
              <option value="1d">일봉</option>
            </select>
          </div>
          <div className="field">
            <label className="field-label" htmlFor="python-start">
              시작일 (UTC)
            </label>
            <input
              className="input"
              type="date"
              id="python-start"
              {...form.register("period_start")}
              aria-invalid={Boolean(errors.period_start)}
            />
            {errors.period_start ? (
              <p className="field-error" role="alert">
                {errors.period_start.message}
              </p>
            ) : null}
          </div>
          <div className="field">
            <label className="field-label" htmlFor="python-end">
              종료일 (UTC, 미포함)
            </label>
            <input
              className="input"
              type="date"
              id="python-end"
              {...form.register("period_end")}
              aria-invalid={Boolean(errors.period_end)}
            />
            {errors.period_end ? (
              <p className="field-error" role="alert">
                {errors.period_end.message}
              </p>
            ) : null}
          </div>
        </div>
        <div className="grid min-w-0 gap-4 md:grid-cols-3">
          {NUMERIC_FIELDS.map(({ name, label, help }) => (
            <div className="field" key={name}>
              <label className="field-label" htmlFor={`python-${name}`}>
                {label}
              </label>
              <input
                className="input mono"
                id={`python-${name}`}
                inputMode="decimal"
                {...form.register(name)}
                aria-invalid={Boolean(errors[name])}
              />
              <p className="text-sm text-muted-foreground">{help}</p>
              {errors[name] ? (
                <p className="field-error" role="alert">
                  {errors[name]?.message}
                </p>
              ) : null}
            </div>
          ))}
        </div>
        {disabledReason ? (
          <p role="status" className="strip-note">
            {disabledReason}
          </p>
        ) : null}
        {error ? (
          <p role="alert" className="field-error">
            {error instanceof ApiError && error.code === "python_strategy_version_conflict"
              ? "다른 곳에서 새 버전이 저장되었습니다. 저장된 전략을 다시 선택한 뒤 실행하세요."
              : describeApiError(error, "백테스트를 시작하지 못했습니다")}
          </p>
        ) : null}
        <button type="submit" className="btn btn-primary" disabled={!canRun || isStarting}>
          {isStarting ? "시작 중…" : "저장한 버전으로 백테스트"}
        </button>
      </form>
    </section>
  );
}
