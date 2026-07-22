"use client";

// 01 요약 — variant-c "성과 요약" 이식. 공용 .kpi-row/.kpi 를 소비한다.
// 프로토타입 variant-c.html:1142-1170 의 4 KPI(총 수익률/순손익/최대 낙폭/샤프 지수) 구조.
// 미터 바(.meter)는 정규화 기준이 스키마로 뒷받침되지 않아 그리지 않는다(S6~S8 kpi-row 선례,
// LESSON-039 Surface Trust). foot 문구는 전부 스키마가 받치는 값(연환산·수수료·회복일)만 쓴다.

import type { ReactNode } from "react";

import type { BacktestConfig, BacktestMetricsOut } from "@/features/backtest/schemas";
import { formatCurrency, formatPercent } from "@/features/backtest/utils";

import { buildMddCaption } from "@/app/(dashboard)/backtests/_components/charts/mdd-caption";

interface KeyStatsStripProps {
  metrics: BacktestMetricsOut;
  config?: BacktestConfig | null;
}

type Tone = "pos" | "neg" | "neutral";

function toneClass(tone: Tone): string {
  return tone === "pos"
    ? "kpi-value mono pos"
    : tone === "neg"
      ? "kpi-value mono neg"
      : "kpi-value mono";
}

function signedPct(v: number, digits = 2): string {
  const sign = v > 0 ? "+" : "";
  return `${sign}${formatPercent(v, digits)}`;
}

function signedCurrency(v: number): string {
  const sign = v > 0 ? "+" : "";
  return `${sign}${formatCurrency(v)}`;
}

function KpiCard({
  label,
  value,
  tone = "neutral",
  foot,
  testId,
}: {
  label: string;
  value: string;
  tone?: Tone;
  foot?: ReactNode;
  testId?: string;
}) {
  return (
    <article className="card kpi" role="listitem">
      <p className="kpi-label">{label}</p>
      <p className={toneClass(tone)} data-testid={testId}>
        {value}
      </p>
      {foot ? <p className="kpi-foot">{foot}</p> : null}
    </article>
  );
}

export function KeyStatsStrip({ metrics: m, config }: KeyStatsStripProps) {
  const totalReturn = m.total_return;
  const returnTone: Tone =
    totalReturn > 0 ? "pos" : totalReturn < 0 ? "neg" : "neutral";

  const netAbs = m.net_profit_abs ?? null;
  const totalFees = m.total_fees ?? null;

  const recoveryDays = m.excursion_stats?.max_drawdown_recovery_days ?? null;

  const mddCaption = buildMddCaption({
    leverage: config?.leverage ?? 1,
    mddBelowCapital: m.max_drawdown < -1,
    mddExceedsCapital: m.mdd_exceeds_capital ?? null,
  });

  return (
    <div
      className="kpi-row"
      role="list"
      aria-label="성과 요약"
      data-testid="key-stats-strip"
    >
      <KpiCard
        label="총 수익률"
        value={signedPct(totalReturn)}
        tone={returnTone}
        testId="kpi-total-return"
        foot={
          m.annual_return_pct != null ? (
            <>
              연환산 <span className="mono">{signedPct(m.annual_return_pct)}</span>
            </>
          ) : (
            "수수료·슬리피지 반영 후"
          )
        }
      />
      <KpiCard
        label="순손익"
        value={netAbs != null ? `${signedCurrency(netAbs)}` : signedPct(totalReturn)}
        tone={netAbs != null ? (netAbs >= 0 ? "pos" : "neg") : returnTone}
        testId="kpi-net-profit"
        foot={
          totalFees != null ? (
            <>
              USDT · 수수료 <span className="mono neg">{signedCurrency(-Math.abs(totalFees))}</span> 반영
            </>
          ) : (
            "USDT · 순(net) 기준"
          )
        }
      />
      <KpiCard
        label="최대 낙폭"
        value={signedPct(m.max_drawdown)}
        tone="neg"
        testId="kpi-max-drawdown"
        foot={
          recoveryDays != null ? (
            <>
              회복 <span className="mono">{Math.round(recoveryDays)}일</span>
            </>
          ) : (
            mddCaption ?? "종가 기준"
          )
        }
      />
      <KpiCard
        label="샤프 지수"
        value={m.sharpe_ratio.toFixed(2)}
        testId="kpi-sharpe"
        foot="무위험 수익률 0% 가정"
      />
    </div>
  );
}
