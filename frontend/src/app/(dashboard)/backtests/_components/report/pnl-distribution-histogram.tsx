"use client";

// TV "수익 분포" histogram — 수익률(%) 버킷별 거래 수 + 평균 수익/손실 세로 점선
// recharts BarChart + ReferenceLine. 데이터는 analytics.binReturnDistribution 파생.

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { binReturnDistribution } from "@/features/backtest/analytics";
import type { TradeItem } from "@/features/backtest/schemas";
import { useChartTheme } from "@/lib/chart-tokens";
import { formatPercent } from "@/features/backtest/utils";

interface PnlDistributionHistogramProps {
  trades: readonly TradeItem[];
  /** metrics.avg_win (비율) — 세로 점선. null 시 미표시. */
  avgWinPct?: number | null;
  /** metrics.avg_loss (비율, 음수) — 세로 점선. null 시 미표시. */
  avgLossPct?: number | null;
  /** trades 가 표본이면 캡션 표시 (Surface Trust). */
  truncated?: boolean;
  totalTrades?: number;
}

const BIN_COUNT = 12;

interface HistogramDatum {
  label: string;
  mid: number;
  count: number;
  win: number;
  lossCount: number;
}

export function PnlDistributionHistogram({
  trades,
  avgWinPct,
  avgLossPct,
  truncated = false,
  totalTrades,
}: PnlDistributionHistogramProps) {
  const palette = useChartTheme();

  const data = useMemo<HistogramDatum[]>(() => {
    const closed = trades.filter((t) => t.status === "closed");
    const bins = binReturnDistribution(
      closed.map((t) => t.return_pct),
      BIN_COUNT,
    );
    return bins.map((b) => {
      const mid = (b.from + b.to) / 2;
      return {
        label: formatPercent(mid, 1),
        mid,
        count: b.count,
        // 버킷 부호로 승/패 시리즈 분리 (양쪽 색 구분 — TV 패턴).
        win: mid >= 0 ? b.count : 0,
        lossCount: mid < 0 ? b.count : 0,
      };
    });
  }, [trades]);

  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [hasWidth, setHasWidth] = useState(false);
  useEffect(() => {
    const node = wrapperRef.current;
    if (node === null) return;
    if (node.getBoundingClientRect().width > 0) setHasWidth(true);
  }, [data]);

  if (data.length === 0) {
    return (
      <div
        className="flex h-40 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground"
        data-testid="pnl-distribution-empty"
      >
        분포를 계산할 거래가 없습니다
      </div>
    );
  }

  const avgWinLabel = avgWinPct != null ? data.length > 0 : false;

  return (
    <div ref={wrapperRef} data-testid="pnl-distribution-histogram">
      {hasWidth ? (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={palette.grid} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 10, fill: palette.axis }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              allowDecimals={false}
              tick={{ fontSize: 11, fill: palette.axis }}
              axisLine={false}
              tickLine={false}
              width={32}
            />
            <Tooltip
              formatter={(value, name) =>
                name === "win" || name === "lossCount"
                  ? [`${String(value)}건`, name === "win" ? "수익 구간" : "손실 구간"]
                  : null
              }
              labelFormatter={(label) => `수익률 ${String(label)} 부근`}
              labelStyle={{ fontSize: 12 }}
            />
            <Bar dataKey="win" stackId="dist" fill={palette.bullish} isAnimationActive={false} />
            <Bar
              dataKey="lossCount"
              stackId="dist"
              fill={palette.bearish}
              isAnimationActive={false}
            />
            {avgWinLabel && avgWinPct != null ? (
              <ReferenceLine
                x={nearestLabel(data, avgWinPct)}
                stroke={palette.bullish}
                strokeDasharray="4 4"
                label={{
                  value: `평균 수익 ${formatPercent(avgWinPct)}`,
                  fontSize: 10,
                  fill: palette.bullish,
                  position: "top",
                }}
              />
            ) : null}
            {avgLossPct != null ? (
              <ReferenceLine
                x={nearestLabel(data, avgLossPct)}
                stroke={palette.bearish}
                strokeDasharray="4 4"
                label={{
                  value: `평균 손실 ${formatPercent(avgLossPct)}`,
                  fontSize: 10,
                  fill: palette.bearish,
                  position: "top",
                }}
              />
            ) : null}
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div style={{ height: 220 }} />
      )}
      {truncated && totalTrades !== undefined ? (
        <p className="mt-1 text-xs text-muted-foreground">
          * 표본 {trades.length}건 기준 (전체 {totalTrades}건).
        </p>
      ) : null}
    </div>
  );
}

/** ReferenceLine 은 category 축이라 값에 가장 가까운 버킷 라벨로 스냅. */
function nearestLabel(data: readonly HistogramDatum[], value: number): string {
  let best = data[0];
  for (const d of data) {
    if (
      best === undefined ||
      Math.abs(d.mid - value) < Math.abs(best.mid - value)
    ) {
      best = d;
    }
  }
  return best?.label ?? "";
}
