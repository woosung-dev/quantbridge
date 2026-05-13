"use client";

import type { BacktestMetricsOut } from "@/features/backtest/schemas";

interface MetricsDetailProps {
  metrics: BacktestMetricsOut;
}

function fmt(
  v: number | null | undefined,
  opts?: { pct?: boolean; decimals?: number },
): string {
  if (v == null || !Number.isFinite(v)) return "—";
  if (opts?.pct) return `${(v * 100).toFixed(2)}%`;
  return v.toFixed(opts?.decimals ?? 3);
}

function fmtInt(v: number | null | undefined): string {
  if (v == null) return "—";
  return v.toLocaleString("en-US");
}

function fmtHours(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "—";
  if (v < 1) return `${(v * 60).toFixed(0)}분`;
  if (v < 24) return `${v.toFixed(1)}시간`;
  return `${(v / 24).toFixed(1)}일`;
}

function fmtBars(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${v.toLocaleString("en-US")} bar`;
}

export function MetricsDetail({ metrics }: MetricsDetailProps) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
      {/* 수익성 — 8 row */}
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
              label="연간수익률 (CAGR)"
              value={fmt(metrics.annual_return_pct, { pct: true })}
              isNew
            />
            <MetricRow
              label="평균 거래"
              value={fmt(metrics.avg_trade_pct, { pct: true })}
              isNew
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
            <MetricRow
              label="최고 거래"
              value={fmt(metrics.best_trade_pct, { pct: true })}
              isNew
            />
            <MetricRow
              label="최악 거래"
              value={fmt(metrics.worst_trade_pct, { pct: true })}
              isNew
            />
          </tbody>
        </table>
      </section>

      {/* 위험 조정 — 5 row */}
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
            <MetricRow
              label="DD 지속 기간"
              value={fmtBars(metrics.drawdown_duration)}
              isNew
            />
          </tbody>
        </table>
      </section>

      {/* 거래 패턴 — 5 row (Sprint 30-γ 신규 section) */}
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-[color:var(--text-muted)]">
          거래 패턴
        </h3>
        <table className="w-full text-sm">
          <tbody className="divide-y divide-[color:var(--border)]">
            <MetricRow
              label="롱 승률"
              value={fmt(metrics.long_win_rate_pct, { pct: true })}
              isNew
            />
            <MetricRow
              label="숏 승률"
              value={fmt(metrics.short_win_rate_pct, { pct: true })}
              isNew
            />
            <MetricRow
              label="연속 승 최대"
              value={fmtInt(metrics.consecutive_wins_max)}
              isNew
            />
            <MetricRow
              label="연속 패 최대"
              value={fmtInt(metrics.consecutive_losses_max)}
              isNew
            />
            <MetricRow
              label="평균 보유 시간"
              value={fmtHours(metrics.avg_holding_hours)}
              isNew
            />
          </tbody>
        </table>
      </section>
    </div>
  );
}

function MetricRow({
  label,
  value,
  isNew = false,
}: {
  label: string;
  value: string;
  isNew?: boolean;
}) {
  return (
    <tr>
      <td className="py-2.5 pr-4 text-[color:var(--text-secondary)]">
        {label}
        {isNew ? (
          <span
            className="ml-1 align-text-top text-[9px] text-[color:var(--text-muted)]"
            aria-label="신규 metric"
          >
            ★
          </span>
        ) : null}
      </td>
      <td className="py-2.5 text-right font-mono font-medium">{value}</td>
    </tr>
  );
}
