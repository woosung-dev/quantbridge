// Sprint 43 W11 — 거래 내역 stats strip (4 mini stat 카드).
// 총 거래 / 평균 수익 / 평균 손실 / 평균 보유 시간 — 거래 배열로부터 즉석 집계.
"use client";

import { useMemo } from "react";

import type { TradeItem } from "@/features/backtest/schemas";
import { formatPercent } from "@/features/backtest/utils";

interface TradeStatsStripProps {
  trades: readonly TradeItem[];
}

interface AggregatedStats {
  totalCount: number;
  winCount: number;
  lossCount: number;
  /** 승리 거래 평균 return_pct (decimal). */
  avgWinPct: number;
  /** 승리 거래 max return_pct (decimal). */
  maxWinPct: number;
  /** 패배 거래 평균 return_pct (decimal, 음수). */
  avgLossPct: number;
  /** 패배 거래 min return_pct (decimal, 음수). */
  minLossPct: number;
  /** 평균 보유 시간 (분 단위). 0이면 데이터 없음. */
  avgHoldMinutes: number;
  /** 보유 시간 중앙값 (분). */
  medianHoldMinutes: number;
}

export function TradeStatsStrip({ trades }: TradeStatsStripProps) {
  const stats = useMemo(() => aggregate(trades), [trades]);

  return (
    <section
      aria-label="거래 요약 통계"
      className="grid grid-cols-2 gap-3 sm:grid-cols-4"
      data-testid="trade-stats-strip"
    >
      <StatCard
        label="총 거래"
        value={stats.totalCount.toString()}
        sub={`${stats.winCount}승 ${stats.lossCount}패`}
      />
      <StatCard
        label="평균 수익"
        value={
          stats.winCount > 0 ? formatPercent(stats.avgWinPct) : "—"
        }
        sub={
          stats.winCount > 0 ? `최대 ${formatPercent(stats.maxWinPct)}` : "데이터 없음"
        }
        tone="pos"
      />
      <StatCard
        label="평균 손실"
        value={
          stats.lossCount > 0 ? formatPercent(stats.avgLossPct) : "—"
        }
        sub={
          stats.lossCount > 0
            ? `최대 ${formatPercent(stats.minLossPct)}`
            : "데이터 없음"
        }
        tone="neg"
      />
      <StatCard
        label="평균 보유 시간"
        value={
          stats.avgHoldMinutes > 0 ? formatHold(stats.avgHoldMinutes) : "—"
        }
        sub={
          stats.medianHoldMinutes > 0
            ? `중앙값 ${formatHold(stats.medianHoldMinutes)}`
            : "데이터 없음"
        }
      />
    </section>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  tone?: "pos" | "neg" | "neutral";
}

function StatCard({ label, value, sub, tone = "neutral" }: StatCardProps) {
  const toneClass =
    tone === "pos"
      ? "text-emerald-600"
      : tone === "neg"
        ? "text-rose-600"
        : "text-foreground";
  return (
    <div className="rounded-lg border bg-card px-4 py-3">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div
        className={`font-mono text-xl font-bold leading-tight ${toneClass}`}
        data-testid={`trade-stat-${label}`}
      >
        {value}
      </div>
      {sub ? (
        <div className="mt-1 text-xs text-muted-foreground">{sub}</div>
      ) : null}
    </div>
  );
}

function aggregate(trades: readonly TradeItem[]): AggregatedStats {
  const wins = trades.filter((t) => t.pnl > 0);
  const losses = trades.filter((t) => t.pnl <= 0 && t.exit_time !== null);

  const winPcts = wins
    .map((t) => t.return_pct)
    .filter((v) => Number.isFinite(v));
  const lossPcts = losses
    .map((t) => t.return_pct)
    .filter((v) => Number.isFinite(v));

  const avgWinPct =
    winPcts.length > 0 ? winPcts.reduce((a, b) => a + b, 0) / winPcts.length : 0;
  const maxWinPct = winPcts.length > 0 ? Math.max(...winPcts) : 0;
  const avgLossPct =
    lossPcts.length > 0
      ? lossPcts.reduce((a, b) => a + b, 0) / lossPcts.length
      : 0;
  const minLossPct = lossPcts.length > 0 ? Math.min(...lossPcts) : 0;

  const holdMinutes = trades
    .map((t) => {
      if (!t.exit_time) return 0;
      const ms = new Date(t.exit_time).getTime() - new Date(t.entry_time).getTime();
      return ms > 0 && Number.isFinite(ms) ? Math.round(ms / 60000) : 0;
    })
    .filter((v) => v > 0);

  const avgHoldMinutes =
    holdMinutes.length > 0
      ? holdMinutes.reduce((a, b) => a + b, 0) / holdMinutes.length
      : 0;
  const medianHoldMinutes =
    holdMinutes.length > 0
      ? [...holdMinutes].sort((a, b) => a - b)[Math.floor(holdMinutes.length / 2)] ?? 0
      : 0;

  return {
    totalCount: trades.length,
    winCount: wins.length,
    lossCount: losses.length,
    avgWinPct,
    maxWinPct,
    avgLossPct,
    minLossPct,
    avgHoldMinutes,
    medianHoldMinutes,
  };
}

function formatHold(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)}m`;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return `${h}h ${m}m`;
}
