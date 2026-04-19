"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  useBacktest,
  useBacktestProgress,
  useBacktestTrades,
} from "@/features/backtest/hooks";
import { formatDate } from "@/features/backtest/utils";

import { BacktestStatusBadge } from "./status-badge";
import { EquityChart } from "./equity-chart";
import { MetricsCards } from "./metrics-cards";
import { TradeTable } from "./trade-table";

const TRADE_QUERY = { limit: 200, offset: 0 };

export function BacktestDetailView({ id }: { id: string }) {
  const detail = useBacktest(id);
  const progress = useBacktestProgress(id);

  const status = detail.data?.status ?? progress.data?.status;
  const tradesEnabled = status === "completed";

  const trades = useBacktestTrades(id, TRADE_QUERY, { enabled: tradesEnabled });

  if (detail.isLoading) {
    return <p className="py-12 text-center text-sm text-muted-foreground">불러오는 중…</p>;
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
  const effectiveStatus = progress.data?.status ?? bt.status;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-2xl font-bold">
              {bt.symbol} · {bt.timeframe}
            </h1>
            <BacktestStatusBadge status={effectiveStatus} />
          </div>
          <p className="text-sm text-muted-foreground">
            {formatDate(bt.period_start)} → {formatDate(bt.period_end)}
          </p>
        </div>
        <Link
          href="/backtests"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← 목록
        </Link>
      </header>

      {effectiveStatus === "queued" || effectiveStatus === "running" || effectiveStatus === "cancelling" ? (
        <InProgressCard status={effectiveStatus} />
      ) : null}

      {effectiveStatus === "failed" ? (
        <ErrorCard
          message={progress.data?.error ?? bt.error ?? "알 수 없는 오류"}
          onRetry={() => {
            detail.refetch();
            progress.refetch();
          }}
        />
      ) : null}

      {effectiveStatus === "cancelled" ? (
        <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
          사용자에 의해 취소된 백테스트입니다
        </p>
      ) : null}

      {effectiveStatus === "completed" && bt.metrics ? (
        <MetricsCards metrics={bt.metrics} />
      ) : null}

      {effectiveStatus === "completed" && bt.equity_curve ? (
        <section className="rounded-xl border bg-card p-4">
          <h2 className="mb-2 text-sm font-medium">Equity Curve</h2>
          <EquityChart points={bt.equity_curve} />
        </section>
      ) : null}

      {effectiveStatus === "completed" ? (
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-medium">거래 기록</h2>
          {trades.isLoading ? (
            <p className="text-sm text-muted-foreground">거래 불러오는 중…</p>
          ) : trades.isError ? (
            <p className="text-sm text-destructive">
              거래 기록 로드 실패: {trades.error?.message}
            </p>
          ) : (
            <TradeTable trades={trades.data?.items ?? []} />
          )}
        </section>
      ) : null}
    </div>
  );
}

function InProgressCard({ status }: { status: "queued" | "running" | "cancelling" }) {
  const label = status === "queued" ? "대기 중" : status === "running" ? "실행 중" : "취소 중";
  return (
    <div className="flex items-center gap-3 rounded-xl border bg-card p-4">
      <span className="inline-block h-3 w-3 animate-pulse rounded-full bg-primary" />
      <p className="text-sm">
        {label}입니다. 결과가 준비되면 자동으로 화면이 전환됩니다. (30초 간격 폴링)
      </p>
    </div>
  );
}

function ErrorCard({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-destructive/40 bg-destructive/5 p-4">
      <p className="text-sm text-destructive">{message}</p>
      <div>
        <Button variant="outline" size="sm" onClick={onRetry}>
          다시 시도
        </Button>
      </div>
    </div>
  );
}
