// 백테스트 폼의 거래 세션 필드 (asia/london/ny) — C 디자인 언어 이식(W3-A).
"use client";

import { useWatch, type Control, type UseFormSetValue } from "react-hook-form";

import type { TradingSession } from "@/features/backtest/schemas";

import type { BacktestFormValues } from "@/app/(dashboard)/backtests/_components/forms/useBacktestForm";

const SESSION_LABEL: Record<TradingSession, string> = {
  asia: "아시아",
  london: "런던",
  ny: "뉴욕",
};

interface BacktestTradingSessionsFieldSetProps {
  control: Control<BacktestFormValues>;
  setValue: UseFormSetValue<BacktestFormValues>;
}

export function BacktestTradingSessionsFieldSet({
  control,
  setValue,
}: BacktestTradingSessionsFieldSetProps) {
  const watchedSessions = useWatch({ control, name: "trading_sessions" });

  return (
    <section
      className="sizing-block"
      aria-label="거래 세션"
      data-testid="backtest-form-trading-sessions-section"
    >
      <div className="sizing-head">
        <div>
          <h3 className="card-title">거래 세션</h3>
          <p className="card-sub">
            Live 전략의 거래 세션을 미러합니다. 선택하지 않으면 24시간 거래로
            봅니다.
          </p>
        </div>
      </div>
      <div className="tabs" role="group" aria-label="거래 세션 선택">
        {(["asia", "london", "ny"] as const).map((s) => {
          const checked = (watchedSessions ?? []).includes(s);
          return (
            <button
              key={s}
              type="button"
              className={checked ? "tab active" : "tab"}
              aria-pressed={checked}
              data-testid={`session-checkbox-${s}`}
              onClick={() => {
                const current = (watchedSessions ?? []).filter(
                  (x): x is TradingSession => x !== s,
                );
                const next: TradingSession[] = checked
                  ? current
                  : [...current, s];
                setValue("trading_sessions", next, { shouldDirty: true });
              }}
            >
              {SESSION_LABEL[s]}
            </button>
          );
        })}
      </div>
    </section>
  );
}
