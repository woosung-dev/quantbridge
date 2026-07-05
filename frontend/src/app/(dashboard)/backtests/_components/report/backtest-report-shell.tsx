"use client";

// 백테스트 리포트 IA 골격 — TV Strategy Tester 정보 구조 (Terminal Tape 위)
// [상시] KeyStatsStrip + AssumptionsCard + PerformanceChart
// [섹션 탭] 상세 결과 / 거래 분석 / 런업&드로다운 / 거래 목록 / 스트레스 테스트
// trades 는 useAllBacktestTrades(200-cap 해소) 1회 로드 후 전 섹션 공유.

import { ArrowRight } from "lucide-react";
import Link from "next/link";

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { useAllBacktestTrades } from "@/features/backtest/hooks";
import type { BacktestDetail } from "@/features/backtest/schemas";

import { AssumptionsCard } from "@/app/(dashboard)/backtests/_components/assumptions-card";
import { StressTestPanel } from "@/app/(dashboard)/backtests/_components/stress-test-panel";
import { TradeAnalysis } from "@/app/(dashboard)/backtests/_components/trades/trade-analysis";
import { DetailedResultsSection } from "@/app/(dashboard)/backtests/_components/report/detailed-results-section";
import { KeyStatsStrip } from "@/app/(dashboard)/backtests/_components/report/key-stats-strip";
import { PerformanceChart } from "@/app/(dashboard)/backtests/_components/report/performance-chart";
import { RunupDrawdownSection } from "@/app/(dashboard)/backtests/_components/report/runup-drawdown-section";
import { TradeAnalyticsSection } from "@/app/(dashboard)/backtests/_components/report/trade-analytics-section";
import { TradeLedgerTable } from "@/app/(dashboard)/backtests/_components/report/trade-ledger-table";

interface BacktestReportShellProps {
  backtest: BacktestDetail;
  currentId: string;
}

export function BacktestReportShell({
  backtest: bt,
  currentId,
}: BacktestReportShellProps) {
  const trades = useAllBacktestTrades(currentId);
  const tradeItems = trades.data?.items;
  const truncated = trades.data?.truncated ?? false;

  const buyAndHoldPoints =
    bt.metrics?.buy_and_hold_curve?.map(([timestamp, value]) => ({
      timestamp,
      value,
    })) ?? null;

  if (!bt.metrics) {
    return null;
  }

  return (
    <div className="flex flex-col gap-4" data-testid="backtest-report-shell">
      <KeyStatsStrip metrics={bt.metrics} config={bt.config} />

      <AssumptionsCard
        initialCapital={bt.initial_capital}
        config={bt.config}
        totalFees={bt.metrics.total_fees}
        totalSlippage={bt.metrics.total_slippage}
        fundingDataIncomplete={bt.metrics.funding_data_incomplete}
      />

      {bt.equity_curve && bt.equity_curve.length > 0 ? (
        <PerformanceChart
          currentId={currentId}
          equityCurve={bt.equity_curve}
          trades={tradeItems}
          initialCapital={bt.initial_capital}
          timeframe={bt.timeframe}
          mddExceedsCapital={bt.metrics.mdd_exceeds_capital ?? null}
          buyAndHoldCurve={buyAndHoldPoints}
        />
      ) : null}

      {truncated ? (
        <p className="text-xs text-muted-foreground">
          거래가 매우 많아 표본 {tradeItems?.length ?? 0}건 기준으로 표시합니다
          (전체 {trades.data?.total ?? 0}건은 CSV 로 확인).
        </p>
      ) : null}

      <Tabs defaultValue="detailed-results" className="qb-card-fade-in">
        <TabsList>
          <TabsTrigger
            value="detailed-results"
            className="data-active:text-[var(--primary)]"
          >
            상세 결과
          </TabsTrigger>
          <TabsTrigger
            value="trade-analysis"
            className="data-active:text-[var(--primary)]"
          >
            거래 분석
          </TabsTrigger>
          <TabsTrigger
            value="runup-drawdown"
            className="data-active:text-[var(--primary)]"
          >
            런업 &amp; 드로다운
          </TabsTrigger>
          <TabsTrigger
            value="trades"
            className="data-active:text-[var(--primary)]"
          >
            거래 목록
          </TabsTrigger>
          <TabsTrigger
            value="stress-test"
            className="data-active:text-[var(--primary)]"
          >
            스트레스 테스트
          </TabsTrigger>
        </TabsList>

        <TabsContent value="detailed-results" className="mt-4">
          <DetailedResultsSection
            metrics={bt.metrics}
            equityCurve={bt.equity_curve ?? null}
            buyAndHoldCurve={buyAndHoldPoints}
            initialCapital={bt.initial_capital}
            trades={tradeItems}
            tradesTruncated={truncated}
          />
        </TabsContent>

        <TabsContent value="trade-analysis" className="mt-4 space-y-8">
          <TradeAnalyticsSection
            metrics={bt.metrics}
            trades={tradeItems ?? []}
            truncated={truncated}
          />
          <TradeAnalysis metrics={bt.metrics} trades={tradeItems} />
        </TabsContent>

        <TabsContent value="runup-drawdown" className="mt-4">
          <RunupDrawdownSection
            metrics={bt.metrics}
            initialCapital={bt.initial_capital}
          />
        </TabsContent>

        <TabsContent value="trades" className="mt-4 space-y-3">
          <div className="flex justify-end">
            <Link
              href={`/backtests/${currentId}/trades`}
              className="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline"
              data-testid="trade-detail-link"
            >
              상세 보기
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
          {trades.isLoading ? (
            <p className="text-sm text-muted-foreground">거래 불러오는 중…</p>
          ) : trades.isError ? (
            <p className="text-sm text-destructive">
              거래 기록 로드 실패: {trades.error?.message}
            </p>
          ) : (
            <TradeLedgerTable
              trades={tradeItems ?? []}
              filenamePrefix={`backtest-${currentId.slice(0, 8)}`}
            />
          )}
        </TabsContent>

        <TabsContent value="stress-test" className="mt-4">
          <StressTestPanel backtestId={bt.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
