"use client";

import { cn } from "@/lib/utils";
import type { BacktestMetricsOut } from "@/features/backtest/schemas";

interface TradeAnalysisProps {
  metrics: BacktestMetricsOut;
}

export function TradeAnalysis({ metrics }: TradeAnalysisProps) {
  const { num_trades, win_rate, long_count, short_count, avg_win, avg_loss } =
    metrics;
  const winCount = Math.round(win_rate * num_trades);
  const lossCount = num_trades - winCount;
  const winPct = num_trades > 0 ? (winCount / num_trades) * 100 : 0;
  const maxAbsAvg = Math.max(
    Math.abs(avg_win ?? 0),
    Math.abs(avg_loss ?? 0),
  );

  return (
    <div className="space-y-8">
      {/* 방향 분포 */}
      <section>
        <SectionTitle>방향 분포</SectionTitle>
        <div className="flex flex-wrap gap-3">
          <DirectionBadge label="롱" value={long_count} />
          <DirectionBadge label="숏" value={short_count} />
          <DirectionBadge label="전체" value={num_trades} />
        </div>
      </section>

      {/* 승/패 비율 */}
      <section>
        <SectionTitle>승/패 비율</SectionTitle>
        <div className="flex items-center gap-3 text-sm">
          <span className="w-14 text-right font-medium text-green-500">
            {winCount}건
          </span>
          <div className="h-4 flex-1 overflow-hidden rounded-full bg-[color:var(--muted)]">
            <div
              className="h-full rounded-full bg-green-500 transition-all duration-300"
              style={{ width: `${winPct}%` }}
            />
          </div>
          <span className="w-14 font-medium text-red-500">{lossCount}건</span>
        </div>
        <p className="mt-1 text-center text-xs text-[color:var(--text-muted)]">
          승률 {winPct.toFixed(1)}% · 패률 {(100 - winPct).toFixed(1)}%
        </p>
      </section>

      {/* 평균 수익 vs 손실 */}
      {avg_win != null && avg_loss != null ? (
        <section>
          <SectionTitle>평균 수익 vs 손실</SectionTitle>
          <div className="space-y-3">
            <RatioBar
              label="평균 수익"
              value={avg_win}
              max={maxAbsAvg}
              colorClass="bg-green-500"
            />
            <RatioBar
              label="평균 손실"
              value={Math.abs(avg_loss)}
              max={maxAbsAvg}
              colorClass="bg-red-500"
            />
          </div>
        </section>
      ) : (
        <p className="text-sm text-[color:var(--text-muted)]">
          평균 수익/손실 데이터가 없습니다 (이전 버전 백테스트).
        </p>
      )}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-[color:var(--text-muted)]">
      {children}
    </h3>
  );
}

function DirectionBadge({
  label,
  value,
}: {
  label: string;
  value: number | null | undefined;
}) {
  return (
    <div className="flex items-baseline gap-1.5 rounded-md border border-[color:var(--border)] px-4 py-2">
      <span className="text-xs text-[color:var(--text-muted)]">{label}</span>
      <span className="text-xl font-bold">{value ?? "—"}</span>
      {value != null && (
        <span className="text-xs text-[color:var(--text-muted)]">건</span>
      )}
    </div>
  );
}

function RatioBar({
  label,
  value,
  max,
  colorClass,
}: {
  label: string;
  value: number;
  max: number;
  colorClass: string;
}) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-20 text-[color:var(--text-secondary)]">{label}</span>
      <div className="h-3 flex-1 overflow-hidden rounded-full bg-[color:var(--muted)]">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-300",
            colorClass,
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-16 text-right font-mono text-xs">
        {(value * 100).toFixed(2)}%
      </span>
    </div>
  );
}
