// Sprint 54 — Optimizer 실행 목록 (status badge + objective + best 요약).
"use client";

import Link from "next/link";

import { useOptimizationRuns } from "@/features/optimizer/hooks";
import {
  OBJECTIVE_DIRECTION_LABEL,
  OBJECTIVE_METRIC_LABEL,
  OPTIMIZATION_STATUS_LABEL,
  OPTIMIZER_DOMAIN_LABEL,
  OPTIMIZER_LIST_HEADER,
} from "@/features/optimizer/labels";
import { CHIP_TONE_CLASS, EMPTY_CELL, statusLabelOf } from "@/lib/labels";

// 실행 이력 빈 상태 (오케스트레이터 확정 카피, terminology-ssot §6-8 해소).
// 정적 JSX 라 렌더마다 재생성하지 않도록 모듈 스코프로 hoist (rendering-hoist-jsx).
const EMPTY_HISTORY = (
  <div className="text-sm text-muted-foreground">
    <p className="font-medium text-foreground">최적화 실행 이력이 없습니다.</p>
    <p>완료된 백테스트를 대상으로 첫 최적화를 제출하면 이곳에 실행 이력이 쌓입니다.</p>
  </div>
);

export function OptimizerRunList({
  limit = 20,
  backtestId,
}: {
  limit?: number;
  backtestId?: string;
}) {
  const { data, isLoading, error } = useOptimizationRuns({
    limit,
    offset: 0,
    backtest_id: backtestId,
  });

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">로드 중…</p>;
  }
  // Sprint 62 T-1 (BL-350/354): error 시 raw error.message (Zod issues JSON) 노출 차단.
  // user-friendly message 만 표시 — 잠재 고객/일반인 신뢰 손실 차단 (★★★ 공통 P0 발견).
  if (error) {
    return (
      <p role="alert" className="text-sm text-destructive">
        {OPTIMIZER_DOMAIN_LABEL.page} 목록을 불러오지 못했습니다. 잠시 후 새로고침 해주세요.
      </p>
    );
  }
  // Sprint 62 T-1 (BL-350/354): skipped_count > 0 + items 0 case = 데이터는 있지만 모두
  // schema 불일치로 표시 X. empty state 대신 graceful warn 노출 의무.
  if (data == null) {
    return EMPTY_HISTORY;
  }
  if (data.items.length === 0 && data.skipped_count === 0) {
    return EMPTY_HISTORY;
  }

  const {
    runId: hRunId,
    status: hStatus,
    objective: hObjective,
    bestObjective: hBest,
    createdAt: hCreated,
  } = OPTIMIZER_LIST_HEADER;

  return (
    <div className="space-y-2">
      {/* Sprint 62 T-1 (BL-350/354): skipped_count > 0 시 graceful warn. 일반인 신뢰 손실 회피. */}
      {data.skipped_count > 0 ? (
        <p
          role="status"
          data-testid="optimizer-skipped-warn"
          data-tone="warning"
          className="rounded border px-3 py-2 text-xs"
        >{`이전 데이터 형식 불일치로 ${data.skipped_count}개 항목이 표시되지 않습니다.`}</p>
      ) : null}
      <div className="overflow-x-auto">
      <table className="min-w-[640px] w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs text-muted-foreground">
            <th className="p-2 font-medium">{hRunId}</th>
            <th className="p-2 font-medium">{hStatus}</th>
            <th className="p-2 font-medium">{hObjective}</th>
            <th className="p-2 font-medium">{hBest}</th>
            <th className="p-2 font-medium">{hCreated}</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((r) => {
            // Sprint 55 — discriminated union by result.kind. Best 표시 = grid_search 면 cell objective,
            // bayesian/genetic 이면 best_iteration objective_value.
            let bestObjective: number | null = null;
            if (r.result?.kind === "grid_search" && r.result.best_cell_index !== null) {
              bestObjective =
                r.result.cells[r.result.best_cell_index]?.objective_value ?? null;
            } else if (
              r.result?.kind === "bayesian" &&
              r.result.best_iteration_idx !== null
            ) {
              bestObjective = r.result.best_objective_value;
            } else if (
              r.result?.kind === "genetic" &&
              r.result.best_iteration_idx !== null
            ) {
              bestObjective = r.result.best_objective_value;
            }
            // 라벨·톤은 용어 SSOT 에서만 온다 (원시 enum 렌더 금지 — no-raw-enum-labels 가드).
            const { label: statusLabel, tone: statusTone } = statusLabelOf(
              OPTIMIZATION_STATUS_LABEL,
              r.status,
            );
            return (
              <tr key={r.id} className="border-b hover:bg-muted/30">
                <td className="p-2 font-mono text-xs">
                  <Link
                    href={`/optimizer/${r.id}`}
                    className="text-primary hover:underline"
                  >
                    {r.id.slice(0, 8)}
                  </Link>
                </td>
                <td className="p-2">
                  <span className={CHIP_TONE_CLASS[statusTone]}>{statusLabel}</span>
                </td>
                <td className="p-2 text-xs">
                  {OBJECTIVE_METRIC_LABEL[r.param_space.objective_metric]} (
                  {OBJECTIVE_DIRECTION_LABEL[r.param_space.direction]})
                </td>
                <td className="p-2 font-mono text-xs tabular-nums">
                  {bestObjective === null ? EMPTY_CELL : bestObjective.toFixed(2)}
                </td>
                <td className="p-2 font-mono text-xs text-muted-foreground">
                  {new Date(r.created_at).toLocaleString()}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    </div>
  );
}
