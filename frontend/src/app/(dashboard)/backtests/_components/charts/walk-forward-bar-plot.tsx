"use client";

// Walk-Forward bar chart 의 recharts plot 서브트리 — 부모(walk-forward-bar-chart.tsx)가
// next/dynamic 으로 지연 로딩해 recharts 를 route 초기 번들에서 제외한다.

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface WalkForwardBarDatum {
  fold: string;
  IS: number;
  OOS: number;
}

export function WalkForwardBarPlot({
  data,
}: {
  data: readonly WalkForwardBarDatum[];
}) {
  return (
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <BarChart
        data={data as WalkForwardBarDatum[]}
        margin={{ top: 12, right: 16, bottom: 36, left: 24 }}
      >
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="fold"
          tick={{ fontSize: 11 }}
          label={{
            value: "Fold",
            position: "insideBottom",
            offset: -8,
            style: { fontSize: 11, fill: "var(--text-muted)" },
          }}
        />
        <YAxis
          tick={{ fontSize: 11 }}
          tickFormatter={(v: number) => `${v.toFixed(1)}%`}
          width={70}
          label={{
            value: "수익률 (%)",
            angle: -90,
            position: "insideLeft",
            offset: 12,
            style: { fontSize: 11, fill: "var(--text-muted)", textAnchor: "middle" },
          }}
        />
        <Tooltip
          formatter={(value) =>
            typeof value === "number" ? `${value.toFixed(2)}%` : String(value)
          }
          contentStyle={{
            background: "var(--card)",
            border: "1px solid var(--border)",
            color: "var(--foreground)",
          }}
          labelStyle={{ color: "var(--foreground)" }}
          itemStyle={{ color: "var(--foreground)" }}
        />
        <Legend verticalAlign="top" height={28} />
        {/* Sprint 43 W10 — prototype 02 정합. label 한국어 보강 + DESIGN.md var 색. */}
        <Bar
          dataKey="IS"
          fill="var(--primary)"
          name="In-sample (학습 구간)"
          isAnimationActive={false}
        />
        <Bar
          dataKey="OOS"
          fill="var(--success)"
          name="Out-of-sample (검증 구간)"
          isAnimationActive={false}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
