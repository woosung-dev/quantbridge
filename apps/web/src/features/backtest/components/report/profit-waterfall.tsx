"use client";

// TV "수익 구조" waterfall — 총 수익 → 총 손실 → 수수료 → 슬리피지 → 총 PnL
// recharts stacked BarChart. 투명 base + kind 별 시리즈(gain/loss/total) 분리 —
// 행마다 한 시리즈만 non-zero 라 per-bar 색이 자연 적용 (Cell deprecated 회피).
// abs 필드 null(구 백테스트) 시 잠금 empty state — 가짜 값 렌더 금지 (Surface Trust).

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";

import type { WaterfallDatum } from "@/features/backtest/components/report/profit-waterfall-plot";

// recharts plot 은 무거워서 지연 로딩 — hasWidth 대기 placeholder 와 동일 높이 유지.
const ProfitWaterfallPlot = dynamic(
  () => import("@/features/backtest/components/charts/recharts-plots").then((m) => m.ProfitWaterfallPlot),
  { ssr: false, loading: () => <div style={{ height: 220 }} /> },
);

interface ProfitWaterfallProps {
  grossProfit: number | null | undefined;
  grossLoss: number | null | undefined; // 양수 크기 (BE 규약)
  fees: number | null | undefined;
  slippage: number | null | undefined;
  netProfit: number | null | undefined;
}

export function ProfitWaterfall({
  grossProfit,
  grossLoss,
  fees,
  slippage,
  netProfit,
}: ProfitWaterfallProps) {
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

  return (
    <div ref={wrapperRef} data-testid="profit-waterfall">
      {hasWidth ? (
        <ProfitWaterfallPlot data={data} />
      ) : (
        <div style={{ height: 220 }} />
      )}
    </div>
  );
}
