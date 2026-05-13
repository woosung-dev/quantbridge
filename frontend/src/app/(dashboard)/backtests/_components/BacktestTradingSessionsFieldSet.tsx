// 백테스트 폼의 Trading Sessions checkbox (asia/london/ny) — Sprint 59 PR-E split.
"use client";

import { useWatch, type Control, type UseFormSetValue } from "react-hook-form";

import type { TradingSession } from "@/features/backtest/schemas";

import type { BacktestFormValues } from "./useBacktestForm";

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
  );
}
