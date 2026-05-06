"use client";

// Phase C: Stress Test 탭 컨테이너.
// - 실행 버튼 2개 (Monte Carlo / Walk-Forward) 로 mutation → activeStressTestId 설정.
// - useStressTest 가 refetchInterval 함수 기반 polling (terminal status 에서 자동 stop — LESSON-004).
// - BE 응답은 kind 별 필드 (monte_carlo_result / walk_forward_result) 이므로 discriminator 로 분기.

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  useCreateMonteCarlo,
  useCreateWalkForward,
  useStressTest,
} from "@/features/backtest/hooks";

import { MonteCarloFanChart } from "./monte-carlo-fan-chart";
import { MonteCarloSummaryTable } from "./monte-carlo-summary-table";
import { WalkForwardBarChart } from "./walk-forward-bar-chart";

interface Props {
  backtestId: string;
}

export function StressTestPanel({ backtestId }: Props) {
  const [activeStressTestId, setActiveStressTestId] = useState<string | null>(
    null,
  );

  const mcMutation = useCreateMonteCarlo({
    onSuccess: (created) => setActiveStressTestId(created.stress_test_id),
    onError: (err) => toast.error(`Monte Carlo 실행 실패: ${err.message}`),
  });
  const wfMutation = useCreateWalkForward({
    onSuccess: (created) => setActiveStressTestId(created.stress_test_id),
    onError: (err) => toast.error(`Walk-Forward 실행 실패: ${err.message}`),
  });
  const stress = useStressTest(activeStressTestId);

  const handleRunMonteCarlo = () => {
    mcMutation.mutate({
      backtest_id: backtestId,
      params: { n_samples: 1000, seed: 42 },
    });
  };

  const handleRunWalkForward = () => {
    wfMutation.mutate({
      backtest_id: backtestId,
      params: {
        train_bars: 500,
        test_bars: 100,
        step_bars: 100,
        max_folds: 20,
      },
    });
  };

  const stressData = stress.data;

  // polling 중 (queued/running) 버튼 재클릭 시 activeStressTestId 가 교체되어
  // 첫 stress test 가 UI 에서 고아가 되는 것을 방지 (Celery 에서는 계속 실행).
  const isStressTestActive =
    stressData?.status === "queued" || stressData?.status === "running";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Button
          onClick={handleRunMonteCarlo}
          disabled={
            mcMutation.isPending || wfMutation.isPending || isStressTestActive
          }
        >
          Monte Carlo 실행
        </Button>
        <Button
          variant="outline"
          onClick={handleRunWalkForward}
          disabled={
            mcMutation.isPending || wfMutation.isPending || isStressTestActive
          }
        >
          Walk-Forward 실행
        </Button>
      </div>

      {activeStressTestId === null ? (
        <p className="text-sm text-muted-foreground">
          위 버튼을 눌러 이 백테스트에 대한 스트레스 테스트를 실행하세요.
        </p>
      ) : (
        <div className="rounded-lg border bg-card p-4">
          {stress.isLoading && !stressData ? (
            <p className="text-sm text-muted-foreground">불러오는 중…</p>
          ) : null}

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
          stressData.kind === "monte_carlo" &&
          stressData.monte_carlo_result ? (
            // Sprint 37 BL-183: 숫자 요약표 (위) + fan chart (아래) 조합.
            // 사용자가 수치 기반 의사결정과 분포 시각 둘 다 확보 가능.
            <div className="space-y-4">
              <MonteCarloSummaryTable
                mcResult={stressData.monte_carlo_result}
              />
              <MonteCarloFanChart result={stressData.monte_carlo_result} />
            </div>
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
    </div>
  );
}
