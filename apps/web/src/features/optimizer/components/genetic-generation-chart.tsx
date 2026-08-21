// Sprint 56 BL-233 — 유전 알고리즘 세대 차트 (best_so_far 라인 + 세대 경계 가이드).
// W3-C 재스킨: shadcn 어휘(text-muted-foreground·border-border·--primary)를 형제가 쓰는 C 어휘
// (.card-sub/.mono/--copper/--ink·--line 계열 토큰)로 교체 (베이지안 반복 차트 1:1 미러).
// 레이아웃·데이터 로직 무변경. 최적 반복 점은 색+반지름 확대(r=4)로 이중 표시(§9).
"use client";

import { useMemo } from "react";

import { OBJECTIVE_DIRECTION_LABEL, OBJECTIVE_METRIC_LABEL } from "@/features/optimizer/labels";
import { formatObjectiveValue } from "@/features/optimizer/format";
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
      <p className="chart-note" style={{ paddingLeft: 0 }}>
        모든 반복이 축퇴(거래 0건 또는 지표 산출 불가)라 누적 최고값 곡선을 그릴 수 없습니다.
        파라미터 범위나 전략을 다시 확인해 주세요.
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
  const yScale = (y: number) => H - PAD - ((y - yMin) / yRange) * (H - 2 * PAD);

  const linePath = data
    .map((d, i) => `${i === 0 ? "M" : "L"} ${xScale(d.idx)} ${yScale(d.bestSoFar)}`)
    .join(" ");

  return (
    <div className="space-y-2">
      <div className="card-sub flex flex-wrap items-baseline justify-between gap-2">
        <span>
          반복별 누적 최고값 ({OBJECTIVE_METRIC_LABEL[result.objective_metric]},{" "}
          {OBJECTIVE_DIRECTION_LABEL[result.direction]})
        </span>
        <span>
          개체군{" "}
          <strong className="mono" style={{ color: "var(--ink)" }}>
            {result.population_size}
          </strong>
          {" · "}세대{" "}
          <strong className="mono" style={{ color: "var(--ink)" }}>
            {result.n_generations}
          </strong>
          {" · "}전체{" "}
          <strong className="mono" style={{ color: "var(--ink)" }}>
            {result.total_iterations}
          </strong>
          {result.degenerate_count > 0 && (
            <>
              {" · "}축퇴{" "}
              <span className="mono" style={{ color: "var(--warn)" }}>
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
          style={{
            border: "1px solid var(--line)",
            borderRadius: "var(--r)",
            background: "var(--bg)",
          }}
          role="img"
          aria-label={`유전 알고리즘 세대 곡선. 반복 ${result.total_iterations}회, 세대 ${result.n_generations + 1}개.`}
        >
          {/* axes */}
          <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="var(--line)" />
          <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="var(--line)" />
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
                  stroke="var(--line-2)"
                  strokeDasharray="3 3"
                />
                <text
                  x={xScale(b.idx - 0.5) + 3}
                  y={PAD + 10}
                  fontSize={9}
                  fill="var(--ink-3)"
                  className="mono"
                >
                  G{b.gen}
                </text>
              </g>
            ))}
          {/* line */}
          <path d={linePath} fill="none" stroke="var(--copper)" strokeWidth={2} />
          {/* points — 최적 반복은 코퍼 채움 + 반지름 확대(r=4), 나머지는 무채색 점 (§9). */}
          {data.map((d) => {
            const isBest = result.best_iteration_idx === d.idx;
            return (
              <circle
                key={d.idx}
                cx={xScale(d.idx)}
                cy={yScale(d.bestSoFar)}
                r={isBest ? 4 : 3}
                fill={isBest ? "var(--copper)" : "var(--ink-3)"}
                opacity={isBest ? 1 : 0.6}
              />
            );
          })}
          {/* y axis labels — 목표값 단위 SSOT (ratio 지표는 %, sharpe 는 소수 3자리 유지). */}
          <text x={4} y={PAD + 4} fontSize={10} fill="var(--ink-3)" className="mono">
            {formatObjectiveValue(result.objective_metric, yMax, {
              percentDigits: 1,
              plainDigits: 3,
            })}
          </text>
          <text x={4} y={H - PAD + 4} fontSize={10} fill="var(--ink-3)" className="mono">
            {formatObjectiveValue(result.objective_metric, yMin, {
              percentDigits: 1,
              plainDigits: 3,
            })}
          </text>
          {/* x axis labels */}
          <text x={PAD} y={H - 8} fontSize={10} fill="var(--ink-3)" className="mono">
            0
          </text>
          <text
            x={W - PAD}
            y={H - 8}
            fontSize={10}
            fill="var(--ink-3)"
            textAnchor="end"
            className="mono"
          >
            {xMax}
          </text>
        </svg>
      </div>
    </div>
  );
}
