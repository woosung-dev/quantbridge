// 백테스트 이력 카드 — prototype 01 의 .history-card 1:1 (Sprint 43 W9-fidelity)
// hover: border primary-100 + translateY(-1px) + soft shadow / ROI 색상 / Sharpe meta.
"use client";

import Link from "next/link";

export interface BacktestHistoryEntry {
  id: string;
  /** 표시용 상대 시각 ("오늘 14:23", "어제 09:10") */
  dateLabel: string;
  /** -100 ~ +∞ 의 백분율 수익률 (예: 12.4) */
  roiPct: number;
  /** 거래 횟수 */
  trades: number;
  /** 승률 백분율 (예: 62) */
  winRatePct: number;
  /** Sharpe ratio (소수점 1자리) */
  sharpe: number;
}

export interface BacktestHistoryCardProps {
  entry: BacktestHistoryEntry;
  href?: string;
}

function formatRoi(roi: number): string {
  const sign = roi >= 0 ? "+" : "";
  return `${sign}${roi.toFixed(1)}%`;
}

export function BacktestHistoryCard({ entry, href }: BacktestHistoryCardProps) {
  const roiPositive = entry.roiPct >= 0;

  // prototype: grid-template-columns: 1fr auto / gap 4px 10px / padding 12 14
  const inner = (
    <div
      className="grid grid-cols-[1fr_auto] items-baseline gap-x-2.5 gap-y-1 rounded-[10px] border border-[color:var(--border)] bg-[color:var(--bg)] px-3.5 py-3 transition-all hover:-translate-y-px hover:border-[color:var(--primary-100)] hover:shadow-[0_4px_10px_rgba(37,99,235,0.06)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--primary)]/30"
      data-testid="backtest-history-card"
    >
      <span className="font-mono text-[0.75rem] font-medium text-[color:var(--text-muted)]">
        {entry.dateLabel}
      </span>
      <span
        className={
          "text-right font-mono text-[0.9375rem] font-bold " +
          (roiPositive
            ? "text-[color:var(--success)]"
            : "text-[color:var(--destructive)]")
        }
        data-testid="backtest-history-roi"
      >
        {formatRoi(entry.roiPct)}
      </span>
      <span className="flex items-center gap-2 text-[0.75rem] text-[color:var(--text-secondary)]">
        <span>{entry.trades} trades</span>
        <span
          aria-hidden
          className="size-[3px] rounded-full bg-[color:var(--text-muted)]"
        />
        <span>Win {entry.winRatePct}%</span>
      </span>
      <span className="text-right font-mono text-[0.75rem] text-[color:var(--text-secondary)]">
        Sharpe{" "}
        <strong className="font-semibold text-[color:var(--text-primary)]">
          {entry.sharpe.toFixed(1)}
        </strong>
      </span>
    </div>
  );

  const ariaLabel = `${entry.dateLabel} 백테스트 결과 ${formatRoi(entry.roiPct)} · ${entry.trades}건 · 승률 ${entry.winRatePct}% · Sharpe ${entry.sharpe.toFixed(1)}`;

  if (href) {
    return (
      <Link
        href={href}
        className="block no-underline"
        aria-label={ariaLabel}
      >
        {inner}
      </Link>
    );
  }

  return (
    <article tabIndex={0} aria-label={ariaLabel}>
      {inner}
    </article>
  );
}
