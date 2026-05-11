// Sprint 55 — Optimizer 실행 detail (param_space + status + result kind 분기).
"use client";

import { useOptimizationRun } from "@/features/optimizer/hooks";

import { BayesianBestParamsTable } from "./bayesian-best-params-table";
import { BayesianIterationChart } from "./bayesian-iteration-chart";
import { GeneticBestParamsTable } from "./genetic-best-params-table";
import { GeneticGenerationChart } from "./genetic-generation-chart";
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
              {field.kind === "integer" || field.kind === "decimal" ? (
                `${field.kind} [${field.min} .. ${field.max} step ${field.step}]`
              ) : field.kind === "bayesian" ? (
                <>
                  bayesian [{field.min} .. {field.max}] prior={field.prior}
                  {field.log_scale ? " log_scale=true" : ""}
                </>
              ) : (
                `categorical [${field.values.join(", ")}]`
              )}
            </li>
          ))}
        </ul>
        {data.kind === "bayesian" && (
          <p className="mt-2 text-xs text-muted-foreground">
            acquisition: {data.param_space.bayesian_acquisition ?? "—"} · random
            warm-up: {data.param_space.bayesian_n_initial_random ?? "—"} · max
            evaluations: {data.param_space.max_evaluations}
          </p>
        )}
        {data.kind === "genetic" && (
          <p className="mt-2 text-xs text-muted-foreground">
            population_size: {data.param_space.population_size ?? "—"} ·
            n_generations: {data.param_space.n_generations ?? "—"} ·
            mutation_rate: {data.param_space.mutation_rate ?? "—"} ·
            crossover_rate: {data.param_space.crossover_rate ?? "—"} · max
            evaluations: {data.param_space.max_evaluations}
          </p>
        )}
      </section>

      {data.status === "completed" && data.result?.kind === "grid_search" && (
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

      {data.status === "completed" &&
        data.result?.kind === "bayesian" &&
        (() => {
          const bayesian = data.result;
          return (
            <section className="space-y-3">
              <h3 className="text-sm font-medium">Bayesian iteration history</h3>
              <BayesianIterationChart result={bayesian} />
              <BayesianBestParamsTable result={bayesian} />

              <details className="text-xs">
                <summary className="cursor-pointer text-muted-foreground">
                  전체 iterations ({bayesian.iterations.length})
                </summary>
                <div className="mt-2 overflow-x-auto">
                  <table className="min-w-[600px] text-xs">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="p-1">idx</th>
                        <th className="p-1">phase</th>
                        <th className="p-1">params</th>
                        <th className="p-1">objective</th>
                        <th className="p-1">best_so_far</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bayesian.iterations.map((it) => (
                        <tr
                          key={it.idx}
                          className={
                            it.idx === bayesian.best_iteration_idx
                              ? "border-b bg-primary/10"
                              : "border-b"
                          }
                        >
                          <td className="p-1 font-mono">{it.idx}</td>
                          <td className="p-1">{it.phase}</td>
                          <td className="p-1 font-mono">
                            {Object.entries(it.params)
                              .map(([k, v]) => `${k}=${Number(v).toFixed(4)}`)
                              .join(", ")}
                          </td>
                          <td className="p-1">
                            {it.objective_value === null
                              ? "—"
                              : it.objective_value.toFixed(4)}
                          </td>
                          <td className="p-1">
                            {it.best_so_far === null
                              ? "—"
                              : it.best_so_far.toFixed(4)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            </section>
          );
        })()}

      {data.status === "completed" &&
        data.result?.kind === "genetic" &&
        (() => {
          const genetic = data.result;
          return (
            <section className="space-y-3">
              <h3 className="text-sm font-medium">Genetic generation history</h3>
              <GeneticGenerationChart result={genetic} />
              <GeneticBestParamsTable result={genetic} />

              <details className="text-xs">
                <summary className="cursor-pointer text-muted-foreground">
                  전체 iterations ({genetic.iterations.length})
                </summary>
                <div className="mt-2 overflow-x-auto">
                  <table className="min-w-[600px] text-xs">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="p-1">idx</th>
                        <th className="p-1">gen</th>
                        <th className="p-1">params</th>
                        <th className="p-1">objective</th>
                        <th className="p-1">best_so_far</th>
                      </tr>
                    </thead>
                    <tbody>
                      {genetic.iterations.map((it) => (
                        <tr
                          key={it.idx}
                          className={
                            it.idx === genetic.best_iteration_idx
                              ? "border-b bg-primary/10"
                              : "border-b"
                          }
                        >
                          <td className="p-1 font-mono">{it.idx}</td>
                          <td className="p-1">{it.generation}</td>
                          <td className="p-1 font-mono">
                            {Object.entries(it.params)
                              .map(([k, v]) => `${k}=${Number(v).toFixed(4)}`)
                              .join(", ")}
                          </td>
                          <td className="p-1">
                            {it.objective_value === null
                              ? "—"
                              : it.objective_value.toFixed(4)}
                          </td>
                          <td className="p-1">
                            {it.best_so_far === null
                              ? "—"
                              : it.best_so_far.toFixed(4)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            </section>
          );
        })()}
    </div>
  );
}
