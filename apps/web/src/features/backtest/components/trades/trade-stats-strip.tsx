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
  /** 미청산 건수 — 승/패 어느 쪽도 아니다(BL-822). totalCount = win + loss + open. */
  openCount: number;
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
      {/* ★BL-822 — 총 거래는 나열된 행 수(미청산 포함)이고 승/패는 청산된 것만 센다.
          미청산을 안 적으면 「총 거래 13 · 2승 10패」처럼 더해서 안 맞는 표기가 된다. */}
      <StatKpi
        label="총 거래"
        value={stats.totalCount.toString()}
        foot={
          stats.openCount > 0
            ? `${stats.winCount}승 ${stats.lossCount}패 · 미청산 ${stats.openCount}건`
            : `${stats.winCount}승 ${stats.lossCount}패`
        }
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
  // ★미청산 거래는 `exit_time === null` 이고 pnl 이 진입 수수료만큼 **음수**라, 걸러내지
  //   않으면 패배로 세어진다(losses 필터가 이미 그렇게 하고 있었다). wins 도 같은 모수여야
  //   총계가 닫힌다 — 미청산은 별도로 센다(BL-822).
  let winCount = 0;
  let lossCount = 0;
  let openCount = 0;
  let winPctCount = 0;
  let lossPctCount = 0;
  let winPctSum = 0;
  let lossPctSum = 0;
  let maxWinPct = -Infinity;
  let minLossPct = Infinity;
  let holdSum = 0;
  const holdMinutes: number[] = [];

  // 승패·유한 수익률·보유 시간을 한 번에 모은다. 중앙값만 정렬이 필요하다.
  for (const trade of trades) {
    if (trade.exit_time === null) {
      openCount += 1;
    } else if (trade.pnl > 0) {
      winCount += 1;
      if (Number.isFinite(trade.return_pct)) {
        winPctCount += 1;
        winPctSum += trade.return_pct;
        maxWinPct = Math.max(maxWinPct, trade.return_pct);
      }
    } else if (trade.pnl <= 0) {
      lossCount += 1;
      if (Number.isFinite(trade.return_pct)) {
        lossPctCount += 1;
        lossPctSum += trade.return_pct;
        minLossPct = Math.min(minLossPct, trade.return_pct);
      }
    }
    if (!trade.exit_time) continue;
    const ms = new Date(trade.exit_time).getTime() - new Date(trade.entry_time).getTime();
    const minutes = ms > 0 && Number.isFinite(ms) ? Math.round(ms / 60000) : 0;
    if (minutes > 0) {
      holdMinutes.push(minutes);
      holdSum += minutes;
    }
  }

  const avgWinPct = winPctCount > 0 ? winPctSum / winPctCount : 0;
  const avgLossPct = lossPctCount > 0 ? lossPctSum / lossPctCount : 0;
  if (winPctCount === 0) maxWinPct = 0;
  if (lossPctCount === 0) minLossPct = 0;
  const avgHoldMinutes = holdMinutes.length > 0 ? holdSum / holdMinutes.length : 0;
  const medianHoldMinutes =
    holdMinutes.length > 0
      ? (holdMinutes.sort((a, b) => a - b)[Math.floor(holdMinutes.length / 2)] ?? 0)
      : 0;

  return {
    totalCount: trades.length,
    winCount,
    lossCount,
    openCount,
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
