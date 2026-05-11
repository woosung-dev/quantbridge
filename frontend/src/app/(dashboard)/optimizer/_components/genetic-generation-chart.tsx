// Sprint 56 BL-233 — Genetic generation chart (best_so_far line + generation boundary guides).
"use client";

import { useMemo } from "react";

import type { GeneticSearchResult } from "@/features/optimizer/schemas";

interface Props {
  result: GeneticSearchResult;
}

/**
 * Inline SVG line chart — best_so_far per iteration (Bayesian iteration chart 1:1 mirror).
 * recharts dependency 회피 (Sprint 56 plan = N-dim viz Sprint 57+ BL-235 이연).
 *
 * X 축 = iteration idx (0..total-1, flat across generations).
 * Y 축 = best_so_far (direction 적용 cumulative, maximize 시 단조 비감소).
 * vertical guides = generation 경계 (initial → gen1 → gen2 → ...).
 */
export function GeneticGenerationChart({ result }: Props) {
  const data = useMemo(() => {
    return result.iterations
      .map((it) => ({
        idx: it.idx,
        bestSoFar: it.best_so_far,
        isDegenerate: it.is_degenerate,
        generation: it.generation,
      }))
      .filter((d) => d.bestSoFar !== null) as Array<{
      idx: number;
      bestSoFar: number;
      isDegenerate: boolean;
      generation: number;
    }>;
  }, [result.iterations]);

  // generation 별 첫 iteration idx 추출 (vertical guide 위치).
  const generationBoundaries = useMemo(() => {
    const seen = new Set<number>();
    const boundaries: Array<{ gen: number; idx: number }> = [];
    for (const it of result.iterations) {
      if (!seen.has(it.generation)) {
        seen.add(it.generation);
        boundaries.push({ gen: it.generation, idx: it.idx });
      }
    }
    return boundaries;
  }, [result.iterations]);

  if (data.length === 0) {
    return (
      <p className="rounded border border-border bg-muted/30 p-3 text-xs text-muted-foreground">
        모든 iteration 이 degenerate (num_trades=0 또는 sharpe=null) — chart 표시 불가.
        파라미터 범위 또는 strategy 검토 권장.
      </p>
    );
  }

  const W = 640;
  const H = 200;
  const PAD = 28;

  const xMax = result.iterations.length - 1;
  const yMin = Math.min(...data.map((d) => d.bestSoFar));
  const yMax = Math.max(...data.map((d) => d.bestSoFar));
  const yRange = yMax - yMin || 1;

  const xScale = (x: number) => PAD + (x / Math.max(xMax, 1)) * (W - 2 * PAD);
  const yScale = (y: number) =>
    H - PAD - ((y - yMin) / yRange) * (H - 2 * PAD);

  const linePath = data
    .map((d, i) => `${i === 0 ? "M" : "L"} ${xScale(d.idx)} ${yScale(d.bestSoFar)}`)
    .join(" ");

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-baseline justify-between gap-2 text-xs text-muted-foreground">
        <span>
          best_so_far per iteration ({result.objective_metric}, {result.direction})
        </span>
        <span>
          population: <strong className="text-foreground">{result.population_size}</strong>
          {" · "}generations:{" "}
          <strong className="text-foreground">{result.n_generations}</strong>
          {" · "}total:{" "}
          <strong className="text-foreground">{result.total_iterations}</strong>
          {result.degenerate_count > 0 && (
            <>
              {" · "}degenerate:{" "}
              <span className="text-amber-600 dark:text-amber-400">
                {result.degenerate_count} / {result.total_iterations}
              </span>
            </>
          )}
        </span>
      </div>
      <div className="overflow-x-auto">
        <svg
          width={W}
          height={H}
          viewBox={`0 0 ${W} ${H}`}
          className="rounded border border-border bg-background"
          role="img"
          aria-label={`Genetic generation chart — ${result.total_iterations} iterations over ${result.n_generations + 1} generations`}
        >
          {/* axes */}
          <line
            x1={PAD}
            y1={H - PAD}
            x2={W - PAD}
            y2={H - PAD}
            stroke="currentColor"
            strokeOpacity={0.2}
          />
          <line
            x1={PAD}
            y1={PAD}
            x2={PAD}
            y2={H - PAD}
            stroke="currentColor"
            strokeOpacity={0.2}
          />
          {/* generation boundary guides (skip gen=0 since it's the start). */}
          {generationBoundaries
            .filter((b) => b.gen > 0)
            .map((b) => (
              <g key={`gen-${b.gen}`}>
                <line
                  x1={xScale(b.idx - 0.5)}
                  y1={PAD}
                  x2={xScale(b.idx - 0.5)}
                  y2={H - PAD}
                  stroke="currentColor"
                  strokeOpacity={0.25}
                  strokeDasharray="3 3"
                />
                <text
                  x={xScale(b.idx - 0.5) + 3}
                  y={PAD + 10}
                  fontSize={9}
                  fill="currentColor"
                  opacity={0.55}
                >
                  G{b.gen}
                </text>
              </g>
            ))}
          {/* line */}
          <path
            d={linePath}
            fill="none"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
          />
          {/* points */}
          {data.map((d) => (
            <circle
              key={d.idx}
              cx={xScale(d.idx)}
              cy={yScale(d.bestSoFar)}
              r={3}
              fill={
                result.best_iteration_idx === d.idx
                  ? "hsl(var(--primary))"
                  : "currentColor"
              }
              opacity={result.best_iteration_idx === d.idx ? 1 : 0.6}
            />
          ))}
          {/* y axis labels */}
          <text x={4} y={PAD + 4} fontSize={10} fill="currentColor" opacity={0.6}>
            {yMax.toFixed(3)}
          </text>
          <text
            x={4}
            y={H - PAD + 4}
            fontSize={10}
            fill="currentColor"
            opacity={0.6}
          >
            {yMin.toFixed(3)}
          </text>
          {/* x axis labels */}
          <text x={PAD} y={H - 8} fontSize={10} fill="currentColor" opacity={0.6}>
            0
          </text>
          <text
            x={W - PAD}
            y={H - 8}
            fontSize={10}
            fill="currentColor"
            opacity={0.6}
            textAnchor="end"
          >
            {xMax}
          </text>
        </svg>
      </div>
    </div>
  );
}
