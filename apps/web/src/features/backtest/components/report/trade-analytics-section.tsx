"use client";

// TV "거래 분석" 섹션 — KPI(평균 PnL/평균 거래 바수/최대 수익/최대 손실) +
// 수익 분포 histogram + 거래 분포 donut + 방향별 성과 표
// (heatmap 은 상세 결과 > 수익률 서브탭으로 이동).
// 방향별 성과는 구 TradeAnalysis(trades/trade-analysis.tsx, 2026-08-18 삭제)에서 흡수했다 —
// 방향 분포 카운트(metrics.long_count/short_count)와 방향별 승률·평균 PnL(trades 파생)을
// 한 표로 합쳤다. 승/패 비율·평균 수익 vs 손실 바는 donut·histogram 마커와 중복이라 승계하지 않는다.

import { useMemo } from "react";

import { computeOutcomeCounts } from "@/features/backtest/analytics";
import type { BacktestMetricsOut, TradeItem } from "@/features/backtest/schemas";
import {
  computeDirectionBreakdown,
  formatCurrency,
  formatPercent,
  type DirectionBreakdown,
  type DirectionStats,
} from "@/features/backtest/utils";

import { PnlDistributionHistogram } from "@/features/backtest/components/report/pnl-distribution-histogram";
import { TradeOutcomeDonut } from "@/features/backtest/components/report/trade-outcome-donut";

interface TradeAnalyticsSectionProps {
  metrics: BacktestMetricsOut;
  trades: readonly TradeItem[];
  truncated?: boolean;
}

function Kpi({
  label,
  value,
  sub,
  tone = "neutral",
}: {
  label: string;
  value: string;
  sub?: string | null;
  tone?: "bullish" | "bearish" | "neutral";
}) {
  const toneClass =
    tone === "bullish"
      ? "text-[color:var(--bullish)]"
      : tone === "bearish"
        ? "text-[color:var(--bearish)]"
        : "text-foreground";
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
        {label}
      </span>
      <span className={`font-mono text-lg font-bold tabular-nums ${toneClass}`}>{value}</span>
      {sub ? (
        <span className="font-mono text-xs tabular-nums text-muted-foreground">{sub}</span>
      ) : null}
    </div>
  );
}

// 방향별 성과 표 한 행 — 거래 수는 metrics 카운트(전체 모집단) 우선, 없으면 trades 파생으로 폴백.
// 승률·평균 PnL 은 trades 파생(stats)이 있고 해당 방향 거래가 있을 때만 수치 표시.
function DirectionRow({
  label,
  tone,
  count,
  stats,
}: {
  label: string;
  tone: "pos" | "neg";
  count: number | null;
  stats: DirectionStats | null;
}) {
  const hasStats = stats !== null && stats.count > 0;
  const pnlSign = hasStats && stats.avgPnl >= 0 ? "+" : "";
  return (
    <tr>
      <td className="py-1.5">
        <span className={`text-xs font-semibold uppercase ${tone}`}>{label}</span>
      </td>
      <td className="py-1.5 text-right font-mono tabular-nums">{count != null ? count : "—"}</td>
      <td className="py-1.5 text-right font-mono tabular-nums">
        {hasStats ? formatPercent(stats.winRate, 1) : "—"}
      </td>
      <td
        className={`py-1.5 text-right font-mono tabular-nums ${
          hasStats ? (stats.avgPnl >= 0 ? "pos" : "neg") : ""
        }`}
      >
        {hasStats ? `${pnlSign}${formatCurrency(stats.avgPnl)}` : "—"}
      </td>
    </tr>
  );
}

export function TradeAnalyticsSection({
  metrics: m,
  trades,
  truncated = false,
}: TradeAnalyticsSectionProps) {
  const closed = useMemo(() => trades.filter((t) => t.status === "closed"), [trades]);
  const counts = useMemo(() => computeOutcomeCounts(closed.map((t) => t.pnl)), [closed]);

  // LESSON-004: dep 는 부모가 내려준 stable trades reference 만 사용 (구 TradeAnalysis 관례 승계).
  const breakdown = useMemo<DirectionBreakdown | null>(() => {
    if (trades.length === 0) return null;
    return computeDirectionBreakdown(trades);
  }, [trades]);

  // 승률·평균 PnL 은 로드된 trades 표본 파생, 거래 수는 metrics 모집단 — 표본이 전체의
  // 부분집합이면(캡 초과 truncated) 헤더 * + 각주로 두 분모를 갈라 고지한다 (codex P2).
  const statsFromSubset = trades.length > 0 && m.num_trades > 0 && trades.length < m.num_trades;

  const avgPnlAbs = m.avg_trade_abs ?? null;

  return (
    <section className="space-y-6" data-testid="trade-analytics-section">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi
          label="평균 PnL"
          value={
            avgPnlAbs !== null
              ? `${avgPnlAbs >= 0 ? "+" : ""}${formatCurrency(avgPnlAbs)} USDT`
              : "—"
          }
          sub={m.avg_trade_pct != null ? formatPercent(m.avg_trade_pct) : null}
          tone={avgPnlAbs !== null ? (avgPnlAbs >= 0 ? "bullish" : "bearish") : "neutral"}
        />
        <Kpi
          label="평균 거래 바수"
          value={m.avg_bars_in_trade != null ? m.avg_bars_in_trade.toFixed(1) : "—"}
          sub={m.avg_holding_hours != null ? `평균 보유 ${m.avg_holding_hours.toFixed(1)}h` : null}
        />
        <Kpi
          label="최대 수익 거래"
          value={m.largest_win_abs != null ? `+${formatCurrency(m.largest_win_abs)} USDT` : "—"}
          sub={m.best_trade_pct != null ? `+${formatPercent(m.best_trade_pct)}` : null}
          tone="bullish"
        />
        <Kpi
          label="최대 손실 거래"
          value={m.largest_loss_abs != null ? `${formatCurrency(m.largest_loss_abs)} USDT` : "—"}
          sub={m.worst_trade_pct != null ? formatPercent(m.worst_trade_pct) : null}
          tone="bearish"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
            수익 분포
          </h3>
          <PnlDistributionHistogram
            trades={closed}
            avgWinPct={m.avg_win}
            avgLossPct={m.avg_loss}
            truncated={truncated}
            totalTrades={m.num_trades}
          />
        </div>
        <div>
          <h3 className="mb-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
            거래 분포
          </h3>
          <TradeOutcomeDonut counts={counts} />
        </div>
      </div>

      {/* 방향별 성과 — 구 TradeAnalysis 흡수분. 캐논상 채움 트랙 바 대신 mono 수치 표. */}
      <div>
        <h3 className="mb-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
          방향별 성과
        </h3>
        <table
          className="w-full max-w-md text-sm"
          aria-label="방향별 성과"
          data-testid="direction-breakdown-table"
        >
          <thead>
            <tr className="text-xs text-muted-foreground">
              <th className="py-1.5 text-left font-medium">방향</th>
              <th className="py-1.5 text-right font-medium">거래 수</th>
              {/* ★분모 분리 고지 — 거래 수는 metrics 모집단, 승률·평균 PnL 은 로드된 표본
                  (MAX_ANALYTICS_TRADES cap) 파생이라 truncated 시 한 행에 두 분모가 공존한다
                  (codex P2). 표본이 부분집합일 때만 * 를 붙여 아래 각주와 결속한다. */}
              <th className="py-1.5 text-right font-medium">승률{statsFromSubset ? "*" : ""}</th>
              <th className="py-1.5 text-right font-medium">
                평균 PnL{statsFromSubset ? "*" : ""}
              </th>
            </tr>
          </thead>
          <tbody>
            <DirectionRow
              label="롱"
              tone="pos"
              count={m.long_count ?? breakdown?.long.count ?? null}
              stats={breakdown?.long ?? null}
            />
            <DirectionRow
              label="숏"
              tone="neg"
              count={m.short_count ?? breakdown?.short.count ?? null}
              stats={breakdown?.short ?? null}
            />
          </tbody>
        </table>
        {/* 부분집합 안내 — 구 TradeAnalysis 의 disclosure 승계. 거래 목록 탭도 같은 cap 을
            가지므로 거기로 안내하지 않고 사실만 표기. */}
        {statsFromSubset ? (
          <p className="mt-2 text-xs text-muted-foreground">
            * 표시된 거래 {trades.length}건 기준 (전체 {m.num_trades}건 중). 거래 수 열은 전체
            기준입니다.
          </p>
        ) : null}
      </div>
    </section>
  );
}
