"use client";

// C13 진짜 OOS — 옵티마이저 spec(param_space+kind)로 fold별 재최적화 walk-forward CTA.
// 각 fold 가 자기 in-sample 구간에서만 재최적화 → out-of-sample 에 적용 = 진짜 OOS.
// 신규 파이프라인 없이 기존 stress-test walk-forward submit/poll + WalkForwardBarChart 재사용.
// C 이식 (W3-C): .section/.card/.trust-*/.chart-note/.disclaimer 소비. 실 API(stress-test WFO)가 받침.

import { AlertTriangleIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { WalkForwardBarChart } from "@/features/backtest/components/charts/walk-forward-bar-chart";
import { InfoIcon } from "@/components/info-icon";
import { TapeProgress } from "@/components/tape/tape-progress";
import { useCreateWalkForward, useStressTest } from "@/features/backtest/hooks";
import type { OptimizationKind, ParamSpace } from "@/features/optimizer/schemas";
import { EMPTY_CELL } from "@/lib/labels";

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
  /** 페이지 내 섹션 번호 — grid 는 03 파라미터 안정성 뒤라 04, bayesian/genetic 은 03. */
  sectionNum: string;
}

export function OptimizerOosEvaluation({ backtestId, paramSpace, kind, sectionNum }: Props) {
  const [activeStressTestId, setActiveStressTestId] = useState<string | null>(null);

  const wfMutation = useCreateWalkForward({
    onSuccess: (created) => setActiveStressTestId(created.stress_test_id),
    onError: (err) => toast.error(`Walk-Forward OOS 검증 실행 실패: ${err.message}`),
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
    <section className="section" aria-label="최적화 OOS 검증">
      <header className="section-head">
        <p className="eyebrow">
          <span className="num">{sectionNum}</span> OOS 검증
        </p>
        <h2 className="section-title">최적화 OOS 검증 (진짜 walk-forward)</h2>
        <p className="section-desc">
          각 fold 는 자신의 in-sample(학습) 구간에서만 파라미터를 재최적화하고
          out-of-sample(검증) 구간에 적용합니다. 진짜 out-of-sample 입니다. IS 가 OOS 보다 크게
          높으면 과최적 경고입니다.
        </p>
      </header>

      <div className="card">
        <div className="card-body">
          <p className="chart-note" style={{ paddingLeft: 0, paddingTop: 0 }}>
            <span>
              단 (1) 탐색공간·목적함수는 사람이 고정, (2) fold 수가 적으면 표본이 작고, (3)
              거래비용·슬리피지는 백테스트 가정값입니다.
            </span>
          </p>

          <button
            type="button"
            className="btn btn-primary"
            onClick={handleRun}
            disabled={wfMutation.isPending || isActive}
          >
            최적화 Walk-Forward OOS 검증 (fold별 재최적화)
          </button>

          {activeStressTestId === null ? null : (
            <div className="card" style={{ marginTop: 16 }}>
              <div className="card-body">
                {stressData?.status === "queued" ? (
                  <p className="section-desc">대기 중입니다.</p>
                ) : null}

                {stressData?.status === "running" ? (
                  <p className="section-desc">
                    실행 중입니다. 2초 간격으로 자동 새로고침하며, fold별 재최적화는 시간이 더
                    걸립니다.
                  </p>
                ) : null}

                {isActive ? (
                  <TapeProgress
                    value={null}
                    ariaLabel="Walk-Forward OOS 검증 진행률"
                    className="mt-2"
                  />
                ) : null}

                {stressData?.status === "failed" ? (
                  <p className="state-code" role="alert">
                    실패: {stressData.error ?? "알 수 없는 오류"}
                  </p>
                ) : null}

                {wfResult ? (
                  <div className="space-y-2">
                    {wfResult.reoptimized_per_fold ? (
                      <span className="chip done">각 fold 재최적화됨 (진짜 OOS)</span>
                    ) : null}
                    {wfResult.degenerate_folds_skipped > 0 ? (
                      <p className="chart-note" style={{ paddingLeft: 0 }}>
                        <AlertTriangleIcon aria-hidden="true" />
                        <span>
                          {wfResult.degenerate_folds_skipped}개 fold 제외. 해당 학습 구간에서
                          전략이 거래를 내지 못했습니다 (취약성 신호).
                        </span>
                      </p>
                    ) : null}
                    {wfResult.reoptimized_per_fold ? (
                      <details className="chart-note" style={{ paddingLeft: 0 }}>
                        <summary style={{ cursor: "pointer" }}>
                          fold별 재최적화 파라미터 (drift 클수록 불안정)
                        </summary>
                        <ul style={{ marginTop: 6 }}>
                          {wfResult.folds.map((f) => (
                            <li key={f.fold_index} className="dim">
                              fold {f.fold_index + 1}:{" "}
                              {f.selected_params
                                ? Object.entries(f.selected_params)
                                    .map(([k, v]) => `${k}=${v}`)
                                    .join(", ")
                                : EMPTY_CELL}
                            </li>
                          ))}
                        </ul>
                      </details>
                    ) : null}
                    <WalkForwardBarChart result={wfResult} />
                  </div>
                ) : null}

                {stress.isError ? (
                  <p className="state-code" role="alert">
                    상세 로드 실패: {stress.error?.message ?? "unknown"}
                  </p>
                ) : null}
              </div>
            </div>
          )}
        </div>

        <p className="disclaimer">
          <InfoIcon />
          <span>
            이 검증에도 한계가 있습니다. 탐색 공간과 목적 함수는 사람이 고정하고, fold 수가 적으면
            표본이 작으며, 거래 비용과 슬리피지는 백테스트 가정값입니다.
          </span>
        </p>
      </div>
    </section>
  );
}
