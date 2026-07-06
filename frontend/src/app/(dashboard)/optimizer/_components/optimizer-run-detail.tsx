// Sprint 55 — Optimizer 실행 detail (param_space + status + result kind 분기).
"use client";

import { Star } from "lucide-react";

import { extractBestParams } from "@/features/optimizer/best-params";
import { useOptimizationRun } from "@/features/optimizer/hooks";

import { BayesianBestParamsTable } from "./bayesian-best-params-table";
import { BayesianIterationChart } from "./bayesian-iteration-chart";
import { GeneticBestParamsTable } from "./genetic-best-params-table";
import { GeneticGenerationChart } from "./genetic-generation-chart";
import { GridSearchPairSelector } from "./grid-search-pair-selector";
import { OptimizerOosEvaluation } from "./optimizer-oos-evaluation";

export function OptimizerRunDetail({ runId }: { runId: string }) {
  const { data, isLoading, error } = useOptimizationRun(runId);

  if (isLoading) return <p className="text-sm text-muted-foreground">로드 중…</p>;
  if (error) {
    // raw error.message 를 그대로 노출하지 않음 (내부 용어 유출 차단) — 콘솔에만 기술 상세.
    console.error("optimization run detail load failed", error);
    return (
      <p role="alert" className="text-sm text-destructive">
        실행 상세를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.
      </p>
    );
  }
  if (data == null) return null;

  const bestParams =
    data.status === "completed" ? extractBestParams(data.result) : null;

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="text-lg font-semibold text-foreground">
          최적화 실행 {data.id.slice(0, 8)}
        </h2>
        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <span>
            상태 <strong className="text-foreground">{data.status}</strong>
          </span>
          <span>·</span>
          <span>방식 {data.kind}</span>
          <span>·</span>
          <span>
            목표 지표 {data.param_space.objective_metric} ({data.param_space.direction})
          </span>
        </div>
        {data.error_message && (
          <p
            role="alert"
            className="rounded-md border border-destructive/40 bg-destructive-subtle p-2 text-sm text-destructive"
          >
            {data.error_message}
          </p>
        )}
      </header>

      <section>
        <h3 className="mb-2 text-sm font-medium text-foreground">파라미터 공간</h3>
        <ul className="space-y-1 rounded-md border border-border bg-muted/20 p-3 text-xs">
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
            획득 함수 {data.param_space.bayesian_acquisition ?? "—"} · 초기 랜덤
            탐색 {data.param_space.bayesian_n_initial_random ?? "—"} · 최대 평가
            횟수 {data.param_space.max_evaluations}
          </p>
        )}
        {data.kind === "genetic" && (
          <p className="mt-2 text-xs text-muted-foreground">
            개체군 크기 {data.param_space.population_size ?? "—"} · 세대 수{" "}
            {data.param_space.n_generations ?? "—"} · 돌연변이율{" "}
            {data.param_space.mutation_rate ?? "—"} · 교차율{" "}
            {data.param_space.crossover_rate ?? "—"} · 최대 평가 횟수{" "}
            {data.param_space.max_evaluations}
          </p>
        )}
      </section>

      {data.status === "completed" && data.result?.kind === "grid_search" && (
        <section className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">결과 히트맵</h3>
          <GridSearchPairSelector result={data.result} />

          {data.result.best_cell_index !== null && (
            <div className="rounded-md border border-border bg-card p-3 text-sm shadow-card">
              <strong className="inline-flex items-center gap-1.5 text-primary">
                <Star className="h-4 w-4 fill-current" aria-hidden="true" />
                최적 셀
              </strong>{" "}
              <span className="font-mono text-xs tabular-nums">
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
              전체 셀 ({data.result.cells.length})
            </summary>
            <div className="mt-2 overflow-x-auto">
              <table className="min-w-[600px] text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="p-2 font-medium">파라미터</th>
                    <th className="p-2 text-right font-medium">목표값</th>
                    <th className="p-2 text-right font-medium">샤프</th>
                    <th className="p-2 text-right font-medium">수익률</th>
                    <th className="p-2 text-right font-medium">최대낙폭</th>
                    <th className="p-2 text-right font-medium">거래수</th>
                  </tr>
                </thead>
                <tbody>
                  {data.result.cells.map((c, i) => (
                    <tr key={i} className="border-b border-border/60">
                      <td className="p-2 font-mono">
                        {Object.entries(c.param_values)
                          .map(([k, v]) => `${k}=${v}`)
                          .join(", ")}
                      </td>
                      <td className="p-2 text-right font-mono tabular-nums">
                        {c.objective_value === null ? "—" : c.objective_value.toFixed(4)}
                      </td>
                      <td className="p-2 text-right font-mono tabular-nums">{c.sharpe ?? "—"}</td>
                      <td className="p-2 text-right font-mono tabular-nums">{c.total_return}</td>
                      <td className="p-2 text-right font-mono tabular-nums">{c.max_drawdown}</td>
                      <td className="p-2 text-right font-mono tabular-nums">{c.num_trades}</td>
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
              <h3 className="text-sm font-medium text-foreground">베이지안 반복 이력</h3>
              <BayesianIterationChart result={bayesian} />
              <BayesianBestParamsTable result={bayesian} />

              <details className="text-xs">
                <summary className="cursor-pointer text-muted-foreground">
                  전체 반복 ({bayesian.iterations.length})
                </summary>
                <div className="mt-2 overflow-x-auto">
                  <table className="min-w-[600px] text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                        <th className="p-2 text-right font-medium">#</th>
                        <th className="p-2 font-medium">단계</th>
                        <th className="p-2 font-medium">파라미터</th>
                        <th className="p-2 text-right font-medium">목표값</th>
                        <th className="p-2 text-right font-medium">누적 최고</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bayesian.iterations.map((it) => (
                        <tr
                          key={it.idx}
                          className={
                            it.idx === bayesian.best_iteration_idx
                              ? "border-b border-border/60 bg-primary/10"
                              : "border-b border-border/60"
                          }
                        >
                          <td className="p-2 text-right font-mono tabular-nums">{it.idx}</td>
                          <td className="p-2">{it.phase}</td>
                          <td className="p-2 font-mono">
                            {Object.entries(it.params)
                              .map(([k, v]) => `${k}=${Number(v).toFixed(4)}`)
                              .join(", ")}
                          </td>
                          <td className="p-2 text-right font-mono tabular-nums">
                            {it.objective_value === null
                              ? "—"
                              : it.objective_value.toFixed(4)}
                          </td>
                          <td className="p-2 text-right font-mono tabular-nums">
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
              <h3 className="text-sm font-medium text-foreground">
                유전 알고리즘 세대 이력
              </h3>
              <GeneticGenerationChart result={genetic} />
              <GeneticBestParamsTable result={genetic} />

              <details className="text-xs">
                <summary className="cursor-pointer text-muted-foreground">
                  전체 반복 ({genetic.iterations.length})
                </summary>
                <div className="mt-2 overflow-x-auto">
                  <table className="min-w-[600px] text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                        <th className="p-2 text-right font-medium">#</th>
                        <th className="p-2 font-medium">세대</th>
                        <th className="p-2 font-medium">파라미터</th>
                        <th className="p-2 text-right font-medium">목표값</th>
                        <th className="p-2 text-right font-medium">누적 최고</th>
                      </tr>
                    </thead>
                    <tbody>
                      {genetic.iterations.map((it) => (
                        <tr
                          key={it.idx}
                          className={
                            it.idx === genetic.best_iteration_idx
                              ? "border-b border-border/60 bg-primary/10"
                              : "border-b border-border/60"
                          }
                        >
                          <td className="p-2 text-right font-mono tabular-nums">{it.idx}</td>
                          <td className="p-2 font-mono tabular-nums">{it.generation}</td>
                          <td className="p-2 font-mono">
                            {Object.entries(it.params)
                              .map(([k, v]) => `${k}=${Number(v).toFixed(4)}`)
                              .join(", ")}
                          </td>
                          <td className="p-2 text-right font-mono tabular-nums">
                            {it.objective_value === null
                              ? "—"
                              : it.objective_value.toFixed(4)}
                          </td>
                          <td className="p-2 text-right font-mono tabular-nums">
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

      {/* WFO 는 best_params 를 쓰지 않고 fold별 재최적화하지만, "옵티마이저가 유효한
          winner 를 찾음" 휴리스틱 게이트로 best_params 존재를 사용 (전 cell degenerate 시
          OOS 검증 무의미). param_space/kind 는 run 의 필수 필드라 렌더 시 항상 존재. */}
      {bestParams && Object.keys(bestParams).length > 0 && (
        <OptimizerOosEvaluation
          backtestId={data.backtest_id}
          paramSpace={data.param_space}
          kind={data.kind}
        />
      )}
    </div>
  );
}
