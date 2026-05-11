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
  if (error) {
    return (
      <p role="alert" className="text-sm text-destructive">
        목록 로드 실패: {error.message}
      </p>
    );
  }
  if (data == null || data.items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Optimizer 실행 이력 없음. 새 Grid Search 를 제출하세요.
      </p>
    );
  }

  return (
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
            const best =
              r.result != null && r.result.best_cell_index !== null
                ? r.result.cells[r.result.best_cell_index]
                : null;
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
                  {best == null
                    ? "—"
                    : `${best.objective_value?.toFixed(2) ?? "—"}`}
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
  );
}
