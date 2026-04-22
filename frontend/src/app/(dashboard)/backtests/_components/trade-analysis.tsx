"use client";

import { useMemo } from "react";

import { cn } from "@/lib/utils";
import {
  computeDirectionBreakdown,
  type DirectionBreakdown,
  type DirectionStats,
} from "@/features/backtest/utils";
import type {
  BacktestMetricsOut,
  TradeItem,
} from "@/features/backtest/schemas";

interface TradeAnalysisProps {
  metrics: BacktestMetricsOut;
  /**
   * 거래 목록(optional). 제공 시 방향별 성과 section 추가 렌더링.
   * 제공되지 않으면 기존 동작 (집계 기반 section 만) 유지.
   */
  trades?: readonly TradeItem[];
}

export function TradeAnalysis({ metrics, trades }: TradeAnalysisProps) {
  const { num_trades, win_rate, long_count, short_count, avg_win, avg_loss } =
    metrics;
  const winCount = Math.round(win_rate * num_trades);
  const lossCount = num_trades - winCount;
  const winPct = num_trades > 0 ? (winCount / num_trades) * 100 : 0;
  const maxAbsAvg = Math.max(
    Math.abs(avg_win ?? 0),
    Math.abs(avg_loss ?? 0),
  );

  // LESSON-004: dep array 는 부모로부터 전달된 stable trades reference 만 사용.
  // React Query 의 result 객체 자체를 dep 로 쓰지 않음 (부모 컴포넌트가 items 만 전달).
  const breakdown = useMemo<DirectionBreakdown | null>(() => {
    if (!trades || trades.length === 0) return null;
    return computeDirectionBreakdown(trades);
  }, [trades]);

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

      {/* 방향별 성과 (W4 신규) */}
      {breakdown &&
      (breakdown.long.count > 0 || breakdown.short.count > 0) ? (
        <section>
          <SectionTitle>방향별 성과</SectionTitle>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <DirectionStatsCard
              label="롱"
              stats={breakdown.long}
              color="green"
            />
            <DirectionStatsCard
              label="숏"
              stats={breakdown.short}
              color="red"
            />
          </div>
          {/* 부분집합 안내: trades 배열 길이 < metrics.num_trades 인 경우 사용자에게 명시.
              거래 목록 탭도 동일한 200건 cap 을 가지므로 거기로 안내하지 않고 사실만 표기. */}
          {trades &&
          num_trades > 0 &&
          trades.length < num_trades ? (
            <p className="mt-2 text-xs text-[color:var(--text-muted)]">
              * 표시된 거래 {trades.length}건 기준 (전체 {num_trades}건 중).
            </p>
          ) : null}
        </section>
      ) : null}

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

// W4: 방향별 성과 카드 (롱/숏 각각 1장).
function DirectionStatsCard({
  label,
  stats,
  color,
}: {
  label: string;
  stats: DirectionStats;
  color: "green" | "red";
}) {
  const colorClass = color === "green" ? "text-green-500" : "text-red-500";
  if (stats.count === 0) {
    return (
      <div className="rounded-md border border-[color:var(--border)] px-4 py-3">
        <p className={cn("text-xs font-semibold uppercase", colorClass)}>
          {label}
        </p>
        <p className="mt-1 text-sm text-[color:var(--text-muted)]">거래 없음</p>
      </div>
    );
  }
  const sign = stats.avgPnl >= 0 ? "+" : "";
  return (
    <div className="rounded-md border border-[color:var(--border)] px-4 py-3">
      <p className={cn("text-xs font-semibold uppercase", colorClass)}>
        {label} · {stats.count}건
      </p>
      <dl className="mt-2 space-y-1 text-sm">
        <div className="flex justify-between">
          <dt className="text-[color:var(--text-muted)]">승률</dt>
          <dd className="font-mono">{(stats.winRate * 100).toFixed(1)}%</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-[color:var(--text-muted)]">평균 PnL</dt>
          <dd className="font-mono">
            {sign}
            {stats.avgPnl.toFixed(2)}
          </dd>
        </div>
      </dl>
    </div>
  );
}
