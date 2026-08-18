// 그리드 탐색 2D 히트맵 — C 디자인 언어 이식 (W3-C, screen-10 04 히트맵).
// 리더보드와 같은 값을 히트맵 배치로 이중 렌더한다. 코퍼 단일 색조 농도 + 숫자 병기(색만으로 읽지
// 않게), 최적 칸은 색이 아니라 테두리, 축퇴 칸(거래 0건)은 무채색 점선 + title 규약.
"use client";

import { OBJECTIVE_METRIC_LABEL } from "@/features/optimizer/labels";
import type { GridSearchResult } from "@/features/optimizer/schemas";
import { OPTIMIZER_EMPTY_REASON } from "@/features/optimizer/labels";
import { EMPTY_CELL } from "@/lib/labels";
import { cn } from "@/lib/utils";

interface Props {
  result: GridSearchResult;
  /**
   * 2D heatmap 으로 그릴 변수쌍 (param_names.length === 2 일 때 자동, N>2 일 때는 pair-selector 선택).
   * pair[0]=행(세로축), pair[1]=열(가로축).
   */
  pair: readonly [string, string];
}

export function GridSearchHeatmap({ result, pair }: Props) {
  const [rowName, colName] = pair;
  const rowValues = result.param_values[rowName] ?? [];
  const colValues = result.param_values[colName] ?? [];

  // pair 가 전체 param_names 와 일치하는 경우 (2D) → 모든 cell row-major 매핑.
  // N>2 인 경우 → best cell 의 나머지 변수 값으로 fix, 해당 (행, 열) 평면 slice.
  const fixOthers: Record<string, number> = {};
  if (result.param_names.length > 2 && result.best_cell_index !== null) {
    const bestCell = result.cells[result.best_cell_index];
    if (bestCell) {
      for (const k of result.param_names) {
        if (k !== rowName && k !== colName) {
          fixOthers[k] = bestCell.param_values[k] ?? 0;
        }
      }
    }
  }

  // cell lookup: (행, 열) → cell (fix other vars equal).
  function findCell(rowV: number, colV: number): GridSearchResult["cells"][number] | null {
    for (const c of result.cells) {
      if (c.param_values[rowName] !== rowV || c.param_values[colName] !== colV) continue;
      let match = true;
      for (const k in fixOthers) {
        if (c.param_values[k] !== fixOthers[k]) {
          match = false;
          break;
        }
      }
      if (match) return c;
    }
    return null;
  }

  // objective_value 선형 정규화 → 코퍼 알파 [0.05, 0.35]. 최적일수록 진하다(direction 반영).
  const objNumbers = result.cells
    .map((c) => c.objective_value)
    .filter((v): v is number => v !== null);
  const objMin = objNumbers.length > 0 ? Math.min(...objNumbers) : 0;
  const objMax = objNumbers.length > 0 ? Math.max(...objNumbers) : 1;
  const objRange = objMax - objMin || 1;

  function bgFor(value: number | null): string | undefined {
    if (value === null) return undefined;
    const t =
      result.direction === "minimize"
        ? (objMax - value) / objRange
        : (value - objMin) / objRange;
    const alpha = 0.05 + Math.max(0, Math.min(1, t)) * 0.3;
    return `color-mix(in srgb, var(--copper) ${(alpha * 100).toFixed(1)}%, transparent)`;
  }

  const bestParamValues =
    result.best_cell_index !== null
      ? result.cells[result.best_cell_index]?.param_values
      : null;

  return (
    <div className="table-wrap">
      <table className="hm" aria-label={`그리드 히트맵 (${rowName} × ${colName})`}>
        <caption className="card-sub" style={{ textAlign: "left", padding: "4px 0 8px" }}>
          가로축 {colName}, 세로축 {rowName}. 칸 안 숫자는{" "}
          {OBJECTIVE_METRIC_LABEL[result.objective_metric]}입니다.
        </caption>
        <thead>
          <tr>
            <th scope="col">
              <span className="dim">{`${rowName} \\ ${colName}`}</span>
            </th>
            {colValues.map((v) => (
              <th key={v} scope="col">
                {v}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rowValues.map((rowV) => (
            <tr key={rowV}>
              <th scope="row">{rowV}</th>
              {colValues.map((colV) => {
                const cell = findCell(rowV, colV);
                if (cell == null) {
                  return (
                    <td key={`${rowV}-${colV}`}>
                      <span className="hm-cell degenerate">{EMPTY_CELL}</span>
                    </td>
                  );
                }
                const objVal = cell.objective_value;
                const isDegenerate = cell.is_degenerate || cell.num_trades === 0;
                const isBest =
                  bestParamValues != null &&
                  bestParamValues[rowName] === rowV &&
                  bestParamValues[colName] === colV &&
                  (Object.keys(fixOthers).length === 0 ||
                    Object.entries(fixOthers).every(([k, v]) => bestParamValues[k] === v));
                if (isDegenerate || objVal === null) {
                  return (
                    <td key={`${rowV}-${colV}`}>
                      <span
                        className="hm-cell degenerate"
                        title={OPTIMIZER_EMPTY_REASON.degenerateNoSharpe}
                      >
                        {EMPTY_CELL}
                      </span>
                    </td>
                  );
                }
                return (
                  <td key={`${rowV}-${colV}`}>
                    <span
                      className={cn("hm-cell", isBest && "best")}
                      style={{ background: bgFor(objVal) }}
                      title={`${rowName}=${rowV}, ${colName}=${colV}, ${OBJECTIVE_METRIC_LABEL[result.objective_metric]}=${objVal.toFixed(2)}${isBest ? " (최적)" : ""}`}
                    >
                      {objVal.toFixed(2)}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="chart-note" style={{ paddingLeft: 0, paddingRight: 0 }}>
        <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <line x1="12" y1="11" x2="12" y2="16" />
          <line x1="12" y1="7.5" x2="12.01" y2="7.5" />
        </svg>
        칸 농도는 목표값을 선형으로 이었습니다. 색만으로 읽지 않도록 숫자를 함께 인쇄합니다. 최적
        칸은 색이 아니라 코퍼 테두리로, 거래 0건 축퇴 칸은 색을 넣지 않고 점선 테두리로 스케일에서
        빼냅니다.
      </p>
      {result.param_names.length > 2 && Object.keys(fixOthers).length > 0 ? (
        <p className="chart-note" style={{ paddingLeft: 0, paddingRight: 0 }}>
          <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="9" />
            <line x1="12" y1="11" x2="12" y2="16" />
            <line x1="12" y1="7.5" x2="12.01" y2="7.5" />
          </svg>
          기타 변수는 최적 셀 값으로 고정한 단면입니다.{" "}
          {Object.entries(fixOthers)
            .map(([k, v]) => `${k}=${v}`)
            .join(", ")}
        </p>
      ) : null}
    </div>
  );
}
