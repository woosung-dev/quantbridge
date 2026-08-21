"use client";

// TV "수익 분포" histogram — 수익률(%) 버킷별 거래 수 + 평균 수익/손실 세로 점선
// recharts BarChart + ReferenceLine. 데이터는 analytics.binReturnDistribution 파생.

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";

import { binReturnDistribution } from "@/features/backtest/analytics";
import type { TradeItem } from "@/features/backtest/schemas";
import { formatPercent } from "@/features/backtest/utils";
import type { HistogramDatum } from "@/features/backtest/components/report/pnl-distribution-plot";

// recharts plot 은 무거워서 지연 로딩 — hasWidth 대기 placeholder 와 동일 높이 유지.
const PnlDistributionPlot = dynamic(
  () =>
    import("@/features/backtest/components/charts/recharts-plots").then(
      (m) => m.PnlDistributionPlot,
    ),
  { ssr: false, loading: () => <div style={{ height: 220 }} /> },
);

interface PnlDistributionHistogramProps {
  trades: readonly TradeItem[];
  /** metrics.avg_win (비율) — 세로 점선. null 시 미표시. */
  avgWinPct?: number | null;
  /** metrics.avg_loss (비율, 음수) — 세로 점선. null 시 미표시. */
  avgLossPct?: number | null;
  /** trades 가 표본이면 캡션 표시 (Surface Trust). */
  truncated?: boolean;
  totalTrades?: number;
}

const BIN_COUNT = 12;

export function PnlDistributionHistogram({
  trades,
  avgWinPct,
  avgLossPct,
  truncated = false,
  totalTrades,
}: PnlDistributionHistogramProps) {
  const data = useMemo<HistogramDatum[]>(() => {
    const closed = trades.filter((t) => t.status === "closed");
    const bins = binReturnDistribution(
      closed.map((t) => t.return_pct),
      BIN_COUNT,
    );
    return bins.map((b) => {
      const mid = (b.from + b.to) / 2;
      return {
        label: formatPercent(mid, 1),
        mid,
        count: b.count,
        // 버킷 부호로 승/패 시리즈 분리 (양쪽 색 구분 — TV 패턴).
        win: mid >= 0 ? b.count : 0,
        lossCount: mid < 0 ? b.count : 0,
      };
    });
  }, [trades]);

  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [hasWidth, setHasWidth] = useState(false);
  useEffect(() => {
    const node = wrapperRef.current;
    if (node === null) return;
    if (node.getBoundingClientRect().width > 0) setHasWidth(true);
  }, [data]);

  if (data.length === 0) {
    return (
      <div
        className="flex h-40 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground"
        data-testid="pnl-distribution-empty"
      >
        분포를 계산할 거래가 없습니다
      </div>
    );
  }

  return (
    <div ref={wrapperRef} data-testid="pnl-distribution-histogram">
      {hasWidth ? (
        <PnlDistributionPlot data={data} avgWinPct={avgWinPct} avgLossPct={avgLossPct} />
      ) : (
        <div style={{ height: 220 }} />
      )}
      {truncated && totalTrades !== undefined ? (
        <p className="mt-1 text-xs text-muted-foreground">
          * 표본 {trades.length}건 기준 (전체 {totalTrades}건).
        </p>
      ) : null}
    </div>
  );
}
