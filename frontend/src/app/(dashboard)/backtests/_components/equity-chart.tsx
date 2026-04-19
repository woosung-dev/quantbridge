"use client";

import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { EquityPoint } from "@/features/backtest/schemas";
import {
  downsampleEquity,
  formatCurrency,
  formatDate,
} from "@/features/backtest/utils";

interface EquityChartProps {
  points: readonly EquityPoint[];
  maxPoints?: number;
}

interface ChartDatum {
  ts: number;
  value: number;
  label: string;
}

export function EquityChart({ points, maxPoints = 1000 }: EquityChartProps) {
  const data = useMemo<ChartDatum[]>(() => {
    const sampled = downsampleEquity(points, maxPoints);
    return sampled.map((p) => ({
      ts: new Date(p.timestamp).getTime(),
      value: p.value,
      label: formatDate(p.timestamp),
    }));
  }, [points, maxPoints]);

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        Equity 데이터가 없습니다
      </div>
    );
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 12, right: 16, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11 }}
            minTickGap={32}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => formatCurrency(v, 0)}
            width={80}
          />
          <Tooltip
            formatter={(value) =>
              typeof value === "number" ? formatCurrency(value) : String(value)
            }
            labelFormatter={(label) => (label == null ? "" : String(label))}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="currentColor"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
