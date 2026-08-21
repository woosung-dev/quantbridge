"use client";

// Monte Carlo fan chart 의 recharts plot 서브트리 — 부모(monte-carlo-fan-chart.tsx)가
// next/dynamic 으로 지연 로딩해 recharts 를 route 초기 번들에서 제외한다.

import {
  Area,
  ComposedChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface FanDatum {
  bar: number;
  p5Base: number;
  p5To95Range: number;
  p25Base: number;
  p25To75Range: number;
  median: number;
}

export function MonteCarloFanPlot({ data }: { data: readonly FanDatum[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <ComposedChart data={data as FanDatum[]} margin={{ top: 12, right: 16, bottom: 24, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="bar"
          tick={{ fontSize: 11 }}
          label={{
            value: "Bar",
            position: "insideBottom",
            offset: -8,
            style: { fontSize: 11 },
          }}
        />
        <YAxis tick={{ fontSize: 11 }} width={70} />
        <Tooltip
          contentStyle={{
            background: "var(--card)",
            border: "1px solid var(--border)",
            color: "var(--foreground)",
          }}
          labelStyle={{ color: "var(--foreground)" }}
          itemStyle={{ color: "var(--foreground)" }}
        />
        <Legend verticalAlign="top" height={28} />
        {/* 외측 밴드 p5~p95: 투명 base + 색상 range (stacked) */}
        <Area
          type="monotone"
          dataKey="p5Base"
          stackId="outer"
          stroke="none"
          fill="transparent"
          legendType="none"
          name="p5_base"
          isAnimationActive={false}
        />
        <Area
          type="monotone"
          dataKey="p5To95Range"
          stackId="outer"
          stroke="none"
          fill="var(--primary)"
          fillOpacity={0.15}
          name="5%~95%"
          isAnimationActive={false}
        />
        {/* 내측 밴드 p25~p75 */}
        <Area
          type="monotone"
          dataKey="p25Base"
          stackId="inner"
          stroke="none"
          fill="transparent"
          legendType="none"
          name="p25_base"
          isAnimationActive={false}
        />
        <Area
          type="monotone"
          dataKey="p25To75Range"
          stackId="inner"
          stroke="none"
          fill="var(--primary)"
          fillOpacity={0.35}
          name="25%~75%"
          isAnimationActive={false}
        />
        {/* 중앙값 */}
        <Line
          type="monotone"
          dataKey="median"
          stroke="var(--primary)"
          strokeWidth={2}
          dot={false}
          name="중앙값"
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
