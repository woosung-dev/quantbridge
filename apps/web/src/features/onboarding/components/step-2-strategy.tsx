"use client";

// 온보딩 스텝 2: 샘플 EMA Crossover 전략 등록 — C 디자인 언어 이식 (W3-E).
// 1) public/samples/ema-crossover.pine 을 fetch
// 2) POST /api/v1/strategies (useCreateStrategy)
// 3) store.setStrategy(id) 후 다음 step 으로 이동

import { useEffect, useRef, useState } from "react";
import { AlertCircleIcon, Loader2Icon, SparklesIcon } from "lucide-react";
import { toast } from "sonner";

import { useCreateStrategy } from "@/features/strategy/hooks";

const SAMPLE_PINE_URL = "/samples/ema-crossover.pine";
const SAMPLE_STRATEGY_NAME = "EMA Crossover Demo (Onboarding)";
const SAMPLE_DESCRIPTION =
  "온보딩 샘플: ta.ema(close, 12/26) + ta.crossover/under 진입 조건.";

export function Step2Strategy({
  onStrategyReady,
  onBack,
}: {
  onStrategyReady: (strategyId: string) => void;
  onBack: () => void;
}) {
  const [isFetching, setIsFetching] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const create = useCreateStrategy();

  // 진행 중 샘플 fetch 를 unmount 시 중단 — stale 응답의 setState 방지.
  const abortRef = useRef<AbortController | null>(null);
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const handleStart = async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setFetchError(null);
    setIsFetching(true);
    try {
      const res = await fetch(SAMPLE_PINE_URL, {
        cache: "no-store",
        signal: controller.signal,
      });
      if (!res.ok) {
        throw new Error(`샘플 Pine 로드 실패 (status ${res.status})`);
      }
      const pineSource = await res.text();
      if (pineSource.trim().length === 0) {
        throw new Error("샘플 Pine 소스가 비어 있습니다");
      }
      create.mutate(
        {
          name: SAMPLE_STRATEGY_NAME,
          description: SAMPLE_DESCRIPTION,
          pine_source: pineSource,
          symbol: "BTCUSDT",
          timeframe: "1h",
          tags: ["onboarding", "sample"],
        },
        {
          onSuccess: (data) => {
            toast.success("샘플 전략이 등록되었습니다");
            onStrategyReady(data.id);
          },
          onError: (err) => {
            setFetchError(err.message);
            toast.error(`전략 등록 실패: ${err.message}`);
          },
        },
      );
    } catch (err) {
      if (controller.signal.aborted) return; // unmount/재시도 abort — 상태 갱신 생략
      const message = err instanceof Error ? err.message : "알 수 없는 오류";
      setFetchError(message);
      toast.error(message);
    } finally {
      if (!controller.signal.aborted) {
        setIsFetching(false);
      }
    }
  };

  const isBusy = isFetching || create.isPending;

  return (
    <div>
      <div className="ob-lede">
        <span className="ob-lede-icon" aria-hidden="true">
          <SparklesIcon strokeWidth={1.8} />
        </span>
        <div>
          <h2 className="ob-heading">샘플 전략으로 시작</h2>
          <p className="ob-subtle break-keep">
            EMA Crossover 전략이 자동으로 등록됩니다. ta.ema(close, 12/26) 교차
            시점에 롱 진입·청산합니다.
          </p>
        </div>
      </div>

      <div className="ob-aside">
        <p className="ob-aside-label">EMA Crossover Demo</p>
        <dl className="ob-spec">
          <dt>Fast EMA</dt>
          <dd>ta.ema(close, 12)</dd>
          <dt>Slow EMA</dt>
          <dd>ta.ema(close, 26)</dd>
          <dt>진입</dt>
          <dd>ta.crossover(fast, slow) → long</dd>
          <dt>청산</dt>
          <dd>ta.crossunder(fast, slow) → close</dd>
        </dl>
      </div>

      {fetchError !== null && (
        <p
          role="alert"
          className="mb-4 flex items-start gap-2 rounded-[var(--r)] border border-[color:var(--warn)] bg-[color:var(--warn-soft)] p-3 text-xs text-[color:var(--warn)]"
        >
          <AlertCircleIcon
            className="mt-0.5 size-4 shrink-0"
            aria-hidden="true"
          />
          <span className="break-all">{fetchError}</span>
        </p>
      )}

      <div className="ob-actions between">
        <button
          className="btn btn-ghost"
          type="button"
          onClick={onBack}
          disabled={isBusy}
        >
          ← 이전
        </button>
        <button
          className="btn btn-primary"
          type="button"
          onClick={() => {
            void handleStart();
          }}
          disabled={isBusy}
          aria-busy={isBusy || undefined}
          aria-label="샘플 전략 등록 및 다음 단계"
        >
          {isBusy && (
            <Loader2Icon
              className="size-4 motion-safe:animate-spin"
              aria-hidden="true"
            />
          )}
          {isBusy ? "등록 중" : "샘플로 시작하기"}
        </button>
      </div>
    </div>
  );
}
