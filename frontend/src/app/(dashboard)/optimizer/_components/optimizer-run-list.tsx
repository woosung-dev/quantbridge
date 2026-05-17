// Sprint 54 — Optimizer 실행 목록 (status badge + objective + best 요약).
"use client";

import Link from "next/link";

import { useOptimizationRuns } from "@/features/optimizer/hooks";
import type { OptimizationRunResponse } from "@/features/optimizer/schemas";
import { cn } from "@/lib/utils";

const STATUS_BADGE: Record<OptimizationRunResponse["status"], string> = {
  queued: "bg-muted text-muted-foreground",
  running: "bg-blue-500/15 text-blue-700 dark:text-blue-300",
  completed: "bg-success/15 text-success",
  failed: "bg-destructive/15 text-destructive",
};

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
        Optimizer 목록을 불러오지 못했습니다. 잠시 후 새로고침 해주세요.
      </p>
    );
  }
  // Sprint 62 T-1 (BL-350/354): skipped_count > 0 + items 0 case = 데이터는 있지만 모두
  // schema 불일치로 표시 X. empty state 대신 graceful warn 노출 의무.
  if (data == null) {
    return (
      <p className="text-sm text-muted-foreground">
        Optimizer 실행 이력 없음. 새 Grid Search 를 제출하세요.
      </p>
    );
  }
  if (data.items.length === 0 && data.skipped_count === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Optimizer 실행 이력 없음. 새 Grid Search 를 제출하세요.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {/* Sprint 62 T-1 (BL-350/354): skipped_count > 0 시 graceful warn. 일반인 신뢰 손실 회피. */}
      {data.skipped_count > 0 ? (
        <p
          role="status"
          data-testid="optimizer-skipped-warn"
          className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900"
        >{`이전 데이터 형식 불일치로 ${data.skipped_count}개 항목이 표시되지 않습니다.`}</p>
      ) : null}
      <div className="overflow-x-auto">
      <table className="min-w-[640px] w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs text-muted-foreground">
            <th className="p-2 font-medium">ID</th>
            <th className="p-2 font-medium">Status</th>
            <th className="p-2 font-medium">Objective</th>
            <th className="p-2 font-medium">Best</th>
            <th className="p-2 font-medium">Created</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((r) => {
            // Sprint 55 — discriminated union by result.kind. Best 표시 = grid_search 면 cell objective,
            // bayesian 이면 best_iteration objective_value.
            let bestObjective: number | null = null;
            if (r.result?.kind === "grid_search" && r.result.best_cell_index !== null) {
              bestObjective =
                r.result.cells[r.result.best_cell_index]?.objective_value ?? null;
            } else if (
              r.result?.kind === "bayesian" &&
              r.result.best_iteration_idx !== null
            ) {
              bestObjective = r.result.best_objective_value;
            }
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
                  <span
                    className={cn(
                      "rounded px-2 py-0.5 text-xs font-medium",
                      STATUS_BADGE[r.status],
                    )}
                  >
                    {r.status}
                  </span>
                </td>
                <td className="p-2 text-xs">
                  {r.param_space.objective_metric} ({r.param_space.direction})
                </td>
                <td className="p-2 text-xs">
                  {bestObjective === null ? "—" : bestObjective.toFixed(2)}
                </td>
                <td className="p-2 text-xs text-muted-foreground">
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
