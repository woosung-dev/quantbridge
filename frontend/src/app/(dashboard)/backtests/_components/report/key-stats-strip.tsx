"use client";

// TV Strategy Tester "주요 통계" 스트립 — 총 PnL / 최대 손실폭 / 수익성 거래 / 수익지수
// 상시 노출 히어로 통계. 큰 mono 숫자 + 위 라벨 (Terminal Tape).
// abs 금액(구 백테스트 null)은 % 단독 표기로 graceful degrade (Surface Trust).

import type { BacktestConfig, BacktestMetricsOut } from "@/features/backtest/schemas";
import { formatCurrency, formatPercent } from "@/features/backtest/utils";

import { buildMddCaption } from "../metrics-cards";

interface KeyStatsStripProps {
  metrics: BacktestMetricsOut;
  config?: BacktestConfig | null;
}

type Tone = "bullish" | "bearish" | "neutral";

function toneClass(tone: Tone): string {
  if (tone === "bullish") return "text-[color:var(--bullish)]";
  if (tone === "bearish") return "text-[color:var(--bearish)]";
  return "text-foreground";
}

function StatBlock({
  label,
  value,
  sub,
  tone = "neutral",
  caption,
}: {
  label: string;
  value: string;
  sub?: string | null;
  tone?: Tone;
  caption?: string | null;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-1 px-4 py-3 first:pl-5 last:pr-5">
      <span className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
        {label}
      </span>
      <span
        className={`font-mono text-xl font-bold tabular-nums md:text-2xl ${toneClass(tone)}`}
      >
        {value}
      </span>
      {sub ? (
        <span className={`font-mono text-xs tabular-nums ${toneClass(tone)} opacity-80`}>
          {sub}
        </span>
      ) : null}
      {caption ? (
        <span className="text-[11px] text-muted-foreground">{caption}</span>
      ) : null}
    </div>
  );
}

export function KeyStatsStrip({ metrics, config }: KeyStatsStripProps) {
  const netAbs = metrics.net_profit_abs ?? null;
  const totalReturn = metrics.total_return;
  const pnlTone: Tone =
    totalReturn > 0 ? "bullish" : totalReturn < 0 ? "bearish" : "neutral";

  const mddAbs = metrics.excursion_stats?.max_drawdown_abs ?? null;
  const mddCaption = buildMddCaption({
    leverage: config?.leverage ?? 1,
    mddBelowCapital: metrics.max_drawdown < -1,
    mddExceedsCapital: metrics.mdd_exceeds_capital ?? null,
  });

  const winRate = metrics.win_rate;
  const winCount = Math.round(winRate * metrics.num_trades);

  const pf = metrics.profit_factor ?? null;

  return (
    <section
      aria-label="주요 통계"
      className="grid grid-cols-2 divide-y divide-[color:var(--border)] rounded-xl border bg-card shadow-[var(--card-shadow)] md:grid-cols-4 md:divide-x md:divide-y-0"
      data-testid="key-stats-strip"
    >
      <StatBlock
        label="총 PnL"
        value={
          netAbs !== null
            ? `${netAbs >= 0 ? "+" : ""}${formatCurrency(netAbs)} USDT`
            : formatPercent(totalReturn)
        }
        sub={
          netAbs !== null
            ? `${totalReturn >= 0 ? "+" : ""}${formatPercent(totalReturn)}`
            : null
        }
        tone={pnlTone}
      />
      <StatBlock
        label="최대 손실폭"
        value={
          mddAbs !== null
            ? `${formatCurrency(mddAbs)} USDT`
            : formatPercent(Math.abs(metrics.max_drawdown))
        }
        sub={mddAbs !== null ? formatPercent(Math.abs(metrics.max_drawdown)) : null}
        tone="bearish"
        caption={mddCaption}
      />
      <StatBlock
        label="수익성 거래"
        value={formatPercent(winRate)}
        sub={`${winCount}/${metrics.num_trades} 거래`}
        tone={winRate >= 0.5 ? "bullish" : "neutral"}
      />
      <StatBlock
        label="수익지수"
        value={pf !== null ? pf.toFixed(3) : "—"}
        sub={pf !== null ? "Profit Factor" : "손실 거래 없음"}
        tone={pf !== null && pf >= 1 ? "bullish" : pf !== null ? "bearish" : "neutral"}
      />
    </section>
  );
}
