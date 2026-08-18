// Sprint 55 — 베이지안 반복 차트 (acquisition_history 라인 + random→acquisition 경계 세로 가이드).
// W3-C 재스킨: shadcn 어휘(text-muted-foreground·border-border·--primary)를 형제(grid-search-heatmap
// 등)가 쓰는 C 어휘(.card-sub/.mono/--copper/--ink·--line 계열 토큰)로 교체. 레이아웃·데이터 로직 무변경.
// random/acquisition 페이즈는 색이 아니라 모양(중공 vs 채움 원)으로 갈라 「색만으로 정보 전달 금지」
// (DESIGN.md §9)를 충족하고, 범례를 함께 인쇄한다.
"use client";

import { useMemo } from "react";

import {
  OBJECTIVE_DIRECTION_LABEL,
  OBJECTIVE_METRIC_LABEL,
} from "@/features/optimizer/labels";
import { formatObjectiveValue } from "@/features/optimizer/format";
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
      <div className="card-sub flex flex-wrap items-baseline justify-between gap-2">
        <span>
          반복별 누적 최고값 ({OBJECTIVE_METRIC_LABEL[result.objective_metric]},{" "}
          {OBJECTIVE_DIRECTION_LABEL[result.direction]})
        </span>
        <span>
          초기 랜덤 탐색{" "}
          <strong className="mono" style={{ color: "var(--ink)" }}>
            {initialRandomBoundary}
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
      {/* 범례 — 페이즈는 색이 아니라 모양(중공/채움)으로 구분한다 (DESIGN.md §9). */}
      <p className="card-sub" style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 0 }}>
        <svg width={12} height={12} viewBox="0 0 12 12" aria-hidden="true">
          {/* 범례는 카드(--card) 위라 중공 fill 도 --card — 차트 내부 점(--bg 배경)과 배경이 다르다 */}
          <circle cx="6" cy="6" r="3.5" fill="var(--card)" stroke="var(--copper)" strokeWidth={1.5} />
        </svg>
        초기 랜덤 (중공)
        <svg width={12} height={12} viewBox="0 0 12 12" aria-hidden="true" style={{ marginLeft: 8 }}>
          <circle cx="6" cy="6" r="3.5" fill="var(--copper)" />
        </svg>
        획득 함수 (채움)
      </p>
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
          aria-label={`베이지안 반복 곡선. 반복 ${result.total_iterations}회.`}
        >
          {/* axes */}
          <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="var(--line)" />
          <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="var(--line)" />
          {/* random/acquisition boundary */}
          {initialRandomBoundary > 0 && initialRandomBoundary <= xMax && (
            <>
              <line
                x1={xScale(initialRandomBoundary - 0.5)}
                y1={PAD}
                x2={xScale(initialRandomBoundary - 0.5)}
                y2={H - PAD}
                stroke="var(--line-2)"
                strokeDasharray="3 3"
              />
              <text
                x={xScale(initialRandomBoundary - 0.5) + 4}
                y={PAD + 12}
                fontSize={10}
                fill="var(--ink-3)"
              >
                획득 함수 →
              </text>
            </>
          )}
          {/* line */}
          <path
            d={linePath}
            fill="none"
            stroke="var(--copper)"
            strokeWidth={2}
          />
          {/* points — random 페이즈는 중공 원, acquisition 은 채움 원 (모양으로 구분, §9).
              최적 반복은 채움 + 반지름 확대(r=4)로 색·크기 이중 표시. */}
          {data.map((d) => {
            const isBest = result.best_iteration_idx === d.idx;
            const isHollow = !isBest && d.phase === "random";
            return (
              <circle
                key={d.idx}
                cx={xScale(d.idx)}
                cy={yScale(d.bestSoFar)}
                r={isBest ? 4 : 3}
                fill={isHollow ? "var(--bg)" : "var(--copper)"}
                stroke={isHollow ? "var(--copper)" : undefined}
                strokeWidth={isHollow ? 1.5 : undefined}
                opacity={isBest ? 1 : 0.7}
              />
            );
          })}
          {/* y axis labels — 목표값 단위 SSOT (ratio 지표는 %, sharpe 는 소수 3자리 유지). */}
          <text x={4} y={PAD + 4} fontSize={10} fill="var(--ink-3)" className="mono">
            {formatObjectiveValue(result.objective_metric, yMax, { percentDigits: 1, plainDigits: 3 })}
          </text>
          <text x={4} y={H - PAD + 4} fontSize={10} fill="var(--ink-3)" className="mono">
            {formatObjectiveValue(result.objective_metric, yMin, { percentDigits: 1, plainDigits: 3 })}
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
