// 베이지안 최적화의 최적 파라미터 테이블 + 비정상 반복 배지
"use client";

import { AlertTriangle, Star } from "lucide-react";

import type { BayesianSearchResult } from "@/features/optimizer/schemas";

interface Props {
  result: BayesianSearchResult;
}

export function BayesianBestParamsTable({ result }: Props) {
  const hasBest =
    result.best_iteration_idx !== null && result.best_params !== null;
  const degenerateRatio =
    result.total_iterations > 0
      ? (result.degenerate_count / result.total_iterations) * 100
      : 0;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <h4 className="font-display font-semibold text-foreground">
          최적 파라미터
        </h4>
        {result.degenerate_count > 0 && (
          <span
            data-tone="warning"
            className="inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium"
            aria-label={`${result.degenerate_count} of ${result.total_iterations} iterations were degenerate`}
          >
            <AlertTriangle className="h-3 w-3" aria-hidden="true" />
            비정상 {result.degenerate_count} / {result.total_iterations} (
            {degenerateRatio.toFixed(0)}%)
          </span>
        )}
      </div>

      {!hasBest ? (
        <p className="rounded-lg border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
          모든 반복이 비정상(거래 0건 또는 지표 산출 불가)이라 최적 파라미터를 선정하지
          못했습니다. 파라미터 범위나 전략을 다시 확인해 주세요.
        </p>
      ) : (
        <div className="rounded-lg border border-border bg-card p-4 shadow-card">
          <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
            <span className="inline-flex items-center gap-1.5 font-semibold text-primary">
              <Star className="h-4 w-4 fill-current" aria-hidden="true" />
              최적 반복
            </span>
            <span className="text-xs text-muted-foreground">
              #<span className="font-mono tabular-nums">{result.best_iteration_idx}</span>
            </span>
            <span className="text-xs text-muted-foreground">
              · {result.objective_metric}{" "}
              <span className="font-mono tabular-nums text-foreground">
                {result.best_objective_value === null
                  ? "—"
                  : result.best_objective_value.toFixed(4)}
              </span>
            </span>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th className="py-1.5 pr-3 font-medium">파라미터</th>
                <th className="py-1.5 text-right font-medium">값</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(result.best_params ?? {}).map(([name, value]) => (
                <tr key={name} className="border-b border-border/60 last:border-b-0">
                  <td className="py-1.5 pr-3 font-mono">{name}</td>
                  <td className="py-1.5 text-right font-mono tabular-nums">
                    {value.toFixed(6)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
