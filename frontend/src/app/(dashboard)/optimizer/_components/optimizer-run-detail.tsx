// Sprint 54 — Optimizer 실행 detail (param_space + status + heatmap + best cell + cells table).
"use client";

import { useOptimizationRun } from "@/features/optimizer/hooks";

import { GridSearchPairSelector } from "./grid-search-pair-selector";

export function OptimizerRunDetail({ runId }: { runId: string }) {
  const { data, isLoading, error } = useOptimizationRun(runId);

  if (isLoading) return <p className="text-sm text-muted-foreground">로드 중…</p>;
  if (error) {
    return (
      <p role="alert" className="text-sm text-destructive">
        상세 로드 실패: {error.message}
      </p>
    );
  }
  if (data == null) return null;

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="text-lg font-semibold">Optimizer Run {data.id.slice(0, 8)}</h2>
        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <span>Status: <strong className="text-foreground">{data.status}</strong></span>
          <span>·</span>
          <span>Kind: {data.kind}</span>
          <span>·</span>
          <span>
            Objective: {data.param_space.objective_metric} ({data.param_space.direction})
          </span>
        </div>
        {data.error_message && (
          <p role="alert" className="rounded border border-destructive bg-destructive/10 p-2 text-sm text-destructive">
            {data.error_message}
          </p>
        )}
      </header>

      <section>
        <h3 className="mb-2 text-sm font-medium">Parameter space</h3>
        <ul className="space-y-1 rounded border border-border bg-muted/20 p-3 text-xs">
          {Object.entries(data.param_space.parameters).map(([name, field]) => (
            <li key={name}>
              <strong className="font-mono">{name}</strong>:{" "}
              {field.kind === "integer" || field.kind === "decimal"
                ? `${field.kind} [${field.min} .. ${field.max} step ${field.step}]`
                : `categorical [${field.values.join(", ")}]`}
            </li>
          ))}
        </ul>
      </section>

      {data.status === "completed" && data.result && (
        <section className="space-y-3">
          <h3 className="text-sm font-medium">Result heatmap</h3>
          <GridSearchPairSelector result={data.result} />

          {data.result.best_cell_index !== null && (
            <div className="rounded border border-primary/30 bg-primary/5 p-3 text-sm">
              <strong>★ Best cell</strong>{" "}
              <span className="font-mono text-xs">
                {Object.entries(
                  data.result.cells[data.result.best_cell_index]?.param_values ?? {},
                )
                  .map(([k, v]) => `${k}=${v}`)
                  .join(", ")}
              </span>
              <span className="ml-3 text-muted-foreground">
                ({data.result.objective_metric} ={" "}
                {data.result.cells[data.result.best_cell_index]?.objective_value?.toFixed(
                  4,
                ) ?? "—"}
                )
              </span>
            </div>
          )}

          <details className="text-xs">
            <summary className="cursor-pointer text-muted-foreground">
              전체 cells ({data.result.cells.length})
            </summary>
            <div className="mt-2 overflow-x-auto">
              <table className="min-w-[600px] text-xs">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="p-1">params</th>
                    <th className="p-1">objective</th>
                    <th className="p-1">sharpe</th>
                    <th className="p-1">return</th>
                    <th className="p-1">MDD</th>
                    <th className="p-1">trades</th>
                  </tr>
                </thead>
                <tbody>
                  {data.result.cells.map((c, i) => (
                    <tr key={i} className="border-b">
                      <td className="p-1 font-mono">
                        {Object.entries(c.param_values)
                          .map(([k, v]) => `${k}=${v}`)
                          .join(", ")}
                      </td>
                      <td className="p-1">
                        {c.objective_value === null ? "—" : c.objective_value.toFixed(4)}
                      </td>
                      <td className="p-1">{c.sharpe ?? "—"}</td>
                      <td className="p-1">{c.total_return}</td>
                      <td className="p-1">{c.max_drawdown}</td>
                      <td className="p-1">{c.num_trades}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </section>
      )}
    </div>
  );
}
