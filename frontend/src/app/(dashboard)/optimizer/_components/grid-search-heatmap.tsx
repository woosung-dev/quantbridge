// Sprint 54 — Grid Search 2D heatmap (cost-assumption-heatmap.tsx 1:1 fork, best cell highlight 추가)
"use client";

import { ArrowDown, ArrowUp, Star } from "lucide-react";

import {
  OBJECTIVE_DIRECTION_LABEL,
  OBJECTIVE_METRIC_LABEL,
} from "@/features/optimizer/labels";
import type { GridSearchResult } from "@/features/optimizer/schemas";
import { cn } from "@/lib/utils";

interface Props {
  result: GridSearchResult;
  /** 2D heatmap 으로 그릴 변수쌍 (param_names.length === 2 일 때 자동, N>2 일 때는 pair-selector 선택) */
  pair: readonly [string, string];
}

// 부호 화살표 — 색 강도와 별개로 색맹 대비용 sign fallback.
function SignArrow({ value }: { value: number | null }) {
  if (value === null) return null;
  return value >= 0 ? (
    <ArrowUp className="inline h-3 w-3" aria-hidden="true" />
  ) : (
    <ArrowDown className="inline h-3 w-3" aria-hidden="true" />
  );
}

export function GridSearchHeatmap({ result, pair }: Props) {
  const [xName, yName] = pair;
  const xValues = result.param_values[xName] ?? [];
  const yValues = result.param_values[yName] ?? [];

  // pair 가 전체 param_names 와 일치하는 경우 (2D) → 모든 cell row-major 매핑.
  // N>2 인 경우 → best cell 의 나머지 변수 값으로 fix, 해당 (x, y) 평면 slice.
  const fixOthers: Record<string, number> = {};
  if (result.param_names.length > 2 && result.best_cell_index !== null) {
    const bestCell = result.cells[result.best_cell_index];
    if (bestCell) {
      for (const k of result.param_names) {
        if (k !== xName && k !== yName) {
          fixOthers[k] = bestCell.param_values[k] ?? 0;
        }
      }
    }
  }

  // cell lookup: (x, y) → cell (fix other vars equal).
  function findCell(x: number, y: number): GridSearchResult["cells"][number] | null {
    for (const c of result.cells) {
      if (c.param_values[xName] !== x || c.param_values[yName] !== y) continue;
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

  // objective_value 정규화 — best cell highlight + 색 강도.
  const objNumbers = result.cells
    .map((c) => c.objective_value)
    .filter((v): v is number => v !== null);
  const maxAbs =
    objNumbers.length > 0 ? Math.max(...objNumbers.map(Math.abs), 1) : 1;

  function bgFor(value: number | null): string | undefined {
    if (value === null) return undefined;
    const intensity = Math.min(100, (Math.abs(value) / maxAbs) * 100);
    const color =
      result.direction === "maximize"
        ? value >= 0 ? "var(--bullish)" : "var(--bearish)"
        : value <= 0 ? "var(--bullish)" : "var(--bearish)";
    return `color-mix(in srgb, ${color} ${intensity}%, transparent)`;
  }

  const bestParamValues =
    result.best_cell_index !== null
      ? result.cells[result.best_cell_index]?.param_values
      : null;

  return (
    <div className="space-y-3 overflow-x-auto">
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <ArrowUp className="h-3 w-3 text-bullish" aria-hidden="true" />{" "}
          {result.direction === "maximize" ? "유리" : "음수 우대"}
        </span>
        <span className="flex items-center gap-1">
          <ArrowDown className="h-3 w-3 text-bearish" aria-hidden="true" />{" "}
          {result.direction === "maximize" ? "불리" : "양수 음수전환"}
        </span>
        <span>— 거래 0건 또는 NaN (degenerate)</span>
        <span className="inline-flex items-center gap-1 rounded border border-primary px-1.5 py-0.5 text-primary">
          <Star className="h-3 w-3 fill-current" aria-hidden="true" /> 최적 셀
        </span>
        <span>
          · 목표 지표 = {OBJECTIVE_METRIC_LABEL[result.objective_metric]} (
          {OBJECTIVE_DIRECTION_LABEL[result.direction]})
        </span>
      </div>
      <table
        className="border-collapse"
        aria-label={`Grid Search heatmap (${xName} × ${yName})`}
      >
        <thead>
          <tr>
            <th
              className="p-1 text-xs text-muted-foreground"
              scope="col"
            >{`${xName} \\ ${yName}`}</th>
            {yValues.map((v) => (
              <th
                key={v}
                className="p-1 font-mono text-xs font-medium tabular-nums"
                scope="col"
              >
                {v}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {xValues.map((x) => (
            <tr key={x}>
              <th className="p-1 font-mono text-xs font-medium tabular-nums text-right" scope="row">
                {x}
              </th>
              {yValues.map((y) => {
                const cell = findCell(x, y);
                if (cell == null) {
                  return (
                    <td
                      key={`${x}-${y}`}
                      className="p-2 text-xs text-center min-w-[72px] border border-border text-muted-foreground"
                    >
                      —
                    </td>
                  );
                }
                const objVal = cell.objective_value;
                const isBest =
                  bestParamValues != null &&
                  bestParamValues[xName] === x &&
                  bestParamValues[yName] === y &&
                  (Object.keys(fixOthers).length === 0 ||
                    Object.entries(fixOthers).every(
                      ([k, v]) => bestParamValues[k] === v,
                    ));
                const tooltip = cell.is_degenerate
                  ? `${xName}=${x}, ${yName}=${y}\n거래 0건 (degenerate)`
                  : `${xName}=${x}, ${yName}=${y}\n${OBJECTIVE_METRIC_LABEL[result.objective_metric]}=${objVal ?? "—"}\nSharpe=${cell.sharpe ?? "—"}\nReturn=${cell.total_return}\nMDD=${cell.max_drawdown}\nTrades=${cell.num_trades}`;
                return (
                  <td
                    key={`${x}-${y}`}
                    className={cn(
                      "p-2 font-mono text-xs text-center min-w-[72px] border border-border tabular-nums",
                      "focus:outline-2 focus:outline-primary focus:outline-offset-1",
                      cell.is_degenerate && "text-muted-foreground",
                      isBest && "outline outline-2 outline-primary outline-offset-[-2px]",
                    )}
                    style={
                      cell.is_degenerate ? undefined : { background: bgFor(objVal) }
                    }
                    tabIndex={0}
                    aria-label={tooltip.replace(/\n/g, ", ") + (isBest ? " 최적 셀" : "")}
                    title={tooltip + (isBest ? "\n최적 셀" : "")}
                  >
                    <span className="block leading-tight">
                      {cell.is_degenerate || objVal === null ? (
                        "—"
                      ) : (
                        <>
                          {isBest && (
                            <Star
                              className="mr-0.5 inline h-3 w-3 fill-current text-primary"
                              aria-hidden="true"
                            />
                          )}
                          <SignArrow value={objVal} />{" "}
                          {objVal.toFixed(2)}
                        </>
                      )}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-muted-foreground">
        목표 지표 = {OBJECTIVE_METRIC_LABEL[result.objective_metric]}. 색 강도는 |값| 기준이며, 위·아래
        화살표는 색맹 대비 부호, 별 아이콘은 최적 셀을 나타냅니다.
      </p>
      {result.param_names.length > 2 && Object.keys(fixOthers).length > 0 && (
        <p className="text-xs text-muted-foreground">
          기타 변수 고정: {Object.entries(fixOthers)
            .map(([k, v]) => `${k}=${v}`)
            .join(", ")}{" "}
          (best cell 기준 slice). N-dim viz 확장 예정.
        </p>
      )}
    </div>
  );
}
