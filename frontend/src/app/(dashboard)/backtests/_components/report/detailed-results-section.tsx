"use client";

// TV "상세 결과" 섹션 — 서브탭 4: 오버뷰 / 수익률 / 벤치마킹 / 위험 조정 성과
// 오버뷰 = KPI 4 + 수익 구조 waterfall + 벤치마킹 floating bar.
// 수익률 = 월별 heatmap(거래 분석에서 이동) + 수익률 rows.
// 벤치마킹 = 전략 vs B&H 지표 테이블 (FE 파생 — equity/BH 커브 기반, 캡션 명시).
// 위험 조정 = Sharpe(bar 기준)/Sortino/Calmar/MDD/DD 지속.

import { useMemo } from "react";

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  computeCurveRange,
  computeExcessReturn,
  computeProfitStructure,
  deriveBuyAndHoldMetrics,
} from "@/features/backtest/analytics";
import type {
  BacktestMetricsOut,
  EquityPoint,
  TradeItem,
} from "@/features/backtest/schemas";
import { formatCurrency, formatPercent } from "@/features/backtest/utils";

import { MonthlyReturnsHeatmap } from "../monthly-returns-heatmap";
import { BenchmarkFloatingBars } from "./benchmark-floating-bars";
import { MetricTable, type MetricRowSpec } from "./metric-table";
import { ProfitWaterfall } from "./profit-waterfall";

interface DetailedResultsSectionProps {
  metrics: BacktestMetricsOut;
  equityCurve: readonly EquityPoint[] | null;
  buyAndHoldCurve: readonly EquityPoint[] | null;
  initialCapital: number;
  /** waterfall 파생용 전체 trades (비용 전 gross 항등식 — analytics 참조). */
  trades?: readonly TradeItem[];
  /** trades 가 표본이면 waterfall 캡션 표시. */
  tradesTruncated?: boolean;
}

function usd(value: number | null | undefined, signed = false): string | null {
  if (value == null || !Number.isFinite(value)) return null;
  const sign = signed && value > 0 ? "+" : "";
  return `${sign}${formatCurrency(value)} USDT`;
}

function pct(value: number | null | undefined, signed = false): string | null {
  if (value == null || !Number.isFinite(value)) return null;
  const sign = signed && value > 0 ? "+" : "";
  return `${sign}${formatPercent(value)}`;
}

function KpiBlock({
  label,
  value,
  sub,
  tone = "neutral",
}: {
  label: string;
  value: string;
  sub?: string | null;
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
      </span>
      <span className={`font-mono text-lg font-bold tabular-nums ${toneClass}`}>
        {value}
      </span>
      {sub ? (
        <span className="font-mono text-xs tabular-nums text-muted-foreground">
          {sub}
        </span>
      ) : null}
    </div>
  );
}

export function DetailedResultsSection({
  metrics: m,
  equityCurve,
  buyAndHoldCurve,
  initialCapital,
  trades,
  tradesTruncated = false,
}: DetailedResultsSectionProps) {
  const equityValues = useMemo(
    () => (equityCurve ?? []).map((p) => p.value),
    [equityCurve],
  );
  const bhValues = useMemo(
    () => (buyAndHoldCurve ?? []).map((p) => p.value),
    [buyAndHoldCurve],
  );

  const profitStructure = useMemo(
    () => computeProfitStructure(trades ?? []),
    [trades],
  );
  const strategyRange = useMemo(() => computeCurveRange(equityValues), [equityValues]);
  const bhRange = useMemo(() => computeCurveRange(bhValues), [bhValues]);
  const bhMetrics = useMemo(() => deriveBuyAndHoldMetrics(bhValues), [bhValues]);
  const excess = useMemo(() => {
    const eqLast = equityValues[equityValues.length - 1];
    const bhLast = bhValues[bhValues.length - 1];
    if (eqLast === undefined || bhLast === undefined) return null;
    return computeExcessReturn(eqLast, bhLast, initialCapital);
  }, [equityValues, bhValues, initialCapital]);

  const returnsRows: MetricRowSpec[] = [
    { label: "총 수익률", value: pct(m.total_return, true), tone: m.total_return >= 0 ? "bullish" : "bearish" },
    { label: "순이익 (절대)", value: usd(m.net_profit_abs, true), nullPolicy: "hide" },
    { label: "연환산 수익률 (CAGR)", value: pct(m.annual_return_pct, true) },
    { label: "평균 거래 수익률", value: pct(m.avg_trade_pct, true) },
    { label: "최고 거래", value: pct(m.best_trade_pct, true), tone: "bullish" },
    { label: "최악 거래", value: pct(m.worst_trade_pct, true), tone: "bearish" },
  ];

  const benchmarkingRows: MetricRowSpec[] = [
    {
      label: "전략 총 수익률",
      value: pct(strategyRange?.currentPct ?? m.total_return, true),
      tone: "bullish",
    },
    { label: "매수 후 보유 수익률", value: pct(bhMetrics?.returnPct, true) },
    {
      label: "전략 초과 수익",
      value:
        excess !== null
          ? `${usd(excess.abs, true) ?? "—"} (${pct(excess.pct, true) ?? "—"})`
          : null,
      tone: excess !== null && excess.abs >= 0 ? "bullish" : "bearish",
    },
    { label: "전략 최대 낙폭 (종가)", value: pct(m.max_drawdown), tone: "bearish" },
    { label: "매수 후 보유 최대 낙폭 (종가)", value: pct(bhMetrics?.maxDrawdownPct), tone: "bearish" },
  ];

  const riskRows: MetricRowSpec[] = [
    { label: "샤프 레이쇼", value: m.sharpe_ratio.toFixed(3), hint: "(bar 수익률 기준)" },
    { label: "소르티노 레이쇼", value: m.sortino_ratio?.toFixed(3) ?? null, hint: "(월간 수익률, RFR 2%)" },
    { label: "칼마 레이쇼", value: m.calmar_ratio?.toFixed(3) ?? null },
    { label: "최대 낙폭 (종가)", value: pct(m.max_drawdown), tone: "bearish" },
    {
      label: "최대 낙폭 지속",
      value: m.drawdown_duration != null ? `${m.drawdown_duration} bars` : null,
    },
  ];

  return (
    <section data-testid="detailed-results-section">
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview" className="data-active:text-[var(--primary)]">
            오버뷰
          </TabsTrigger>
          <TabsTrigger value="returns" className="data-active:text-[var(--primary)]">
            수익률
          </TabsTrigger>
          <TabsTrigger value="benchmarking" className="data-active:text-[var(--primary)]">
            벤치마킹
          </TabsTrigger>
          <TabsTrigger value="risk" className="data-active:text-[var(--primary)]">
            위험 조정 성과
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4 space-y-6">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiBlock
              label="오픈 PnL"
              value={usd(m.open_pnl, true) ?? "—"}
              tone={
                m.open_pnl != null && m.open_pnl !== 0
                  ? m.open_pnl > 0
                    ? "bullish"
                    : "bearish"
                  : "neutral"
              }
            />
            <KpiBlock
              label="기대 수익"
              value={usd(m.avg_trade_abs, true) ?? "—"}
              sub={pct(m.avg_trade_pct, true)}
              tone={
                m.avg_trade_abs != null
                  ? m.avg_trade_abs >= 0
                    ? "bullish"
                    : "bearish"
                  : "neutral"
              }
            />
            <KpiBlock
              label="전략 초과 수익"
              value={excess !== null ? (usd(excess.abs, true) ?? "—") : "—"}
              sub={excess !== null ? pct(excess.pct, true) : null}
              tone={
                excess !== null ? (excess.abs >= 0 ? "bullish" : "bearish") : "neutral"
              }
            />
            <KpiBlock
              label="샤프 레이쇼"
              value={m.sharpe_ratio.toFixed(3)}
              sub="(bar 수익률 기준)"
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div>
              <h3 className="mb-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
                수익 구조
              </h3>
              {/* trades 기반 비용 전(gross) 항등식 — BE net-기준 gross 필드는
                  수수료 별도 bar 와 이중 차감이라 waterfall 에 사용 금지. */}
              <ProfitWaterfall
                grossProfit={profitStructure?.grossProfit ?? null}
                grossLoss={profitStructure?.grossLoss ?? null}
                fees={profitStructure?.fees ?? null}
                slippage={profitStructure?.slippage ?? null}
                netProfit={profitStructure?.net ?? null}
              />
              {profitStructure !== null && tradesTruncated ? (
                <p className="mt-1 text-xs text-muted-foreground">
                  * 표본 {trades?.length ?? 0}건 기준 근사 (전체 거래는 CSV 확인).
                </p>
              ) : null}
            </div>
            <div>
              <h3 className="mb-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
                벤치마킹
              </h3>
              <BenchmarkFloatingBars strategyRange={strategyRange} bhRange={bhRange} />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="returns" className="mt-4 space-y-6">
          <MetricTable rows={returnsRows} />
          <div>
            <h3 className="mb-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
              월별 수익률
            </h3>
            <MonthlyReturnsHeatmap data={m.monthly_returns} />
          </div>
        </TabsContent>

        <TabsContent value="benchmarking" className="mt-4">
          <MetricTable
            rows={benchmarkingRows}
            caption="매수 후 보유 지표는 FE 계산 — Buy & Hold 커브(종가) 기반."
          />
        </TabsContent>

        <TabsContent value="risk" className="mt-4">
          <MetricTable rows={riskRows} />
        </TabsContent>
      </Tabs>
    </section>
  );
}
