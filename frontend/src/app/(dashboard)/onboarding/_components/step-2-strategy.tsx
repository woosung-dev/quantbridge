"use client";

// H2 Sprint 11 Phase D Step 2: 샘플 EMA Crossover 전략 등록.
// 1) public/samples/ema-crossover.pine 을 fetch
// 2) POST /api/v1/strategies (useCreateStrategy)
// 3) store.setStrategy(id) 후 다음 step 으로 이동

import { useState } from "react";
import { AlertCircleIcon, SparklesIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
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

  const handleStart = async () => {
    setFetchError(null);
    setIsFetching(true);
    try {
      const res = await fetch(SAMPLE_PINE_URL, { cache: "no-store" });
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
      const message = err instanceof Error ? err.message : "알 수 없는 오류";
      setFetchError(message);
      toast.error(message);
    } finally {
      setIsFetching(false);
    }
  };

  const isBusy = isFetching || create.isPending;

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        <SparklesIcon
          className="size-5 text-[color:var(--primary)]"
          strokeWidth={1.8}
        />
        <h2 className="font-display text-lg font-semibold">샘플 전략으로 시작</h2>
      </div>
      <p className="mb-5 text-xs text-[color:var(--text-muted)] break-keep">
        EMA Crossover 전략이 자동으로 등록됩니다. ta.ema(close, 12/26) 교차 시점에 롱 진입·청산합니다.
      </p>

      <div className="mb-6 rounded-[var(--radius-md)] border border-[color:var(--border)] bg-[color:var(--bg-alt)] p-4">
        <h3 className="mb-2 text-sm font-semibold">EMA Crossover Demo</h3>
        <dl className="grid grid-cols-2 gap-y-1.5 text-xs">
          <dt className="text-[color:var(--text-muted)]">Fast EMA</dt>
          <dd className="font-mono">ta.ema(close, 12)</dd>
          <dt className="text-[color:var(--text-muted)]">Slow EMA</dt>
          <dd className="font-mono">ta.ema(close, 26)</dd>
          <dt className="text-[color:var(--text-muted)]">진입</dt>
          <dd className="font-mono">ta.crossover(fast, slow) → long</dd>
          <dt className="text-[color:var(--text-muted)]">청산</dt>
          <dd className="font-mono">ta.crossunder(fast, slow) → close</dd>
        </dl>
      </div>

      {fetchError !== null && (
        <div
          role="alert"
          className="mb-4 flex items-start gap-2 rounded-[var(--radius-md)] border border-[color:var(--danger)] bg-[color:var(--danger-light,#fee2e2)] p-3 text-xs text-[color:var(--danger)]"
        >
          <AlertCircleIcon className="mt-0.5 size-4 shrink-0" />
          <span className="break-all">{fetchError}</span>
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <Button variant="ghost" onClick={onBack} disabled={isBusy}>
          ← 이전
        </Button>
        <Button
          onClick={() => {
            void handleStart();
          }}
          disabled={isBusy}
          aria-label="샘플 전략 등록 및 다음 단계"
        >
          {isBusy ? "등록 중…" : "샘플로 시작하기 →"}
        </Button>
      </div>
    </div>
  );
}
