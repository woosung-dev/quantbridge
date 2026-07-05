"use client";

// 수익 분포 histogram 의 recharts plot 서브트리 — 부모(pnl-distribution-histogram.tsx)가
// next/dynamic 으로 지연 로딩해 recharts 를 route 초기 번들에서 제외한다.

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

import { useChartTheme } from "@/lib/chart-tokens";
import { formatPercent } from "@/features/backtest/utils";

export interface HistogramDatum {
  label: string;
  mid: number;
  count: number;
  win: number;
  lossCount: number;
}

export interface PnlDistributionPlotProps {
  data: readonly HistogramDatum[];
  avgWinPct?: number | null;
  avgLossPct?: number | null;
}

export function PnlDistributionPlot({
  data,
  avgWinPct,
  avgLossPct,
}: PnlDistributionPlotProps) {
  const palette = useChartTheme();

  const avgWinLabel = avgWinPct != null ? data.length > 0 : false;

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        data={data as HistogramDatum[]}
        margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
      >
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
