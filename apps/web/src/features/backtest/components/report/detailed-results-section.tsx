"use client";

// 심화 분석 — variant-c 에 없는 현행 분석 시각을 C 섹션 언어로 보존 배치한 카드 묶음.
// 수익 구조(waterfall) / 벤치마킹(strategy vs B&H 범위 막대) / 월별 수익률(heatmap) 3장.
// 지표 수치 자체는 03 상세 지표(.metric-groups)가 담당하므로 여기서는 시각만 남긴다.
// (이전 shadcn 서브탭 4종 + 중복 지표 표는 metric-groups 로 이관, IA 를 variant-c 구조로 재편.)

import { useMemo } from "react";

import {
  computeCurveRange,
  computeProfitStructure,
} from "@/features/backtest/analytics";
import type {
  BacktestMetricsOut,
  EquityPoint,
  TradeItem,
} from "@/features/backtest/schemas";

import { MonthlyReturnsHeatmap } from "@/features/backtest/components/charts/monthly-returns-heatmap";
import { BenchmarkFloatingBars } from "@/features/backtest/components/report/benchmark-floating-bars";
import { ProfitWaterfall } from "@/features/backtest/components/report/profit-waterfall";

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

export function DetailedResultsSection({
  metrics: m,
  equityCurve,
  buyAndHoldCurve,
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

  return (
    <div className="report-analysis-grid" data-testid="detailed-results-section">
      <div className="card">
        <div className="card-head">
          <div>
            <h3 className="card-title">수익 구조</h3>
            <p className="card-sub">총 이익에서 총 손실·비용을 차감한 순손익 분해입니다.</p>
          </div>
        </div>
        <div className="card-body">
          <ProfitWaterfall
            grossProfit={profitStructure?.grossProfit ?? null}
            grossLoss={profitStructure?.grossLoss ?? null}
            fees={profitStructure?.fees ?? null}
            slippage={profitStructure?.slippage ?? null}
            netProfit={profitStructure?.net ?? null}
          />
          {profitStructure !== null && tradesTruncated ? (
            <p className="card-sub" style={{ marginTop: 8 }}>
              표본 {trades?.length ?? 0}건 기준 근사입니다. 전체 거래는 CSV 로 확인하세요.
            </p>
          ) : null}
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h3 className="card-title">벤치마킹</h3>
            <p className="card-sub">전략과 매수 후 보유의 최고·현재·최저 수익률 범위를 겹쳐 봅니다.</p>
          </div>
        </div>
        <div className="card-body">
          <BenchmarkFloatingBars strategyRange={strategyRange} bhRange={bhRange} />
        </div>
      </div>

      <div className="card report-analysis-wide">
        <div className="card-head">
          <div>
            <h3 className="card-title">월별 수익률</h3>
            <p className="card-sub">월별 수익 분포입니다. 값이 없는 달은 빈 칸으로 둡니다.</p>
          </div>
        </div>
        <div className="card-body">
          <MonthlyReturnsHeatmap data={m.monthly_returns} />
        </div>
      </div>
    </div>
  );
}
