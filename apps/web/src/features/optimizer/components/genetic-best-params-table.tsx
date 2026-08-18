// 유전 알고리즘 최적화의 최적 파라미터 테이블 (세대 표시 포함) — C 디자인 언어 이식 (W3-C).
"use client";

import { AlertTriangleIcon, StarIcon } from "lucide-react";

import { OBJECTIVE_METRIC_LABEL } from "@/features/optimizer/labels";
import { formatObjectiveValue } from "@/features/optimizer/format";
import type { GeneticSearchResult } from "@/features/optimizer/schemas";
import { EMPTY_CELL } from "@/lib/labels";

interface Props {
  result: GeneticSearchResult;
}

export function GeneticBestParamsTable({ result }: Props) {
  const hasBest = result.best_iteration_idx !== null && result.best_params !== null;
  const degenerateRatio =
    result.total_iterations > 0
      ? (result.degenerate_count / result.total_iterations) * 100
      : 0;

  const bestGeneration =
    result.best_iteration_idx !== null
      ? result.iterations.find((it) => it.idx === result.best_iteration_idx)?.generation
      : undefined;

  return (
    <div className="space-y-2">
      <div className="card-head" style={{ border: "none", padding: 0 }}>
        <h3 className="card-title">최적 파라미터</h3>
        {result.degenerate_count > 0 ? (
          <span
            className="chip warn"
            aria-label={`${result.total_iterations}회 중 ${result.degenerate_count}회가 축퇴 반복입니다.`}
          >
            <AlertTriangleIcon aria-hidden="true" />
            축퇴 {result.degenerate_count} / {result.total_iterations} (
            {degenerateRatio.toFixed(0)}%)
          </span>
        ) : null}
      </div>

      {!hasBest ? (
        <p className="chart-note" style={{ paddingLeft: 0 }}>
          모든 반복이 축퇴(거래 0건 또는 지표 산출 불가)라 최적 파라미터를 선정하지 못했습니다.
          파라미터 범위나 전략을 다시 확인해 주세요.
        </p>
      ) : (
        <>
          <p className="chart-note" style={{ paddingLeft: 0, paddingTop: 0 }}>
            <StarIcon aria-hidden="true" />
            <span>
              최적 반복 #<span className="mono">{result.best_iteration_idx}</span>
              {bestGeneration !== undefined ? (
                <>
                  {" "}
                  · 세대 <span className="mono">{bestGeneration}</span>
                </>
              ) : null}{" "}
              · {OBJECTIVE_METRIC_LABEL[result.objective_metric]}{" "}
              {/* 목표값 단위 SSOT — ratio 지표는 %, sharpe 는 소수 4자리 유지. */}
              <span className="mono">
                {result.best_objective_value === null
                  ? EMPTY_CELL
                  : formatObjectiveValue(result.objective_metric, result.best_objective_value, {
                      plainDigits: 4,
                    })}
              </span>
            </span>
          </p>
          <div className="table-wrap">
            <table className="trades" aria-label="최적 파라미터">
              <thead>
                <tr>
                  <th scope="col">파라미터</th>
                  <th scope="col" className="num">
                    값
                  </th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(result.best_params ?? {}).map(([name, value]) => (
                  <tr key={name}>
                    <td className="mono-l">{name}</td>
                    <td className="num">{value.toFixed(6)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
