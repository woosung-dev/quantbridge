// Sprint 55 — 베이지안 반복 차트 (acquisition_history 라인 + random→acquisition 경계 세로 가이드).
"use client";

import { useMemo } from "react";

import {
  OBJECTIVE_DIRECTION_LABEL,
  OBJECTIVE_METRIC_LABEL,
} from "@/features/optimizer/labels";
import type { BayesianSearchResult } from "@/features/optimizer/schemas";

interface Props {
  result: BayesianSearchResult;
}

/**
 * Inline SVG line chart — best_so_far per iteration. recharts dependency 회피
 * (Sprint 55 plan §4 = recharts 도입 시 cross-page consistency 검토 의무).
 *
 * X 축 = iteration idx (0..N-1).
 * Y 축 = best_so_far (direction 적용 cumulative best, monotonic non-decreasing for maximize).
 * vertical guide = idx = bayesian_n_initial_random — random → acquisition 경계.
 * degenerate iteration 의 best_so_far == null → 가능한 경우 skip.
 */
export function BayesianIterationChart({ result }: Props) {
  const data = useMemo(() => {
    return result.iterations
      .map((it) => ({
        idx: it.idx,
        bestSoFar: it.best_so_far,
        isDegenerate: it.is_degenerate,
        phase: it.phase,
      }))
      .filter((d) => d.bestSoFar !== null) as Array<{
      idx: number;
      bestSoFar: number;
      isDegenerate: boolean;
      phase: "random" | "acquisition";
    }>;
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
  const yScale = (y: number) =>
    H - PAD - ((y - yMin) / yRange) * (H - 2 * PAD);

  const linePath = data
    .map((d, i) => `${i === 0 ? "M" : "L"} ${xScale(d.idx)} ${yScale(d.bestSoFar)}`)
    .join(" ");

  const initialRandomBoundary = result.bayesian_n_initial_random;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-baseline justify-between gap-2 text-xs text-muted-foreground">
        <span>
          반복별 누적 최고값 ({OBJECTIVE_METRIC_LABEL[result.objective_metric]},{" "}
          {OBJECTIVE_DIRECTION_LABEL[result.direction]})
        </span>
        <span>
          초기 랜덤 탐색 <strong className="font-mono tabular-nums text-foreground">{initialRandomBoundary}</strong>
          {" · "}전체 <strong className="font-mono tabular-nums text-foreground">{result.total_iterations}</strong>
          {result.degenerate_count > 0 && (
            <>
              {" · "}축퇴{" "}
              <span className="font-mono tabular-nums text-warning">
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
          aria-label={`베이지안 반복 곡선. 반복 ${result.total_iterations}회.`}
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
          {/* random/acquisition boundary */}
          {initialRandomBoundary > 0 && initialRandomBoundary <= xMax && (
            <>
              <line
                x1={xScale(initialRandomBoundary - 0.5)}
                y1={PAD}
                x2={xScale(initialRandomBoundary - 0.5)}
                y2={H - PAD}
                stroke="currentColor"
                strokeOpacity={0.35}
                strokeDasharray="3 3"
              />
              <text
                x={xScale(initialRandomBoundary - 0.5) + 4}
                y={PAD + 12}
                fontSize={10}
                fill="currentColor"
                opacity={0.6}
              >
                획득 함수 →
              </text>
            </>
          )}
          {/* line */}
          <path
            d={linePath}
            fill="none"
            stroke="var(--primary)"
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
                  ? "var(--primary)"
                  : d.phase === "random"
                    ? "currentColor"
                    : "var(--primary)"
              }
              opacity={result.best_iteration_idx === d.idx ? 1 : 0.7}
            />
          ))}
          {/* y axis labels */}
          <text x={4} y={PAD + 4} fontSize={10} fill="currentColor" opacity={0.6} className="font-mono">
            {yMax.toFixed(3)}
          </text>
          <text
            x={4}
            y={H - PAD + 4}
            fontSize={10}
            fill="currentColor"
            opacity={0.6}
            className="font-mono"
          >
            {yMin.toFixed(3)}
          </text>
          {/* x axis labels */}
          <text x={PAD} y={H - 8} fontSize={10} fill="currentColor" opacity={0.6} className="font-mono">
            0
          </text>
          <text
            x={W - PAD}
            y={H - 8}
            fontSize={10}
            fill="currentColor"
            opacity={0.6}
            textAnchor="end"
            className="font-mono"
          >
            {xMax}
          </text>
        </svg>
      </div>
    </div>
  );
}
