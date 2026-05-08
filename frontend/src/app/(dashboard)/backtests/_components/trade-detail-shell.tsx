// Sprint 43 W11 — 거래 내역 상세 page shell (breadcrumb + 요약 카드 + 본문 wrap).
// /backtests/[id]/trades route 의 client-side 데이터 fetching + 레이아웃.
"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  useBacktest,
  useBacktestTrades,
} from "@/features/backtest/hooks";
import {
  formatDate,
  formatPercent,
} from "@/features/backtest/utils";

import { TradeDetailTable } from "./trade-detail-table";
import { TradeStatsStrip } from "./trade-stats-strip";

const TRADE_QUERY = { limit: 200, offset: 0 };

export function TradeDetailShell({ id }: { id: string }) {
  const detail = useBacktest(id);
  const trades = useBacktestTrades(id, TRADE_QUERY, {
    enabled: detail.data?.status === "completed",
  });

  if (detail.isLoading) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        불러오는 중…
      </p>
    );
  }

  if (detail.isError || !detail.data) {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-center">
        <p className="text-sm text-destructive">
          백테스트 정보를 불러오지 못했습니다
          {detail.error ? `: ${detail.error.message}` : ""}
        </p>
        <Button variant="outline" onClick={() => detail.refetch()}>
          다시 시도
        </Button>
      </div>
    );
  }

  const bt = detail.data;
  const items = trades.data?.items ?? [];
  const tradeCount = trades.data?.total ?? items.length;

  return (
    <div className="flex flex-col gap-5">
      {/* Breadcrumb */}
      <nav
        aria-label="현재 위치"
        className="flex items-center gap-2 text-sm text-muted-foreground"
      >
        <Link
          href="/backtests"
          className="hover:text-foreground"
          data-testid="trade-detail-crumb-list"
        >
          백테스트
        </Link>
        <span aria-hidden className="text-muted-foreground/60">
          /
        </span>
        <Link
          href={`/backtests/${id}`}
          className="hover:text-foreground"
          data-testid="trade-detail-crumb-report"
        >
          {bt.symbol} · {bt.timeframe}
        </Link>
        <span aria-hidden className="text-muted-foreground/60">
          /
        </span>
        <span className="font-semibold text-foreground">거래 내역</span>
        <span className="text-xs text-muted-foreground/80">
          · {tradeCount}개 거래
        </span>
      </nav>

      {/* 요약 카드: 백테스트 메타 + 4 metric-mini */}
      <section
        aria-labelledby="trade-detail-summary-title"
        className="flex flex-wrap items-center justify-between gap-6 rounded-xl border bg-card px-6 py-5 shadow-sm"
      >
        <div className="min-w-0 flex-1">
          <h1
            id="trade-detail-summary-title"
            className="font-display text-xl font-bold tracking-tight"
          >
            {bt.symbol} · {bt.timeframe}
          </h1>
          <p className="font-mono text-xs text-muted-foreground">
            {formatDate(bt.period_start)} ~ {formatDate(bt.period_end)}
          </p>
          <p className="font-mono text-[11px] text-muted-foreground/80">
            백테스트 ID: {bt.id.slice(0, 8)}…
          </p>
        </div>

        {bt.metrics ? (
          <div
            role="list"
            aria-label="백테스트 주요 성과"
            className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4"
          >
            <SummaryMetric
              label="총 수익률"
              value={formatPercent(bt.metrics.total_return)}
              tone={bt.metrics.total_return >= 0 ? "pos" : "neg"}
            />
            <SummaryMetric
              label="샤프"
              value={
                Number.isFinite(bt.metrics.sharpe_ratio)
                  ? bt.metrics.sharpe_ratio.toFixed(2)
                  : "—"
              }
            />
            <SummaryMetric
              label="MDD"
              value={formatPercent(bt.metrics.max_drawdown)}
              tone="neg"
            />
            <SummaryMetric
              label="승률"
              value={formatPercent(bt.metrics.win_rate)}
              sub={`${bt.metrics.num_trades}건`}
            />
          </div>
        ) : null}
      </section>

      {/* Stats strip */}
      <TradeStatsStrip trades={items} />

      {/* Filter + table */}
      <TradeDetailTable
        trades={items}
        isLoading={trades.isLoading}
        isError={trades.isError}
        errorMessage={trades.error?.message}
        filenamePrefix={`backtest-${id.slice(0, 8)}`}
      />
    </div>
  );
}

interface SummaryMetricProps {
  label: string;
  value: string;
  tone?: "pos" | "neg" | "neutral";
  sub?: string;
}

function SummaryMetric({
  label,
  value,
  tone = "neutral",
  sub,
}: SummaryMetricProps) {
  const toneClass =
    tone === "pos"
      ? "text-emerald-600"
      : tone === "neg"
        ? "text-rose-600"
        : "text-foreground";
  return (
    <div role="listitem" className="min-w-0">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className={`font-mono text-base font-bold leading-tight ${toneClass}`}>
        {value}
      </div>
      {sub ? (
        <div className="text-[11px] text-muted-foreground">{sub}</div>
      ) : null}
    </div>
  );
}
