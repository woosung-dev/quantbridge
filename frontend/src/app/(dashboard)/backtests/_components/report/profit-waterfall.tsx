"use client";

// TV "수익 구조" waterfall — 총 수익 → 총 손실 → 수수료 → 슬리피지 → 총 PnL
// recharts stacked BarChart. 투명 base + kind 별 시리즈(gain/loss/total) 분리 —
// 행마다 한 시리즈만 non-zero 라 per-bar 색이 자연 적용 (Cell deprecated 회피).
// abs 필드 null(구 백테스트) 시 잠금 empty state — 가짜 값 렌더 금지 (Surface Trust).

import { useEffect, useMemo, useRef, useState } from "react";
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

interface ProfitWaterfallProps {
  grossProfit: number | null | undefined;
  grossLoss: number | null | undefined; // 양수 크기 (BE 규약)
  fees: number | null | undefined;
  slippage: number | null | undefined;
  netProfit: number | null | undefined;
}

interface WaterfallDatum {
  name: string;
  base: number;
  gain: number;
  loss: number;
  total: number;
  signed: number;
}

export function ProfitWaterfall({
  grossProfit,
  grossLoss,
  fees,
  slippage,
  netProfit,
}: ProfitWaterfallProps) {
  const palette = useChartTheme();

  const data = useMemo<WaterfallDatum[] | null>(() => {
    if (
      grossProfit == null ||
      grossLoss == null ||
      fees == null ||
      slippage == null ||
      netProfit == null
    ) {
      return null;
    }
    // 누적 워터폴: 시작 0 → +총수익 → -총손실 → -수수료 → -슬리피지 → 총 PnL.
    const steps: Array<{ name: string; signed: number; kind: "gain" | "loss" }> = [
      { name: "총 수익", signed: grossProfit, kind: "gain" },
      { name: "총 손실", signed: -grossLoss, kind: "loss" },
      { name: "수수료", signed: -fees, kind: "loss" },
      { name: "슬리피지", signed: -slippage, kind: "loss" },
    ];
    let running = 0;
    const out: WaterfallDatum[] = [];
    for (const s of steps) {
      const start = running;
      running += s.signed;
      out.push({
        name: s.name,
        base: Math.min(start, running),
        gain: s.kind === "gain" ? Math.abs(s.signed) : 0,
        loss: s.kind === "loss" ? Math.abs(s.signed) : 0,
        total: 0,
        signed: s.signed,
      });
    }
    out.push({
      name: "총 PnL",
      base: Math.min(0, netProfit),
      gain: 0,
      loss: 0,
      total: Math.abs(netProfit),
      signed: netProfit,
    });
    return out;
  }, [grossProfit, grossLoss, fees, slippage, netProfit]);

  // jsdom width(-1) warning 회피 (walk-forward-bar-chart 패턴).
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [hasWidth, setHasWidth] = useState(false);
  useEffect(() => {
    const node = wrapperRef.current;
    if (node === null) return;
    if (node.getBoundingClientRect().width > 0) setHasWidth(true);
  }, [data]);

  if (data === null) {
    return (
      <div
        className="flex h-40 flex-col items-center justify-center gap-1 rounded-lg border border-dashed text-sm text-muted-foreground"
        data-testid="profit-waterfall-locked"
      >
        <p>수익 구조 데이터가 없는 구 백테스트입니다</p>
        <p className="text-xs">재실행하면 총 수익/손실/비용 분해가 생성됩니다</p>
      </div>
    );
  }

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
    <div ref={wrapperRef} data-testid="profit-waterfall">
      {hasWidth ? (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
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
      ) : (
        <div style={{ height: 220 }} />
      )}
    </div>
  );
}
