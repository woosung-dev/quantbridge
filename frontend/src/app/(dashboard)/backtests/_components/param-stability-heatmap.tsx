// Sprint 51 BL-220: Param Stability heatmap — pine_v2 input override 9-cell 시각화 (Sprint 50 cost-assumption-heatmap 1:1 재사용)
"use client";

import type { ParamStabilityResult } from "@/features/backtest/schemas";
import { cn } from "@/lib/utils";

interface Props {
  result: ParamStabilityResult;
}

// 색맹 fallback marker (Sprint 50 codex P2#8 패턴). Sharpe 부호 = 색만이 아닌 ▲/▼ 글리프로 구분.
function signMarkerFor(sharpe: number | null): string {
  if (sharpe === null) return "";
  return sharpe >= 0 ? "▲" : "▼";
}

export function ParamStabilityHeatmap({ result }: Props) {
  const { param1_name, param2_name, param1_values, param2_values, cells } =
    result;

  const sharpeNumbers = cells
    .map((c) => (c.is_degenerate || c.sharpe === null ? null : Number(c.sharpe)))
    .filter((v): v is number => v !== null);
  // codex G.4 P3 fix: 모든 non-degenerate cell sharpe=0 시 maxAbs=0 → bgFor() 의
  // (Math.abs(sharpe) / maxAbs) * 100 가 0/0 NaN% CSS. || 1 fallback 으로 차단.
  const maxAbsRaw =
    sharpeNumbers.length > 0 ? Math.max(...sharpeNumbers.map(Math.abs)) : 1;
  const maxAbs = maxAbsRaw || 1;

  function bgFor(cell: (typeof cells)[number]): string | undefined {
    if (cell.is_degenerate || cell.sharpe === null) return undefined;
    const sharpe = Number(cell.sharpe);
    const intensity = Math.min(100, (Math.abs(sharpe) / maxAbs) * 100);
    const color = sharpe >= 0 ? "var(--success)" : "var(--destructive)";
    return `color-mix(in srgb, ${color} ${intensity}%, transparent)`;
  }

  return (
    <div className="space-y-3 overflow-x-auto">
      {/* Legend — 색만으로 부호를 전달하지 않도록 sign marker 명시 */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <span className="text-success">▲</span> 양수 Sharpe
        </span>
        <span className="flex items-center gap-1">
          <span className="text-destructive">▼</span> 음수 Sharpe
        </span>
        <span>— 거래 0건 (degenerate cell)</span>
      </div>
      <table
        className="border-collapse"
        aria-label="Param Stability heatmap"
      >
        <thead>
          <tr>
            <th
              className="p-1 text-xs text-muted-foreground"
              scope="col"
            >{`${param1_name} \\ ${param2_name}`}</th>
            {param2_values.map((v) => (
              <th key={v} className="p-1 text-xs font-medium" scope="col">
                {v}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {param1_values.map((v1, i) => (
            <tr key={v1}>
              <th
                className="p-1 text-xs font-medium text-right"
                scope="row"
              >
                {v1}
              </th>
              {param2_values.map((v2, j) => {
                const cell = cells[i * param2_values.length + j];
                if (cell == null) return null;
                const sharpeNum =
                  cell.is_degenerate || cell.sharpe === null
                    ? null
                    : Number(cell.sharpe);
                const tooltip = cell.is_degenerate
                  ? `${param1_name}=${v1}, ${param2_name}=${v2}\n거래 0건 (degenerate)`
                  : `${param1_name}=${v1}, ${param2_name}=${v2}\nSharpe=${cell.sharpe ?? "—"}\nReturn=${cell.total_return}\nMDD=${cell.max_drawdown}\nTrades=${cell.num_trades}`;
                return (
                  <td
                    key={`${v1}-${v2}`}
                    className={cn(
                      "p-2 text-xs text-center min-w-[72px] border border-border",
                      // keyboard focus ring (2px outline + offset)
                      "focus:outline-2 focus:outline-primary focus:outline-offset-1",
                      cell.is_degenerate && "text-muted-foreground",
                    )}
                    style={
                      cell.is_degenerate ? undefined : { background: bgFor(cell) }
                    }
                    tabIndex={0}
                    aria-label={tooltip.replace(/\n/g, ", ")}
                    title={tooltip}
                  >
                    <span className="block leading-tight">
                      {cell.is_degenerate || sharpeNum === null ? (
                        "—"
                      ) : (
                        <>
                          <span aria-hidden="true">{signMarkerFor(sharpeNum)}</span>{" "}
                          {sharpeNum.toFixed(2)}
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
        Sharpe 값. 색 강도 = |Sharpe|. 부호는 ▲/▼ marker (색맹 fallback).
      </p>
    </div>
  );
}
