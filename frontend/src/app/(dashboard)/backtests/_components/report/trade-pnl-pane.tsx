"use client";

// TV 성과 차트의 per-trade PnL 바 pane — 청산 시각 × 순손익(USDT) 히스토그램
// lightweight-charts HistogramSeries (per-point 녹/적 = chart-tokens bullish/bearish).

import { useMemo } from "react";

import {
  TradingChart,
  type ChartPoint,
  type HistogramPoint,
} from "@/components/charts/trading-chart";
import { useChartTheme } from "@/lib/chart-tokens";
import type { TradeItem } from "@/features/backtest/schemas";

interface TradePnlPaneProps {
  trades: readonly TradeItem[];
  height: number;
}

const EMPTY_MAIN: readonly ChartPoint[] = [];

export function TradePnlPane({ trades, height }: TradePnlPaneProps) {
  const palette = useChartTheme();

  const bars = useMemo<HistogramPoint[]>(
    () =>
      trades
        .filter((t) => t.status === "closed" && t.exit_time !== null)
        .map((t) => ({
          time: t.exit_time as string,
          value: t.pnl,
          color: t.pnl >= 0 ? palette.bullish : palette.bearish,
        })),
    [trades, palette],
  );

  const histogram = useMemo(() => ({ data: bars }), [bars]);

  if (bars.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-xs text-muted-foreground"
        style={{ height }}
        data-testid="trade-pnl-pane-empty"
      >
        표시할 거래 PnL 데이터가 없습니다
      </div>
    );
  }

  return (
    <div data-testid="trade-pnl-pane">
      <TradingChart
        data={EMPTY_MAIN}
        histogram={histogram}
        height={height}
        ariaLabel="거래별 순손익 (PnL) 바 차트 — 녹색 = 수익, 적색 = 손실, 단위 USDT"
      />
    </div>
  );
}
