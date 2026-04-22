"use client";

import type { BacktestMetricsOut } from "@/features/backtest/schemas";

interface MetricsDetailProps {
  metrics: BacktestMetricsOut;
}

function fmt(
  v: number | null | undefined,
  opts?: { pct?: boolean; decimals?: number },
): string {
  if (v == null) return "—";
  if (opts?.pct) return `${(v * 100).toFixed(2)}%`;
  return v.toFixed(opts?.decimals ?? 3);
}

export function MetricsDetail({ metrics }: MetricsDetailProps) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      {/* 수익성 */}
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-[color:var(--text-muted)]">
          수익성
        </h3>
        <table className="w-full text-sm">
          <tbody className="divide-y divide-[color:var(--border)]">
            <MetricRow
              label="총 수익률"
              value={fmt(metrics.total_return, { pct: true })}
            />
            <MetricRow
              label="Profit Factor"
              value={fmt(metrics.profit_factor)}
            />
            <MetricRow
              label="평균 수익"
              value={fmt(metrics.avg_win, { pct: true })}
            />
            <MetricRow
              label="평균 손실"
              value={fmt(metrics.avg_loss, { pct: true })}
            />
          </tbody>
        </table>
      </section>
      {/* 위험 조정 */}
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-[color:var(--text-muted)]">
          위험 조정
        </h3>
        <table className="w-full text-sm">
          <tbody className="divide-y divide-[color:var(--border)]">
            <MetricRow label="Sharpe Ratio" value={fmt(metrics.sharpe_ratio)} />
            <MetricRow
              label="Sortino Ratio"
              value={fmt(metrics.sortino_ratio)}
            />
            <MetricRow
              label="Calmar Ratio"
              value={fmt(metrics.calmar_ratio)}
            />
            <MetricRow
              label="Max Drawdown"
              value={fmt(metrics.max_drawdown, { pct: true })}
            />
          </tbody>
        </table>
      </section>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <tr>
      <td className="py-2.5 pr-4 text-[color:var(--text-secondary)]">
        {label}
      </td>
      <td className="py-2.5 text-right font-mono font-medium">{value}</td>
    </tr>
  );
}
