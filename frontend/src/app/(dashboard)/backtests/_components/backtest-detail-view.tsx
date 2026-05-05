"use client";

import Link from "next/link";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  useBacktest,
  useBacktestProgress,
  useBacktestTrades,
} from "@/features/backtest/hooks";
import { formatDate } from "@/features/backtest/utils";

const TERMINAL_STATUSES = ["completed", "failed", "cancelled"] as const;

import { AssumptionsCard } from "./assumptions-card";
import { BacktestStatusBadge } from "./status-badge";
import { EquityChartV2 } from "./equity-chart-v2";
import { MetricsCards } from "./metrics-cards";
import { MetricsDetail } from "./metrics-detail";
import { RerunButton } from "./rerun-button";
import { StressTestPanel } from "./stress-test-panel";
import { TradeAnalysis } from "./trade-analysis";
import { TradeTable } from "./trade-table";

const TRADE_QUERY = { limit: 200, offset: 0 };

export function BacktestDetailView({ id }: { id: string }) {
  const detail = useBacktest(id);
  const progress = useBacktestProgress(id);

  const status = detail.data?.status ?? progress.data?.status;
  const tradesEnabled = status === "completed";

  const trades = useBacktestTrades(id, TRADE_QUERY, { enabled: tradesEnabled });

  // Terminal 전환 시 detail refetch — queued→completed 감지되면 initial cache (metrics=null)
  // 를 신선화. 안 하면 폴링이 멈춘 후 metrics 가 null 로 stuck.
  // LESSON-004 guard: primitive dep (string) + stable function reference.
  const progressStatus = progress.data?.status;
  const detailStatus = detail.data?.status;
  const refetchDetail = detail.refetch;
  useEffect(() => {
    if (!progressStatus) return;
    if (!(TERMINAL_STATUSES as readonly string[]).includes(progressStatus)) return;
    if (detailStatus === progressStatus) return;
    refetchDetail();
  }, [progressStatus, detailStatus, refetchDetail]);

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
        <div className="flex items-center gap-3">
          <RerunButton
            backtest={bt}
            isEnabled={(TERMINAL_STATUSES as readonly string[]).includes(
              effectiveStatus,
            )}
          />
          <Link
            href="/backtests"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            ← 목록
          </Link>
        </div>
      </header>

      {effectiveStatus === "queued" ||
      effectiveStatus === "running" ||
      effectiveStatus === "cancelling" ? (
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

      {effectiveStatus === "completed" && !bt.metrics ? (
        <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
          결과를 불러오는 중…
        </p>
      ) : null}

      {effectiveStatus === "completed" && bt.metrics ? (
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">개요</TabsTrigger>
            <TabsTrigger value="metrics">성과 지표</TabsTrigger>
            <TabsTrigger value="analysis">거래 분석</TabsTrigger>
            <TabsTrigger value="trades">거래 목록</TabsTrigger>
            <TabsTrigger value="stress-test">스트레스 테스트</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-4 space-y-4">
            <AssumptionsCard
              initialCapital={bt.initial_capital}
              config={bt.config}
            />
            <MetricsCards metrics={bt.metrics} config={bt.config} />
            {bt.equity_curve && bt.equity_curve.length > 0 && (
              <section className="rounded-xl border bg-card p-4">
                <h2 className="mb-2 text-sm font-medium">
                  Equity Curve · Buy &amp; Hold · Drawdown
                </h2>
                <EquityChartV2
                  equityCurve={bt.equity_curve}
                  trades={trades.data?.items}
                  initialCapital={bt.initial_capital}
                  timeframe={bt.timeframe}
                  mddExceedsCapital={bt.metrics?.mdd_exceeds_capital ?? null}
                />
              </section>
            )}
          </TabsContent>

          <TabsContent value="metrics" className="mt-4">
            <MetricsDetail metrics={bt.metrics} />
          </TabsContent>

          <TabsContent value="analysis" className="mt-4">
            <TradeAnalysis metrics={bt.metrics} trades={trades.data?.items} />
          </TabsContent>

          <TabsContent value="trades" className="mt-4">
            {trades.isLoading ? (
              <p className="text-sm text-muted-foreground">
                거래 불러오는 중…
              </p>
            ) : trades.isError ? (
              <p className="text-sm text-destructive">
                거래 기록 로드 실패: {trades.error?.message}
              </p>
            ) : (
              <TradeTable
                trades={trades.data?.items ?? []}
                filenamePrefix={`backtest-${id.slice(0, 8)}`}
              />
            )}
          </TabsContent>

          <TabsContent value="stress-test" className="mt-4">
            <StressTestPanel backtestId={bt.id} />
          </TabsContent>
        </Tabs>
      ) : null}
    </div>
  );
}

function InProgressCard({
  status,
}: {
  status: "queued" | "running" | "cancelling";
}) {
  const label =
    status === "queued"
      ? "대기 중"
      : status === "running"
        ? "실행 중"
        : "취소 중";
  return (
    <div className="flex items-center gap-3 rounded-xl border bg-card p-4">
      <span className="inline-block h-3 w-3 animate-pulse rounded-full bg-primary" />
      <p className="text-sm">
        {label}입니다. 결과가 준비되면 자동으로 화면이 전환됩니다. (30초 간격
        폴링)
      </p>
    </div>
  );
}

function ErrorCard({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
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
