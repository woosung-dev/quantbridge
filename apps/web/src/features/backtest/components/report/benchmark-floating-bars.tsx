"use client";

// TV "벤치마킹" floating bar — B&H(매수 후 보유) vs 전략 손익의 최대/현재/최소 %
// 카테고리 2개뿐이라 차트 라이브러리 대신 커스텀 SVG (Terminal Tape 밀도).

import { useMemo } from "react";

import type { CurveRange } from "@/features/backtest/analytics";
import { useChartTheme } from "@/lib/chart-tokens";
import { formatPercent } from "@/features/backtest/utils";

interface BenchmarkFloatingBarsProps {
  strategyRange: CurveRange | null;
  bhRange: CurveRange | null;
}

const W = 640;
const H = 220;
const PAD_Y = 18;
const BAR_W = 120;

export function BenchmarkFloatingBars({
  strategyRange,
  bhRange,
}: BenchmarkFloatingBarsProps) {
  const palette = useChartTheme();

  const layout = useMemo(() => {
    if (strategyRange === null) return null;
    const ranges = [bhRange, strategyRange].filter(
      (r): r is CurveRange => r !== null,
    );
    const maxAll = Math.max(0, ...ranges.map((r) => r.maxPct));
    const minAll = Math.min(0, ...ranges.map((r) => r.minPct));
    const span = maxAll - minAll || 1;
    const toY = (pct: number): number =>
      PAD_Y + ((maxAll - pct) / span) * (H - PAD_Y * 2);
    return { toY, zeroY: toY(0) };
  }, [strategyRange, bhRange]);

  if (strategyRange === null || layout === null) {
    return (
      <div
        className="flex h-40 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground"
        data-testid="benchmark-floating-bars-empty"
      >
        벤치마킹을 계산할 equity 데이터가 부족합니다
      </div>
    );
  }

  const { toY, zeroY } = layout;
  const bars: Array<{
    label: string;
    range: CurveRange;
    x: number;
    color: string;
  }> = [];
  if (bhRange !== null) {
    bars.push({ label: "매수 후 보유 손익", range: bhRange, x: 120, color: palette.benchmark });
  }
  bars.push({
    label: "전략 손익",
    range: strategyRange,
    x: bhRange !== null ? 400 : 260,
    color: palette.compare,
  });

  return (
    <div className="overflow-x-auto" data-testid="benchmark-floating-bars">
      <svg
        viewBox={`0 0 ${W} ${H + 24}`}
        className="min-w-[480px]"
        role="img"
        aria-label={
          `벤치마킹 — 전략 손익 최대 ${formatPercent(strategyRange.maxPct)}, ` +
          `현재 ${formatPercent(strategyRange.currentPct)}, 최소 ${formatPercent(strategyRange.minPct)}` +
          (bhRange
            ? ` · 매수 후 보유 최대 ${formatPercent(bhRange.maxPct)}, 현재 ${formatPercent(bhRange.currentPct)}, 최소 ${formatPercent(bhRange.minPct)}`
            : "")
        }
      >
        {/* 0% 기준선 */}
        <line
          x1={16}
          x2={W - 16}
          y1={zeroY}
          y2={zeroY}
          stroke={palette.axis}
          strokeDasharray="4 4"
          strokeOpacity={0.5}
        />
        <text x={W - 16} y={zeroY - 4} textAnchor="end" fontSize={10} fill={palette.axis}>
          0%
        </text>

        {bars.map((bar) => {
          const top = toY(bar.range.maxPct);
          const bottom = toY(bar.range.minPct);
          const current = toY(bar.range.currentPct);
          return (
            <g key={bar.label}>
              {/* 플로팅 바 (max→min) */}
              <rect
                x={bar.x}
                y={top}
                width={BAR_W}
                height={Math.max(2, bottom - top)}
                rx={3}
                fill={bar.color}
                fillOpacity={0.75}
              />
              {/* 현재값 tick */}
              <line
                x1={bar.x - 6}
                x2={bar.x + BAR_W + 6}
                y1={current}
                y2={current}
                stroke={bar.color}
                strokeWidth={2}
              />
              {/* 값 pill 라벨 (최대/현재/최소) */}
              <ValuePill
                x={bar.x + BAR_W + 10}
                y={top}
                label="최대"
                value={formatPercent(bar.range.maxPct)}
                color={bar.color}
              />
              <ValuePill
                x={bar.x + BAR_W + 10}
                y={current}
                label="현재"
                value={formatPercent(bar.range.currentPct)}
                color={bar.color}
              />
              <ValuePill
                x={bar.x + BAR_W + 10}
                y={bottom}
                label="최소"
                value={formatPercent(bar.range.minPct)}
                color={bar.color}
              />
              <text
                x={bar.x + BAR_W / 2}
                y={H + 16}
                textAnchor="middle"
                fontSize={11}
                fill={palette.axis}
              >
                {bar.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function ValuePill({
  x,
  y,
  label,
  value,
  color,
}: {
  x: number;
  y: number;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <g>
      <rect x={x} y={y - 9} width={96} height={18} rx={4} fill={color} fillOpacity={0.14} />
      <text x={x + 5} y={y + 4} fontSize={10} fill={color} fontWeight={600}>
        {label}
      </text>
      <text
        x={x + 91}
        y={y + 4}
        fontSize={10}
        textAnchor="end"
        fill={color}
        fontFamily="var(--font-mono, monospace)"
      >
        {value}
      </text>
    </g>
  );
}
