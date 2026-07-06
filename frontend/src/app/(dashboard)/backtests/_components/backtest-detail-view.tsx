"use client";

import { ArrowLeft, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

import { TapeProgress } from "@/components/tape/tape-progress";
import { Button } from "@/components/ui/button";
import { useBacktest, useBacktestProgress } from "@/features/backtest/hooks";
import { formatDate } from "@/features/backtest/utils";

const TERMINAL_STATUSES = ["completed", "failed", "cancelled"] as const;

import { BacktestStatusBadge } from "@/app/(dashboard)/backtests/_components/status-badge";
import { BacktestReportShell } from "@/app/(dashboard)/backtests/_components/report/backtest-report-shell";
import { RerunButton } from "@/app/(dashboard)/backtests/_components/rerun-button";
import { ShareButton } from "@/app/(dashboard)/backtests/_components/share-button";

export function BacktestDetailView({ id }: { id: string }) {
  const detail = useBacktest(id);
  const progress = useBacktestProgress(id);

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
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            {formatDate(bt.period_start)}
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            {formatDate(bt.period_end)}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {effectiveStatus === "completed" ? (
            <ShareButton backtestId={bt.id} isEnabled />
          ) : null}
          <RerunButton
            backtest={bt}
            isEnabled={(TERMINAL_STATUSES as readonly string[]).includes(
              effectiveStatus,
            )}
          />
          <Link
            href="/backtests"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            목록
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

      {/* TV parity IA — 완료 상태는 report shell 이 전담 (KeyStatsStrip +
          AssumptionsCard + PerformanceChart 상시 + 섹션 탭). */}
      {effectiveStatus === "completed" && bt.metrics ? (
        <BacktestReportShell backtest={bt} currentId={id} />
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
    <div className="qb-card-fade-in flex flex-col gap-3 rounded-lg border bg-card p-4">
      <TapeProgress value={null} ariaLabel={`${label} 진행률`} />
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
    <div className="flex flex-col gap-3 rounded-lg border border-destructive/40 bg-destructive-subtle p-4">
      <p className="text-sm text-destructive">{message}</p>
      <div>
        <Button variant="outline" size="sm" onClick={onRetry}>
          다시 시도
        </Button>
      </div>
    </div>
  );
}
