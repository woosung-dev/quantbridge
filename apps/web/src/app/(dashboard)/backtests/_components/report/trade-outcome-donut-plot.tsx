"use client";

// 거래 분포 donut 의 recharts plot 서브트리 — 부모(trade-outcome-donut.tsx)가
// next/dynamic 으로 지연 로딩해 recharts 를 route 초기 번들에서 제외한다.

import { Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

export interface DonutDatum {
  name: string;
  value: number;
  fill: string;
}

export function TradeOutcomeDonutPlot({ data }: { data: readonly DonutDatum[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data as DonutDatum[]}
          dataKey="value"
          nameKey="name"
          innerRadius={58}
          outerRadius={82}
          strokeWidth={0}
          isAnimationActive={false}
        />
        <Tooltip
          formatter={(value, name) => [`${String(value)}건`, String(name)]}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
