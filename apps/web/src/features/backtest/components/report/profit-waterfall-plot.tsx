"use client";

// 수익 구조 waterfall 의 recharts plot 서브트리 — 부모(profit-waterfall.tsx)가
// next/dynamic 으로 지연 로딩해 recharts 를 route 초기 번들에서 제외한다.

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useChartTheme } from "@/lib/chart-tokens";
import { formatCurrency } from "@/features/backtest/utils";

export interface WaterfallDatum {
  name: string;
  base: number;
  gain: number;
  loss: number;
  total: number;
  signed: number;
}

export function ProfitWaterfallPlot({ data }: { data: readonly WaterfallDatum[] }) {
  const palette = useChartTheme();

  const tooltipFormatter = (
    _value: unknown,
    name: unknown,
    entry: { payload?: WaterfallDatum } | undefined,
  ): [string, string] | null => {
    if (name === "base") return null;
    const signed = entry?.payload?.signed;
    if (signed === undefined) return null;
    return [`${signed >= 0 ? "+" : ""}${formatCurrency(signed)} USDT`, "금액"];
  };

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        data={data as WaterfallDatum[]}
        margin={{ top: 8, right: 8, left: 8, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={palette.grid} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: palette.axis }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: palette.axis }}
          tickFormatter={(v: number) => formatCurrency(v, 0)}
          axisLine={false}
          tickLine={false}
          width={80}
        />
        <Tooltip formatter={tooltipFormatter} labelStyle={{ fontSize: 12 }} />
        {/* 투명 base + kind 별 시리즈 스택 = 플로팅 워터폴 바. */}
        <Bar dataKey="base" stackId="wf" fill="transparent" isAnimationActive={false} />
        <Bar dataKey="gain" stackId="wf" fill={palette.bullish} isAnimationActive={false} />
        <Bar dataKey="loss" stackId="wf" fill={palette.bearish} isAnimationActive={false} />
        <Bar dataKey="total" stackId="wf" fill={palette.compare} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}
