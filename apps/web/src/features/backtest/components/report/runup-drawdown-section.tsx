"use client";

// TV "런업 & 드로다운" 섹션 — 서브탭 오버뷰/런업/드로다운
// 데이터 = metrics.excursion_stats (BE 팩). 구 백테스트(null) → 잠금 empty state.
// `_intrabar` 행은 "(bar 근사)" 라벨 의무 (Surface Trust — 틱 데이터 아님).

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import type {
  BacktestMetricsOut,
  ExcursionStats,
} from "@/features/backtest/schemas";
import { formatCurrency, formatPercent } from "@/features/backtest/utils";

import { MetricTable, type MetricRowSpec } from "@/features/backtest/components/report/metric-table";

interface RunupDrawdownSectionProps {
  metrics: BacktestMetricsOut;
  initialCapital: number;
}

const BAR_APPROX = "(bar 근사)";

function usd(value: number | null | undefined): string | null {
  if (value == null || !Number.isFinite(value)) return null;
  return `${formatCurrency(value)} USDT`;
}

function days(value: number | null | undefined): string | null {
  if (value == null || !Number.isFinite(value)) return null;
  return `${value.toFixed(1)} 일`;
}

function usdWithPct(
  abs: number | null | undefined,
  pctValue: number | null | undefined,
): string | null {
  const absStr = usd(abs);
  if (absStr === null) return null;
  return pctValue != null ? `${absStr} (${formatPercent(pctValue)})` : absStr;
}

export function RunupDrawdownSection({
  metrics,
  initialCapital,
}: RunupDrawdownSectionProps) {
  const stats: ExcursionStats | null | undefined = metrics.excursion_stats;

  if (stats == null) {
    return (
      <div
        className="flex h-40 flex-col items-center justify-center gap-1 rounded-lg border border-dashed text-sm text-muted-foreground"
        data-testid="runup-drawdown-locked"
      >
        <p>런업/드로다운 통계가 없는 구 백테스트입니다</p>
        <p className="text-xs">재실행하면 상승/낙폭 에피소드 통계가 생성됩니다</p>
      </div>
    );
  }

  const mddVsCapital =
    stats.max_drawdown_intrabar_abs != null && initialCapital > 0
      ? stats.max_drawdown_intrabar_abs / initialCapital
      : null;
  const runupVsCapital =
    stats.max_runup_intrabar_abs != null && initialCapital > 0
      ? stats.max_runup_intrabar_abs / initialCapital
      : null;

  const runupRows: MetricRowSpec[] = [
    { label: "평균 상승폭 지속 기간 (종가 기준)", value: days(stats.avg_runup_duration_days) },
    { label: "평균 상승폭 (종가 기준)", value: usd(stats.avg_runup_abs), tone: "bullish" },
    {
      label: "최대 상승폭 (종가 기준)",
      value: usdWithPct(stats.max_runup_abs, stats.max_runup_pct),
      tone: "bullish",
    },
    {
      label: "최대 상승폭 (인트라바)",
      value: usdWithPct(stats.max_runup_intrabar_abs, stats.max_runup_intrabar_pct),
      hint: BAR_APPROX,
      tone: "bullish",
    },
    {
      label: "초기 자본 대비 최대 상승률 (인트라바)",
      value: runupVsCapital != null ? formatPercent(runupVsCapital) : null,
      hint: BAR_APPROX,
      tone: "bullish",
    },
  ];

  const drawdownRows: MetricRowSpec[] = [
    { label: "평균 낙폭 지속 기간 (종가 기준)", value: days(stats.avg_drawdown_duration_days) },
    { label: "평균 낙폭 (종가 기준)", value: usd(stats.avg_drawdown_abs), tone: "bearish" },
    {
      label: "최대 손실폭 (종가 기준)",
      value: usdWithPct(stats.max_drawdown_abs, Math.abs(metrics.max_drawdown)),
      tone: "bearish",
    },
    {
      label: "최대 손실폭 (인트라바)",
      value: usdWithPct(
        stats.max_drawdown_intrabar_abs,
        stats.max_drawdown_intrabar_pct,
      ),
      hint: BAR_APPROX,
      tone: "bearish",
    },
    {
      label: "초기 자본 대비 최대 손실률 (인트라바)",
      value: mddVsCapital != null ? formatPercent(mddVsCapital) : null,
      hint: BAR_APPROX,
      tone: "bearish",
    },
    {
      label: "최대 손실폭의 회복",
      value:
        stats.max_drawdown_recovery_days != null
          ? `${stats.max_drawdown_recovery_days.toFixed(1)} 일 (${stats.max_drawdown_recovery_bars ?? "?"} bars)`
          : "미회복",
    },
  ];

  return (
    <section data-testid="runup-drawdown-section">
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview" className="data-active:text-[var(--primary)]">
            오버뷰
          </TabsTrigger>
          <TabsTrigger value="runup" className="data-active:text-[var(--primary)]">
            런업
          </TabsTrigger>
          <TabsTrigger value="drawdown" className="data-active:text-[var(--primary)]">
            드로다운
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <OverviewKpi label="평균 상승 지속 기간" value={days(stats.avg_runup_duration_days) ?? "—"} />
            <OverviewKpi label="평균 낙폭 지속 기간" value={days(stats.avg_drawdown_duration_days) ?? "—"} />
            <OverviewKpi
              label="초기 자본 대비 최대 손실률"
              value={mddVsCapital != null ? formatPercent(mddVsCapital) : "—"}
              hint={BAR_APPROX}
              tone="bearish"
            />
            <OverviewKpi
              label="최대 손실폭의 회복"
              value={
                stats.max_drawdown_recovery_days != null
                  ? `${stats.max_drawdown_recovery_days.toFixed(1)} 일`
                  : "미회복"
              }
            />
          </div>
        </TabsContent>

        <TabsContent value="runup" className="mt-4">
          <MetricTable rows={runupRows} caption={`인트라바 값은 bar high/low 근사 ${BAR_APPROX} — 틱 정밀 아님.`} />
        </TabsContent>

        <TabsContent value="drawdown" className="mt-4">
          <MetricTable rows={drawdownRows} caption={`인트라바 값은 bar high/low 근사 ${BAR_APPROX} — 틱 정밀 아님.`} />
        </TabsContent>
      </Tabs>
    </section>
  );
}

function OverviewKpi({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "bullish" | "bearish" | "neutral";
}) {
  const toneClass =
    tone === "bullish"
      ? "text-[color:var(--bullish)]"
      : tone === "bearish"
        ? "text-[color:var(--bearish)]"
        : "text-foreground";
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
        {label}
        {hint ? <span className="ml-1 normal-case">{hint}</span> : null}
      </span>
      <span className={`font-mono text-lg font-bold tabular-nums ${toneClass}`}>
        {value}
      </span>
    </div>
  );
}
