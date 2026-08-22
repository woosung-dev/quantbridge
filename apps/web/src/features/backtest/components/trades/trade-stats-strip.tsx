// 거래 요약 통계 — C 디자인 언어 이식(S6). 공용 .kpi-row/.kpi 를 소비한다.
// 총 거래 / 평균 수익 / 평균 손실 / 평균 보유 — 로드된 거래 배열로부터 즉석 집계.
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
    <ul
      className="kpi-row m-0 list-none p-0"
      aria-label="거래 요약 통계"
      data-testid="trade-stats-strip"
    >
      <StatKpi
        label="총 거래"
        value={stats.totalCount.toString()}
        foot={`${stats.winCount}승 ${stats.lossCount}패`}
      />
      <StatKpi
        label="평균 수익"
        value={stats.winCount > 0 ? formatPercent(stats.avgWinPct) : "—"}
        foot={stats.winCount > 0 ? `최대 ${formatPercent(stats.maxWinPct)}` : "데이터 없음"}
        tone="pos"
      />
      <StatKpi
        label="평균 손실"
        value={stats.lossCount > 0 ? formatPercent(stats.avgLossPct) : "—"}
        foot={stats.lossCount > 0 ? `최대 ${formatPercent(stats.minLossPct)}` : "데이터 없음"}
        tone="neg"
      />
      <StatKpi
        label="평균 보유 시간"
        value={stats.avgHoldMinutes > 0 ? formatHold(stats.avgHoldMinutes) : "—"}
        foot={
          stats.medianHoldMinutes > 0
            ? `중앙값 ${formatHold(stats.medianHoldMinutes)}`
            : "데이터 없음"
        }
      />
    </ul>
  );
}

interface StatKpiProps {
  label: string;
  value: string;
  foot?: string;
  tone?: "pos" | "neg" | "neutral";
}

function StatKpi({ label, value, foot, tone = "neutral" }: StatKpiProps) {
  const valueClass =
    tone === "pos"
      ? "kpi-value mono pos"
      : tone === "neg"
        ? "kpi-value mono neg"
        : "kpi-value mono";
  return (
    <li className="card kpi">
      <p className="kpi-label">{label}</p>
      <p className={valueClass} data-testid={`trade-stat-${label}`}>
        {value}
      </p>
      {foot ? (
        <p className="kpi-foot">
          <span>{foot}</span>
        </p>
      ) : null}
    </li>
  );
}

function aggregate(trades: readonly TradeItem[]): AggregatedStats {
  const wins = trades.filter((t) => t.pnl > 0);
  const losses = trades.filter((t) => t.pnl <= 0 && t.exit_time !== null);

  const winPcts = wins.map((t) => t.return_pct).filter((v) => Number.isFinite(v));
  const lossPcts = losses.map((t) => t.return_pct).filter((v) => Number.isFinite(v));

  const avgWinPct = winPcts.length > 0 ? winPcts.reduce((a, b) => a + b, 0) / winPcts.length : 0;
  const maxWinPct = winPcts.length > 0 ? Math.max(...winPcts) : 0;
  const avgLossPct =
    lossPcts.length > 0 ? lossPcts.reduce((a, b) => a + b, 0) / lossPcts.length : 0;
  const minLossPct = lossPcts.length > 0 ? Math.min(...lossPcts) : 0;

  const holdMinutes = trades
    .map((t) => {
      if (!t.exit_time) return 0;
      const ms = new Date(t.exit_time).getTime() - new Date(t.entry_time).getTime();
      return ms > 0 && Number.isFinite(ms) ? Math.round(ms / 60000) : 0;
    })
    .filter((v) => v > 0);

  const avgHoldMinutes =
    holdMinutes.length > 0 ? holdMinutes.reduce((a, b) => a + b, 0) / holdMinutes.length : 0;
  const medianHoldMinutes =
    holdMinutes.length > 0
      ? ([...holdMinutes].sort((a, b) => a - b)[Math.floor(holdMinutes.length / 2)] ?? 0)
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
