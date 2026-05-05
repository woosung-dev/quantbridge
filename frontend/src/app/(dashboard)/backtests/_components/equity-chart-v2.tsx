"use client";

// Sprint 30-β (W2): EquityChartV2 — lightweight-charts 기반 equity curve.
// Sprint 32-B (BL-169 + BL-170): 2-pane split (Equity top + Drawdown bottom)
//   + ChartLegend + Worker C marker hook (extraMarkers prop).
// Sprint 32-C (BL-171 + BL-172): MarkerLayer (의미 있는 trade markers) +
//   AxisLabelBar (Y축/X축 라벨) — ui-ux-pro-max P0 #1 + #5 해소.
// 기존 equity-chart.tsx (recharts) 는 보존 (rollback path). 신규 차트만 lightweight-charts.
// ADR: docs/dev-log/2026-05-05-sprint30-chart-lib-decision.md
//
// ui-ux-pro-max 진단 (dogfood Day 4 = 5/10) 해소:
// - P0 #1 Y축 단위 모호 (-9855.71 USDT vs %) → AxisLabelBar 로 Y/X 축 단위 명시
//   + DrawdownPane mddExceedsCapital 시 leverage warning inline
// - P0 #2 3 series 시각 구분 불가 → Legend + LineStyle (solid/dashed/area) 명시
// - P0 #3 Drawdown -30000 vs KPI -343.15% 매핑 모호 → Drawdown pane Y축 % only
// - P0 #4 Legend 부재 → ChartLegend inline (top-right)
// - P0 #5 거래 마커 약자 의미 0 → MarkerLayer 가 "L $price" / "+1.23%" 등
//   의미 있는 text + shape (arrow=entry, circle=exit) + 색상 (PnL 부호) 표시
// - P0 #6 Y축 dual scale 부재 → 2-pane 으로 자연스러운 dual scale (각 pane 독립 priceScale)

import { useMemo } from "react";

import type {
  ChartMarker,
  ChartPoint,
} from "@/components/charts/trading-chart";
import type { EquityPoint, TradeItem } from "@/features/backtest/schemas";
import { computeBuyAndHold } from "@/features/backtest/utils";

import { AxisLabelBar } from "./axis-label-bar";
import { ChartLegend } from "./chart-legend";
import { DrawdownPane } from "./drawdown-pane";
import { EquityPane } from "./equity-pane";
import { deriveTradeMarkers } from "./marker-layer";

// 2-pane 비율 (ui-ux-pro-max 권장 60/40).
const TOP_PANE_RATIO = 0.6;
const BOTTOM_PANE_RATIO = 0.4;

interface EquityChartV2Props {
  equityCurve: readonly EquityPoint[];
  trades?: readonly TradeItem[];
  initialCapital: number;
  /** 전체 차트 영역 높이 (top + bottom 합계). default 360. */
  height?: number;
  /**
   * Worker C marker hook — 외부에서 추가 markers 주입.
   * 자동 계산된 trade markers 와 merge 됨.
   * 본 PR 은 hook point 만 정의 — Worker C (BL-171/172) 가 의미 있는 마커 추가.
   */
  extraMarkers?: readonly ChartMarker[];
  /**
   * Sprint 32-C BL-172: candle 단위 (예: "1h", "1d", "15m"). X축 라벨에 표시.
   * 미지정 시 X축 라벨에 단위 미표시 (그래도 X축 단위 = "시간" 만 안내).
   */
  timeframe?: string;
  /**
   * Sprint 32-C BL-172: BL-156 메타 (`metrics.mdd_exceeds_capital`) pass-through.
   * true 면 DrawdownPane Y축 라벨에 leverage warning inline.
   */
  mddExceedsCapital?: boolean | null;
}

interface DrawdownPoint {
  timestamp: string;
  value: number;
}

/**
 * equity_curve 만으로 drawdown 계산.
 * - peak = running max
 * - drawdown = (current - peak) / peak (음수, 0..-1)
 *
 * NOTE: backend 가 drawdown_curve 를 별도 응답하면 그것을 우선 사용해야 함.
 * 본 컴포넌트는 BE drawdown_curve 부재 시 자체 계산 fallback.
 * BL-156 (Worker D) MDD 수학 검증 시 본 fallback 도 보완 대상.
 */
function computeDrawdownArea(
  curve: readonly EquityPoint[],
): DrawdownPoint[] {
  if (curve.length === 0) return [];
  const out: DrawdownPoint[] = [];
  let peak = curve[0]!.value;
  for (const point of curve) {
    if (!Number.isFinite(point.value)) continue;
    if (point.value > peak) peak = point.value;
    const dd = peak > 0 ? (point.value - peak) / peak : 0; // 음수
    out.push({ timestamp: point.timestamp, value: dd });
  }
  return out;
}

export function EquityChartV2({
  equityCurve,
  trades,
  initialCapital,
  height = 360,
  extraMarkers,
  timeframe,
  mddExceedsCapital,
}: EquityChartV2Props) {
  const equityData = useMemo<ChartPoint[]>(
    () =>
      equityCurve.map((p) => ({
        time: p.timestamp,
        value: p.value,
      })),
    [equityCurve],
  );

  const benchmarkData = useMemo<ChartPoint[]>(() => {
    const bh = computeBuyAndHold(equityCurve, initialCapital);
    return bh.map((p) => ({ time: p.timestamp, value: p.value }));
  }, [equityCurve, initialCapital]);

  const drawdownData = useMemo<ChartPoint[]>(() => {
    return computeDrawdownArea(equityCurve).map((p) => ({
      time: p.timestamp,
      value: p.value,
    }));
  }, [equityCurve]);

  // Sprint 32-C BL-171: deriveTradeMarkers 사용. 이전 inline 변환 코드 대체.
  const tradeMarkers = useMemo<ChartMarker[]>(
    () => deriveTradeMarkers(trades),
    [trades],
  );

  // Worker C hook — extraMarkers 가 있으면 자동 계산된 마커와 merge.
  const mergedMarkers = useMemo<ChartMarker[]>(() => {
    if (extraMarkers === undefined || extraMarkers.length === 0) {
      return tradeMarkers;
    }
    return [...tradeMarkers, ...extraMarkers];
  }, [tradeMarkers, extraMarkers]);

  if (equityCurve.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        Equity 데이터가 없습니다
      </div>
    );
  }

  // 2-pane 분리 (top: 60% / bottom: 40%). 각 pane 은 독립 chart 인스턴스
  // → Y축 priceScale 자연스럽게 분리. 단위 모호 문제 해소.
  const topHeight = Math.round(height * TOP_PANE_RATIO);
  const bottomHeight = Math.round(height * BOTTOM_PANE_RATIO);
  const showBenchmark = benchmarkData.length > 0;
  const showDrawdown = drawdownData.length > 0;

  return (
    <div
      className="space-y-2"
      data-testid="equity-chart-v2"
      role="group"
      aria-label="백테스트 자본 곡선 + Buy and Hold 비교 + Drawdown 차트"
    >
      <ChartLegend
        showBenchmark={showBenchmark}
        showDrawdown={showDrawdown}
      />

      <div data-testid="equity-pane-wrapper">
        <EquityPane
          equityData={equityData}
          benchmarkData={benchmarkData}
          markers={mergedMarkers}
          height={topHeight}
        />
        <AxisLabelBar
          yAxisLabel="USDT (자본금)"
          xAxisLabel={
            timeframe !== undefined && timeframe !== ""
              ? `시간 · ${timeframe} 단위 캔들`
              : "시간"
          }
          variant="equity"
        />
      </div>

      {showDrawdown && (
        <div data-testid="drawdown-pane-wrapper">
          <DrawdownPane drawdownData={drawdownData} height={bottomHeight} />
          <AxisLabelBar
            yAxisLabel={
              mddExceedsCapital === true
                ? "% (자본 대비 손실 · leverage 시 -100% 초과 가능)"
                : "% (자본 대비 손실 · 0 ~ -100%)"
            }
            xAxisLabel={
              timeframe !== undefined && timeframe !== ""
                ? `시간 · ${timeframe} 단위 캔들`
                : "시간"
            }
            variant="drawdown"
          />
        </div>
      )}
    </div>
  );
}
