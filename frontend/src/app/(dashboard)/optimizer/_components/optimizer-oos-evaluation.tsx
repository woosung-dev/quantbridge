"use client";

// C13 — 옵티마이저 최적 파라미터를 walk-forward OOS 로 검증하는 CTA + 결과 임베드.
// 신규 파이프라인 없이 기존 stress-test walk-forward submit/poll + WalkForwardBarChart 재사용
// (best_params 만 주입). 과최적화(IS≫OOS) 정직 경고가 목적.

import { useState } from "react";
import { toast } from "sonner";

import { WalkForwardBarChart } from "@/app/(dashboard)/backtests/_components/walk-forward-bar-chart";
import { Button } from "@/components/ui/button";
import { useCreateWalkForward, useStressTest } from "@/features/backtest/hooks";

// stress-test-panel 의 walk-forward 기본값과 동일 (재사용 일관성).
const WF_DEFAULTS = {
  train_bars: 500,
  test_bars: 100,
  step_bars: 100,
  max_folds: 20,
} as const;

interface Props {
  backtestId: string;
  bestParams: Record<string, number>;
}

export function OptimizerOosEvaluation({ backtestId, bestParams }: Props) {
  const [activeStressTestId, setActiveStressTestId] = useState<string | null>(
    null,
  );

  const wfMutation = useCreateWalkForward({
    onSuccess: (created) => setActiveStressTestId(created.stress_test_id),
    onError: (err) =>
      toast.error(`Walk-Forward OOS 검증 실행 실패: ${err.message}`),
  });
  const stress = useStressTest(activeStressTestId);
  const stressData = stress.data;

  const isActive =
    stressData?.status === "queued" || stressData?.status === "running";

  const handleRun = () => {
    wfMutation.mutate({
      backtest_id: backtestId,
      params: { ...WF_DEFAULTS, best_params: bestParams },
    });
  };

  return (
    <section className="space-y-3 rounded border border-border bg-muted/10 p-3">
      <div className="space-y-1">
        <h3 className="text-sm font-medium">
          최적 파라미터 OOS 검증 (과최적 경고)
        </h3>
        <p className="text-xs text-muted-foreground">
          최적 파라미터를 롤링 윈도우로 검증 — IS/OOS 일관성(degradation). IS≫OOS =
          과최적 경고.
        </p>
        <p className="text-xs text-muted-foreground">
          단, 이 최적 파라미터는 전체 기간(OOS 구간 포함)에서 선택돼 모든 fold 에
          고정 적용됩니다(fold별 재최적화 아님). 따라서 OOS 는 파라미터 선택 기간과
          겹쳐, 진짜 out-of-sample 보다 낙관적일 수 있습니다.
        </p>
      </div>

      <Button onClick={handleRun} disabled={wfMutation.isPending || isActive}>
        최적 파라미터로 Walk-Forward OOS 검증
      </Button>

      {activeStressTestId === null ? null : (
        <div className="rounded border bg-card p-3">
          {stressData?.status === "queued" ? (
            <p className="text-sm text-muted-foreground">대기 중…</p>
          ) : null}

          {stressData?.status === "running" ? (
            <p className="text-sm text-muted-foreground">
              실행 중… (2초 간격 자동 새로고침)
            </p>
          ) : null}

          {stressData?.status === "failed" ? (
            <p className="text-sm text-destructive">
              실패: {stressData.error ?? "알 수 없는 오류"}
            </p>
          ) : null}

          {stressData?.status === "completed" &&
          stressData.kind === "walk_forward" &&
          stressData.walk_forward_result ? (
            <WalkForwardBarChart result={stressData.walk_forward_result} />
          ) : null}

          {stress.isError ? (
            <p className="text-sm text-destructive">
              상세 로드 실패: {stress.error?.message ?? "unknown"}
            </p>
          ) : null}
        </div>
      )}
    </section>
  );
}
