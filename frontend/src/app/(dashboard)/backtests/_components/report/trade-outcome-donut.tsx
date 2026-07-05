"use client";

// TV "거래 분포" donut — 승자/패자/손익분기 + 중앙 총 거래 수
// recharts PieChart(innerRadius). 데이터는 analytics.computeOutcomeCounts 파생.

import { useEffect, useMemo, useRef, useState } from "react";
import { Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { OutcomeCounts } from "@/features/backtest/analytics";
import { useChartTheme } from "@/lib/chart-tokens";
import { formatPercent } from "@/features/backtest/utils";

interface TradeOutcomeDonutProps {
  counts: OutcomeCounts;
}

export function TradeOutcomeDonut({ counts }: TradeOutcomeDonutProps) {
  const palette = useChartTheme();

  const data = useMemo(
    () =>
      [
        { name: "승자", value: counts.wins, fill: palette.bullish },
        { name: "패자", value: counts.losses, fill: palette.bearish },
        { name: "손익분기점", value: counts.breakeven, fill: palette.axis },
      ].filter((d) => d.value > 0),
    [counts, palette],
  );

  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [hasWidth, setHasWidth] = useState(false);
  useEffect(() => {
    const node = wrapperRef.current;
    if (node === null) return;
    if (node.getBoundingClientRect().width > 0) setHasWidth(true);
  }, [data]);

  if (counts.total === 0) {
    return (
      <div
        className="flex h-40 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground"
        data-testid="trade-outcome-donut-empty"
      >
        거래가 없습니다
      </div>
    );
  }

  const legendRows: Array<{ name: string; count: number; color: string }> = [
    { name: "승자", count: counts.wins, color: palette.bullish },
    { name: "패자", count: counts.losses, color: palette.bearish },
    { name: "손익분기점", count: counts.breakeven, color: palette.axis },
  ];

  return (
    <div
      className="flex flex-col items-center gap-4 sm:flex-row"
      data-testid="trade-outcome-donut"
    >
      <div ref={wrapperRef} className="relative h-[180px] w-[180px] shrink-0">
        {hasWidth ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
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
        ) : null}
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-2xl font-bold tabular-nums">
            {counts.total}
          </span>
          <span className="text-xs text-muted-foreground">총 거래</span>
        </div>
      </div>

      <table className="w-full max-w-xs text-sm" aria-label="거래 분포 상세">
        <tbody>
          {legendRows.map((row) => (
            <tr key={row.name}>
              <td className="py-1.5">
                <span className="inline-flex items-center gap-2">
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: row.color }}
                    aria-hidden="true"
                  />
                  {row.name}
                </span>
              </td>
              <td className="py-1.5 text-right font-mono tabular-nums">
                {row.count} 거래
              </td>
              <td className="py-1.5 text-right font-mono tabular-nums text-muted-foreground">
                {formatPercent(counts.total > 0 ? row.count / counts.total : 0)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
