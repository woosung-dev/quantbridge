"use client";

// C13 진짜 OOS — 옵티마이저 spec(param_space+kind)로 fold별 재최적화 walk-forward CTA.
// 각 fold 가 자기 in-sample 구간에서만 재최적화 → out-of-sample 에 적용 = 진짜 OOS.
// 신규 파이프라인 없이 기존 stress-test walk-forward submit/poll + WalkForwardBarChart 재사용.

import { useState } from "react";
import { toast } from "sonner";

import { WalkForwardBarChart } from "@/app/(dashboard)/backtests/_components/walk-forward-bar-chart";
import { Button } from "@/components/ui/button";
import { useCreateWalkForward, useStressTest } from "@/features/backtest/hooks";
import type { OptimizationKind, ParamSpace } from "@/features/optimizer/schemas";

// stress-test-panel 의 walk-forward 기본값과 동일 (재사용 일관성).
const WF_DEFAULTS = {
  train_bars: 500,
  test_bars: 100,
  step_bars: 100,
  max_folds: 20,
} as const;

interface Props {
  backtestId: string;
  paramSpace: ParamSpace;
  kind: OptimizationKind;
}

export function OptimizerOosEvaluation({ backtestId, paramSpace, kind }: Props) {
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
      params: {
        ...WF_DEFAULTS,
        optimizer_param_space: paramSpace,
        optimizer_kind: kind,
      },
    });
  };

  const wfResult =
    stressData?.status === "completed" &&
    stressData.kind === "walk_forward" &&
    stressData.walk_forward_result
      ? stressData.walk_forward_result
      : null;

  return (
    <section className="space-y-3 rounded border border-border bg-muted/10 p-3">
      <div className="space-y-1">
        <h3 className="text-sm font-medium">
          최적화 OOS 검증 (진짜 walk-forward)
        </h3>
        <p className="text-xs text-muted-foreground">
          각 fold 는 자신의 in-sample(학습) 구간에서만 파라미터를 재최적화하고
          out-of-sample(검증) 구간에 적용합니다 — 진짜 out-of-sample. IS≫OOS =
          과최적 경고.
        </p>
        <p className="text-xs text-muted-foreground">
          단 (1) 탐색공간·목적함수는 사람이 고정, (2) fold 수가 적으면 표본이 작고,
          (3) 거래비용·슬리피지는 백테스트 가정값입니다.
        </p>
      </div>

      <Button onClick={handleRun} disabled={wfMutation.isPending || isActive}>
        최적화 Walk-Forward OOS 검증 (fold별 재최적화)
      </Button>

      {activeStressTestId === null ? null : (
        <div className="rounded border bg-card p-3">
          {stressData?.status === "queued" ? (
            <p className="text-sm text-muted-foreground">대기 중…</p>
          ) : null}

          {stressData?.status === "running" ? (
            <p className="text-sm text-muted-foreground">
              실행 중… (2초 간격 자동 새로고침 · fold별 재최적화는 시간이 더
              걸립니다)
            </p>
          ) : null}

          {stressData?.status === "failed" ? (
            <p className="text-sm text-destructive">
              실패: {stressData.error ?? "알 수 없는 오류"}
            </p>
          ) : null}

          {wfResult ? (
            <div className="space-y-2">
              {wfResult.reoptimized_per_fold ? (
                <span className="inline-block rounded bg-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                  각 fold 재최적화됨 (진짜 OOS)
                </span>
              ) : null}
              {wfResult.degenerate_folds_skipped > 0 ? (
                <p className="text-xs text-amber-600 dark:text-amber-400">
                  ⚠️ {wfResult.degenerate_folds_skipped}개 fold 제외 — 해당 학습
                  구간에서 전략이 거래를 내지 못했습니다 (취약성 신호).
                </p>
              ) : null}
              {wfResult.reoptimized_per_fold ? (
                <details className="text-xs">
                  <summary className="cursor-pointer text-muted-foreground">
                    fold별 재최적화 파라미터 (drift 클수록 불안정)
                  </summary>
                  <ul className="mt-1 space-y-0.5">
                    {wfResult.folds.map((f) => (
                      <li key={f.fold_index} className="text-muted-foreground">
                        fold {f.fold_index + 1}:{" "}
                        {f.selected_params
                          ? Object.entries(f.selected_params)
                              .map(([k, v]) => `${k}=${v}`)
                              .join(", ")
                          : "—"}
                      </li>
                    ))}
                  </ul>
                </details>
              ) : null}
              <WalkForwardBarChart result={wfResult} />
            </div>
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
