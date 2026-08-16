"use client";

// TV "거래 분석" 섹션 — KPI(평균 PnL/평균 거래 바수/최대 수익/최대 손실) +
// 수익 분포 histogram + 거래 분포 donut. 방향별 성과는 기존 TradeAnalysis 유지
// (heatmap 은 상세 결과 > 수익률 서브탭으로 이동).

import { useMemo } from "react";

import { computeOutcomeCounts } from "@/features/backtest/analytics";
import type {
  BacktestMetricsOut,
  TradeItem,
} from "@/features/backtest/schemas";
import { formatCurrency, formatPercent } from "@/features/backtest/utils";

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
      <span className={`font-mono text-lg font-bold tabular-nums ${toneClass}`}>
        {value}
      </span>
      {sub ? (
        <span className="font-mono text-xs tabular-nums text-muted-foreground">
          {sub}
        </span>
      ) : null}
    </div>
  );
}

export function TradeAnalyticsSection({
  metrics: m,
  trades,
  truncated = false,
}: TradeAnalyticsSectionProps) {
  const closed = useMemo(
    () => trades.filter((t) => t.status === "closed"),
    [trades],
  );
  const counts = useMemo(
    () => computeOutcomeCounts(closed.map((t) => t.pnl)),
    [closed],
  );

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
          tone={
            avgPnlAbs !== null ? (avgPnlAbs >= 0 ? "bullish" : "bearish") : "neutral"
          }
        />
        <Kpi
          label="평균 거래 바수"
          value={m.avg_bars_in_trade != null ? m.avg_bars_in_trade.toFixed(1) : "—"}
          sub={
            m.avg_holding_hours != null
              ? `평균 보유 ${m.avg_holding_hours.toFixed(1)}h`
              : null
          }
        />
        <Kpi
          label="최대 수익 거래"
          value={
            m.largest_win_abs != null
              ? `+${formatCurrency(m.largest_win_abs)} USDT`
              : "—"
          }
          sub={m.best_trade_pct != null ? `+${formatPercent(m.best_trade_pct)}` : null}
          tone="bullish"
        />
        <Kpi
          label="최대 손실 거래"
          value={
            m.largest_loss_abs != null
              ? `${formatCurrency(m.largest_loss_abs)} USDT`
              : "—"
          }
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
    </section>
  );
}
