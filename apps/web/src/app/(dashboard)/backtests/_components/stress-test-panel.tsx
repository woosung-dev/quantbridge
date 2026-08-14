"use client";

// Phase C: Stress Test 탭 컨테이너.
// - 실행 버튼 4개 (Monte Carlo / Walk-Forward / Cost Assumption / Param Stability) 로 mutation → activeStressTestId.
// - useStressTest 가 refetchInterval 함수 기반 polling (terminal status 에서 자동 stop — LESSON-004).
// - BE 응답은 kind 별 필드 (monte_carlo_result / walk_forward_result / cost_assumption_result / param_stability_result) 이므로 discriminator 로 분기.
// - Sprint 50: Cost Assumption Sensitivity = fees x slippage 9-cell preset 즉시 submit (MVP).
// - Sprint 52 BL-223: Param Stability = 2 var_name x 3 value preset form (사용자 strategy InputDecl 변수명 입력).

import { useState } from "react";
import { toast } from "sonner";

import { TapeProgress } from "@/components/tape/tape-progress";
import { Button } from "@/components/ui/button";
import {
  useCreateCostAssumption,
  useCreateMonteCarlo,
  useCreateParamStability,
  useCreateWalkForward,
  useLatestStressTest,
  useStressTest,
} from "@/features/backtest/hooks";

import { CostAssumptionHeatmap } from "@/app/(dashboard)/backtests/_components/charts/cost-assumption-heatmap";
import { MonteCarloFanChart } from "@/app/(dashboard)/backtests/_components/charts/monte-carlo-fan-chart";
import { MonteCarloSummaryTable } from "@/app/(dashboard)/backtests/_components/monte-carlo-summary-table";
import { ParamStabilityForm } from "@/app/(dashboard)/backtests/_components/param-stability-form";
import { ParamStabilityHeatmap } from "@/app/(dashboard)/backtests/_components/charts/param-stability-heatmap";
import { WalkForwardBarChart } from "@/app/(dashboard)/backtests/_components/charts/walk-forward-bar-chart";
import { DEFAULT_FEES_PCT, DEFAULT_SLIPPAGE_PCT } from "@/features/backtest/cost-defaults";

interface Props {
  backtestId: string;
}

export function StressTestPanel({ backtestId }: Props) {
  const [activeStressTestId, setActiveStressTestId] = useState<string | null>(
    null,
  );
  const [showParamStabilityForm, setShowParamStabilityForm] = useState(false);

  const mcMutation = useCreateMonteCarlo({
    onSuccess: (created) => setActiveStressTestId(created.stress_test_id),
    onError: (err) => toast.error(`Monte Carlo 실행 실패: ${err.message}`),
  });
  const wfMutation = useCreateWalkForward({
    onSuccess: (created) => setActiveStressTestId(created.stress_test_id),
    onError: (err) => toast.error(`Walk-Forward 실행 실패: ${err.message}`),
  });
  const caMutation = useCreateCostAssumption({
    onSuccess: (created) => setActiveStressTestId(created.stress_test_id),
    onError: (err) =>
      toast.error(`Cost Assumption Sensitivity 실행 실패: ${err.message}`),
  });
  const psMutation = useCreateParamStability({
    onSuccess: (created) => {
      setActiveStressTestId(created.stress_test_id);
      setShowParamStabilityForm(false);
    },
    onError: (err) =>
      toast.error(`Param Stability 실행 실패: ${err.message}`),
  });
  const latestStressTest = useLatestStressTest(backtestId);
  const displayedStressTestId =
    activeStressTestId ?? latestStressTest.data?.id ?? null;
  const stress = useStressTest(displayedStressTestId);

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

  const handleRunCostAssumption = () => {
    // Sprint 50 MVP — 9-cell preset. customization 은 Sprint 51 BL-220 와 함께.
    //
    // ★★[BL-730] — 격자에 **현재 기본값이 반드시 들어가야 한다.** 종전 격자의 최저점은
    //   fees 0.0005 / slippage 0.0001 이라 실제 기본값(0.00055 / 0.00014)이 **격자 밖**이었다.
    //   그러면 「지금 설정으로 돌리면 어떻게 되나」를 이 패널로 재현할 수 없고, 민감도 표의
    //   어느 칸도 운영 실측과 대응하지 않는다. [BL-698] 이 같은 병의 다른 판이었다
    //   (`step="0.0001"` 격자가 기본값을 입력 불가로 만들었다).
    //
    // ★★기본값을 **넣되 종전 상단을 지운다**는 뜻이 아니다 (2026-08-15 codex Standards-5).
    //   초판은 배수 1x/2x/4x 로 잡았는데, 그러면 slippage 상단이 0.001 → 0.00056 으로
    //   **거의 절반**이 된다 — 사용자가 보던 보수적 시나리오와 과거 실행과의 비교 범위가
    //   함께 사라진다. 기본값 포함과 상단 보존은 **양립 가능**하므로 둘 다 한다:
    //   최저점 = 현재 기본값, 나머지 둘 = 종전 격자의 중간·상단.
    const grid = {
      fees: [String(DEFAULT_FEES_PCT), "0.001", "0.002"],
      slippage: [String(DEFAULT_SLIPPAGE_PCT), "0.0005", "0.001"],
    };
    caMutation.mutate({
      backtest_id: backtestId,
      params: { param_grid: grid },
    });
  };

  const stressData = stress.data;

  // polling 중 (queued/running) 버튼 재클릭 시 activeStressTestId 가 교체되어
  // 첫 stress test 가 UI 에서 고아가 되는 것을 방지 (Celery 에서는 계속 실행).
  const isStressTestActive =
    stressData?.status === "queued" || stressData?.status === "running";
  const isAnyMutationPending =
    mcMutation.isPending ||
    wfMutation.isPending ||
    caMutation.isPending ||
    psMutation.isPending;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Button
          onClick={handleRunMonteCarlo}
          disabled={isAnyMutationPending || isStressTestActive}
        >
          Monte Carlo 실행
        </Button>
        <Button
          variant="outline"
          onClick={handleRunWalkForward}
          disabled={isAnyMutationPending || isStressTestActive}
        >
          Walk-Forward 실행
        </Button>
        <Button
          variant="outline"
          onClick={handleRunCostAssumption}
          disabled={isAnyMutationPending || isStressTestActive}
        >
          Cost Assumption Sensitivity 실행
        </Button>
        <Button
          variant="outline"
          onClick={() => setShowParamStabilityForm((v) => !v)}
          disabled={isAnyMutationPending || isStressTestActive}
        >
          {showParamStabilityForm
            ? "Param Stability 닫기"
            : "Param Stability 실행"}
        </Button>
      </div>

      {showParamStabilityForm ? (
        <ParamStabilityForm
          backtestId={backtestId}
          onSubmit={(payload) => psMutation.mutate(payload)}
          isSubmitting={psMutation.isPending}
          onCancel={() => setShowParamStabilityForm(false)}
        />
      ) : null}

      {displayedStressTestId === null ? (
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
            <div className="space-y-2">
              <TapeProgress value={null} ariaLabel="스트레스 테스트 진행률" />
              <p className="text-sm text-muted-foreground">
                실행 중… (2초 간격 자동 새로고침)
              </p>
            </div>
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

          {stressData?.status === "completed" &&
          stressData.kind === "cost_assumption_sensitivity" &&
          stressData.cost_assumption_result ? (
            <CostAssumptionHeatmap result={stressData.cost_assumption_result} />
          ) : null}

          {stressData?.status === "completed" &&
          stressData.kind === "param_stability" &&
          stressData.param_stability_result ? (
            <ParamStabilityHeatmap
              result={stressData.param_stability_result}
            />
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
