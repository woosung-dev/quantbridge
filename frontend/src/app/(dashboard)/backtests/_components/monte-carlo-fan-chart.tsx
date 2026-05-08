"use client";

// Phase C: Monte Carlo fan chart.
// - equity_percentiles 는 "5"/"25"/"50"/"75"/"95" 키를 가진 dict (값은 number 배열, schema 에서 decimalString transform 완료).
// - MVP: median line + p5~p95 outer band + p25~p75 inner band (stacked Area 로 fan).
// - jsdom + ResizeObserver 미정의 환경에서도 warning 없이 렌더 가능하게 EquityChart 패턴 차용.

import { useEffect, useMemo, useRef, useState } from "react";
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

import type { MonteCarloResult } from "@/features/backtest/schemas";

interface Props {
  result: MonteCarloResult;
}

interface FanDatum {
  bar: number;
  p5Base: number;
  p5To95Range: number;
  p25Base: number;
  p25To75Range: number;
  median: number;
}

function safeSeries(
  percentiles: MonteCarloResult["equity_percentiles"],
  key: string,
): readonly number[] {
  const s = percentiles[key];
  return Array.isArray(s) ? s : [];
}

export function MonteCarloFanChart({ result }: Props) {
  const data = useMemo<FanDatum[]>(() => {
    const p5 = safeSeries(result.equity_percentiles, "5");
    const p25 = safeSeries(result.equity_percentiles, "25");
    const p50 = safeSeries(result.equity_percentiles, "50");
    const p75 = safeSeries(result.equity_percentiles, "75");
    const p95 = safeSeries(result.equity_percentiles, "95");
    const length = Math.min(p5.length, p25.length, p50.length, p75.length, p95.length);
    const rows: FanDatum[] = [];
    for (let i = 0; i < length; i += 1) {
      const lo5 = p5[i] ?? 0;
      const lo25 = p25[i] ?? 0;
      const mid = p50[i] ?? 0;
      const hi75 = p75[i] ?? 0;
      const hi95 = p95[i] ?? 0;
      rows.push({
        bar: i,
        p5Base: lo5,
        p5To95Range: Math.max(0, hi95 - lo5),
        p25Base: lo25,
        p25To75Range: Math.max(0, hi75 - lo25),
        median: mid,
      });
    }
    return rows;
  }, [result]);

  // jsdom 환경에서 width(-1) warning 회피 — EquityChart 와 동일 패턴.
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [hasWidth, setHasWidth] = useState(false);

  useEffect(() => {
    const node = wrapperRef.current;
    if (node === null) return;
    const initial = node.getBoundingClientRect().width;
    if (initial >= 1) {
      setHasWidth(true);
      return;
    }
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width >= 1) {
          setHasWidth(true);
          observer.disconnect();
          break;
        }
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []); // primitive-only dep — LESSON-004 준수

  if (data.length === 0) {
    return (
      <div className="flex h-80 items-center justify-center text-sm text-muted-foreground">
        Monte Carlo 데이터가 없습니다
      </div>
    );
  }

  // Sprint 43 W10 — prototype 02 정합. fan chart 위 요약 통계 카드 (CI 95% / median / MDD p95).
  const summaryItems: ReadonlyArray<{
    label: string;
    value: string;
    tone: "neutral" | "negative";
    helper: string;
  }> = [
    {
      label: "신뢰구간 95%",
      value: `${result.ci_lower_95.toLocaleString()} ~ ${result.ci_upper_95.toLocaleString()}`,
      tone: "neutral",
      helper: `${result.samples.toLocaleString()} 회 시뮬레이션`,
    },
    {
      label: "중앙값 최종 자산",
      value: result.median_final_equity.toLocaleString(),
      tone: "neutral",
      helper: "전체 시뮬레이션 median",
    },
    {
      label: "최대 낙폭 (p95)",
      value: result.max_drawdown_p95.toLocaleString(),
      tone: "negative",
      helper: `평균 ${result.max_drawdown_mean.toLocaleString()}`,
    },
  ];

  return (
    <div className="space-y-3">
      <div
        className="grid grid-cols-1 gap-3 sm:grid-cols-3"
        data-testid="mc-summary-cards"
      >
        {summaryItems.map((item) => (
          <div
            key={item.label}
            className="rounded-md border border-[color:var(--border)] bg-[color:var(--card)] p-3"
          >
            <div className="text-[11px] font-medium uppercase tracking-wide text-[color:var(--text-muted)]">
              {item.label}
            </div>
            <div
              className={
                "mt-1 font-mono text-lg font-semibold tabular-nums " +
                (item.tone === "negative"
                  ? "text-[color:var(--destructive)]"
                  : "text-[color:var(--text-primary)]")
              }
            >
              {item.value}
            </div>
            <div className="mt-0.5 text-[11px] text-[color:var(--text-muted)]">
              {item.helper}
            </div>
          </div>
        ))}
      </div>
      <div ref={wrapperRef} className="h-80 w-full" style={{ minWidth: 0 }}>
      {hasWidth ? (
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <ComposedChart
            data={data}
            margin={{ top: 12, right: 16, bottom: 24, left: 8 }}
          >
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
            <Tooltip />
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
              fill="currentColor"
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
              fill="currentColor"
              fillOpacity={0.35}
              name="25%~75%"
              isAnimationActive={false}
            />
            {/* 중앙값 */}
            <Line
              type="monotone"
              dataKey="median"
              stroke="currentColor"
              strokeWidth={2}
              dot={false}
              name="중앙값"
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-full w-full" aria-busy="true" />
      )}
      </div>
    </div>
  );
}
