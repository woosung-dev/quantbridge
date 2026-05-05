"use client";

// H2 Sprint 11 Phase D Step 3: 샘플 전략 백테스트 실행.
// 기본 파라미터: BTCUSDT 1H, 최근 30일, initial_capital 10000.
// useBacktestProgress 로 polling (LESSON-004 준수 — refetchInterval 순수 함수).

import { useEffect, useRef, useState } from "react";
import { AlertCircleIcon, LoaderIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  useBacktestProgress,
  useCreateBacktest,
} from "@/features/backtest/hooks";

const INITIAL_CAPITAL = 10_000;
const LOOKBACK_DAYS = 30;

function toIsoMinute(date: Date): string {
  // Drop milliseconds to keep URLs/logs tidy. FastAPI 는 offset 포함 ISO 를 요구.
  return new Date(Math.floor(date.getTime() / 1000) * 1000).toISOString();
}

function buildDefaultWindow() {
  const end = new Date();
  const start = new Date(end.getTime() - LOOKBACK_DAYS * 24 * 60 * 60 * 1000);
  return {
    period_start: toIsoMinute(start),
    period_end: toIsoMinute(end),
  };
}

export function Step3Backtest({
  strategyId,
  onBacktestReady,
  onBack,
}: {
  strategyId: string | null;
  onBacktestReady: (backtestId: string) => void;
  onBack: () => void;
}) {
  const [backtestId, setBacktestId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const hasTriggeredRef = useRef(false);
  const hasPropagatedRef = useRef(false);

  const create = useCreateBacktest({
    onSuccess: (data) => {
      setBacktestId(data.backtest_id);
    },
    onError: (err) => {
      setSubmitError(err.message);
      toast.error(`백테스트 요청 실패: ${err.message}`);
    },
  });

  const progress = useBacktestProgress(backtestId ?? undefined);

  // 마운트 시 1회만 create 요청 — strategyId 가 있고 아직 trigger 안 된 경우.
  // LESSON-004: effect deps 는 primitive/stable 참조만.
  useEffect(() => {
    if (!strategyId) return;
    if (hasTriggeredRef.current) return;
    if (create.isPending) return;
    if (backtestId !== null) return;
    hasTriggeredRef.current = true;
    const window = buildDefaultWindow();
    create.mutate({
      strategy_id: strategyId,
      symbol: "BTCUSDT",
      timeframe: "1h",
      period_start: window.period_start,
      period_end: window.period_end,
      initial_capital: INITIAL_CAPITAL,
      // Sprint 31 BL-162a — Bybit Perpetual taker 표준 default (onboarding fixed).
      leverage: 1,
      fees_pct: 0.001,
      slippage_pct: 0.0005,
      include_funding: true,
    });
  }, [strategyId, create, backtestId]);

  // completed 시 부모에게 한 번만 알림 (hasPropagatedRef 로 idempotent).
  const progressStatus = progress.data?.status;
  useEffect(() => {
    if (progressStatus !== "completed") return;
    if (!backtestId) return;
    if (hasPropagatedRef.current) return;
    hasPropagatedRef.current = true;
    onBacktestReady(backtestId);
  }, [progressStatus, backtestId, onBacktestReady]);

  const isFailed =
    progressStatus === "failed" || progressStatus === "cancelled";
  const isRunning =
    create.isPending ||
    progressStatus === "queued" ||
    progressStatus === "running";

  return (
    <div>
      <h2 className="mb-2 font-display text-lg font-semibold">백테스트 실행</h2>
      <p className="mb-5 text-xs text-[color:var(--text-muted)] break-keep">
        BTC/USDT 1H · 최근 {LOOKBACK_DAYS}일 · 초기 자본 ${INITIAL_CAPITAL.toLocaleString()}
      </p>

      <div className="mb-6 min-h-[140px] rounded-[var(--radius-md)] border border-[color:var(--border)] bg-[color:var(--bg-alt)] p-5">
        {isRunning && (
          <div
            className="flex items-center gap-3 text-sm text-[color:var(--text-secondary)]"
            aria-live="polite"
          >
            <LoaderIcon
              className="size-5 animate-spin text-[color:var(--primary)]"
              strokeWidth={2}
            />
            <div>
              <p className="font-medium">
                {create.isPending
                  ? "백테스트 요청 중…"
                  : progressStatus === "queued"
                    ? "대기열에서 순서를 기다리는 중…"
                    : "시장 데이터 수집 및 계산 중…"}
              </p>
              <p className="text-xs text-[color:var(--text-muted)]">
                Celery worker 가 vectorbt 로 계산 중입니다. 보통 5~30초 걸립니다.
              </p>
            </div>
          </div>
        )}
        {progressStatus === "completed" && (
          <p
            className="text-sm font-medium text-[color:var(--success)]"
            aria-live="polite"
          >
            백테스트가 완료되었습니다. 결과로 이동합니다…
          </p>
        )}
        {isFailed && (
          <div
            role="alert"
            className="flex items-start gap-2 text-sm text-[color:var(--danger)]"
          >
            <AlertCircleIcon className="mt-0.5 size-4 shrink-0" />
            <span>
              백테스트가 실패했습니다 ({progressStatus}).{" "}
              {progress.data?.error ?? "알 수 없는 오류"}
            </span>
          </div>
        )}
        {!isRunning && !isFailed && progressStatus === undefined && !backtestId && (
          <p className="text-xs text-[color:var(--text-muted)]">
            전략이 준비되면 자동으로 실행됩니다.
          </p>
        )}
      </div>

      {submitError !== null && (
        <div
          role="alert"
          className="mb-4 flex items-start gap-2 rounded-[var(--radius-md)] border border-[color:var(--danger)] bg-[color:var(--danger-light,#fee2e2)] p-3 text-xs text-[color:var(--danger)]"
        >
          <AlertCircleIcon className="mt-0.5 size-4 shrink-0" />
          <span className="break-all">{submitError}</span>
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <Button variant="ghost" onClick={onBack} disabled={isRunning}>
          ← 이전
        </Button>
        {isFailed && (
          <Button
            variant="secondary"
            onClick={() => {
              hasTriggeredRef.current = false;
              setBacktestId(null);
              setSubmitError(null);
            }}
          >
            다시 시도
          </Button>
        )}
      </div>
    </div>
  );
}
