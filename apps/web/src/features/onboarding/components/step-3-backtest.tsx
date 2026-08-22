"use client";

// 온보딩 스텝 3: 샘플 전략 백테스트 실행 — C 디자인 언어 이식 (W3-E).
// 기본 파라미터: BTCUSDT 1H, 최근 30일, initial_capital 10000.
// useBacktestProgress 로 polling (LESSON-004 준수 — refetchInterval 순수 함수).

import { useEffect, useRef, useState } from "react";
import { AlertCircleIcon, CheckIcon, LoaderIcon } from "lucide-react";
import { toast } from "sonner";

import { useBacktestProgress, useCreateBacktest } from "@/features/backtest/hooks";
import { DEFAULT_FEES_PCT, DEFAULT_SLIPPAGE_PCT } from "@/features/backtest/cost-defaults";

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
      // ★[BL-730] — 이 경로는 값을 **명시적으로 실어 보내므로** 낡으면 BE 기본값이 아예
      //   안 쓰인다. 0.001/0.0005 를 하드코딩해 왕복 0.30% 를 제출하고 있었다.
      leverage: 1,
      fees_pct: DEFAULT_FEES_PCT,
      slippage_pct: DEFAULT_SLIPPAGE_PCT,
      include_funding: true,
      fill_timing: "bar_close",
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

  const isFailed = progressStatus === "failed" || progressStatus === "cancelled";
  const isRunning = create.isPending || progressStatus === "queued" || progressStatus === "running";
  const isIdle = !isRunning && !isFailed && progressStatus === undefined && !backtestId;

  return (
    <div>
      <div className="ob-lede">
        <span className="ob-lede-icon" aria-hidden="true">
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="6" y1="20" x2="6" y2="14" />
            <line x1="12" y1="20" x2="12" y2="4" />
            <line x1="18" y1="20" x2="18" y2="10" />
          </svg>
        </span>
        <div>
          <h2 className="ob-heading">백테스트 실행</h2>
          <p className="ob-subtle break-keep">
            BTC/USDT 1H · 최근 {LOOKBACK_DAYS}일 · 초기 자본 ${INITIAL_CAPITAL.toLocaleString()}
          </p>
        </div>
      </div>

      <div className="ob-run" aria-live="polite" aria-busy={isRunning || undefined}>
        {isRunning && (
          <>
            <div className="ob-run-row">
              <LoaderIcon
                className="text-[color:var(--copper)] motion-safe:animate-spin"
                strokeWidth={2}
                aria-hidden="true"
              />
              <div>
                <p className="ob-run-title">
                  {create.isPending
                    ? "백테스트 요청 중"
                    : progressStatus === "queued"
                      ? "대기열에서 순서를 기다리는 중"
                      : "시장 데이터 수집 및 계산 중"}
                </p>
                <p className="ob-run-sub">백테스트 엔진이 계산 중입니다. 보통 5~30초 걸립니다.</p>
              </div>
            </div>
            {/* 스켈레톤 — 계산 중 결과 자리를 예약한다 (KIT 상태 4종 중 스켈레톤). */}
            <div
              className="sk sk-line"
              style={{ width: "58%", marginTop: 16 }}
              aria-hidden="true"
            />
          </>
        )}
        {progressStatus === "completed" && (
          <div className="ob-run-row">
            <CheckIcon className="ob-run-done" strokeWidth={2.4} aria-hidden="true" />
            <p className="ob-run-title ob-run-done">
              백테스트가 완료되었습니다. 결과로 이동합니다.
            </p>
          </div>
        )}
        {isFailed && (
          <p role="alert" className="ob-run-row ob-run-fail">
            <AlertCircleIcon strokeWidth={2} aria-hidden="true" />
            <span>백테스트가 실패했습니다. {progress.data?.error ?? "알 수 없는 오류"}</span>
          </p>
        )}
        {isIdle && <p className="ob-run-sub">전략이 준비되면 자동으로 실행됩니다.</p>}
      </div>

      {submitError !== null && (
        <p
          role="alert"
          className="mb-4 flex items-start gap-2 rounded-[var(--r)] border border-[color:var(--warn)] bg-[color:var(--warn-soft)] p-3 text-xs text-[color:var(--warn)]"
        >
          <AlertCircleIcon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span className="break-all">{submitError}</span>
        </p>
      )}

      <div className="ob-actions between">
        <button className="btn btn-ghost" type="button" onClick={onBack} disabled={isRunning}>
          ← 이전
        </button>
        {isFailed && (
          <button
            className="btn"
            type="button"
            onClick={() => {
              hasTriggeredRef.current = false;
              setBacktestId(null);
              setSubmitError(null);
            }}
          >
            다시 시도
          </button>
        )}
      </div>
    </div>
  );
}
