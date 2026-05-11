// Sprint 56 BL-233 — Genetic best params table (Bayesian table 1:1 mirror + generation 표시).
"use client";

import type { GeneticSearchResult } from "@/features/optimizer/schemas";

interface Props {
  result: GeneticSearchResult;
}

export function GeneticBestParamsTable({ result }: Props) {
  const hasBest =
    result.best_iteration_idx !== null && result.best_params !== null;
  const degenerateRatio =
    result.total_iterations > 0
      ? (result.degenerate_count / result.total_iterations) * 100
      : 0;

  const bestGeneration =
    result.best_iteration_idx !== null
      ? result.iterations.find((it) => it.idx === result.best_iteration_idx)
          ?.generation
      : undefined;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-baseline gap-2 text-sm">
        <h4 className="font-medium">Best parameters</h4>
        {result.degenerate_count > 0 && (
          <span
            className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200"
            aria-label={`${result.degenerate_count} of ${result.total_iterations} iterations were degenerate`}
          >
            ⚠ degenerate {result.degenerate_count} / {result.total_iterations} (
            {degenerateRatio.toFixed(0)}%)
          </span>
        )}
      </div>

      {!hasBest ? (
        <p className="rounded border border-border bg-muted/30 p-3 text-xs text-muted-foreground">
          모든 iteration 이 degenerate (num_trades=0 또는 sharpe=null) — best_params 미선정.
          파라미터 범위 또는 strategy 검토 권장.
        </p>
      ) : (
        <div className="rounded border border-primary/30 bg-primary/5 p-3">
          <div className="mb-2 flex flex-wrap items-baseline gap-2 text-sm">
            <strong>★ Best iteration</strong>
            <span className="text-xs text-muted-foreground">
              idx = <span className="font-mono">{result.best_iteration_idx}</span>
            </span>
            {bestGeneration !== undefined && (
              <span className="text-xs text-muted-foreground">
                · gen = <span className="font-mono">{bestGeneration}</span>
              </span>
            )}
            <span className="text-xs text-muted-foreground">·</span>
            <span className="text-xs">
              {result.objective_metric} ={" "}
              <span className="font-mono">
                {result.best_objective_value === null
                  ? "—"
                  : result.best_objective_value.toFixed(4)}
              </span>
            </span>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="p-1">var_name</th>
                <th className="p-1">value</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(result.best_params ?? {}).map(([name, value]) => (
                <tr key={name} className="border-b last:border-b-0">
                  <td className="p-1 font-mono">{name}</td>
                  <td className="p-1 font-mono">{value.toFixed(6)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
