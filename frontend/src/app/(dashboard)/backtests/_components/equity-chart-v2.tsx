"use client";

// Sprint 30-β (W2): EquityChartV2 — lightweight-charts 기반 equity curve.
// Sprint 32-B (BL-169 + BL-170): 2-pane split (Equity top + Drawdown bottom)
//   + ChartLegend + Worker C marker hook (extraMarkers prop).
// 기존 equity-chart.tsx (recharts) 는 보존 (rollback path). 신규 차트만 lightweight-charts.
// ADR: docs/dev-log/2026-05-05-sprint30-chart-lib-decision.md
//
// ui-ux-pro-max 진단 (dogfood Day 4 = 5/10) 해소:
// - P0 #1 Y축 단위 모호 (-9855.71 USDT vs %) → Equity pane = 통화 / Drawdown pane = % 명확 분리
// - P0 #2 3 series 시각 구분 불가 → Legend + LineStyle (solid/dashed/area) 명시
// - P0 #3 Drawdown -30000 vs KPI -343.15% 매핑 모호 → Drawdown pane Y축 % only
// - P0 #4 Legend 부재 → ChartLegend inline (top-right)
// - P0 #5 거래 마커 약자 의미 0 → Worker C (BL-171/172) 후속, 본 PR 은 hook 만 노출
// - P0 #6 Y축 dual scale 부재 → 2-pane 으로 자연스러운 dual scale (각 pane 독립 priceScale)
//
// Marker hook (Worker C 의존):
// - `extraMarkers` prop 으로 외부에서 marker 주입 가능
// - 자동 계산된 trade markers + extraMarkers 가 merge 됨
// - Worker C 는 본 PR 머지 후 rebase 하여 MarkerLayer 만 추가 (충돌 X)

import { useMemo } from "react";

import type {
  ChartMarker,
  ChartPoint,
} from "@/components/charts/trading-chart";
import type { EquityPoint, TradeItem } from "@/features/backtest/schemas";
import { computeBuyAndHold } from "@/features/backtest/utils";

import { ChartLegend } from "./chart-legend";
import { DrawdownPane } from "./drawdown-pane";
import { EquityPane } from "./equity-pane";

// 차트 마커 cap — TRADE_LIMIT 정합 (trade-table 의 200건 cap 과 동일 의미).
const MARKER_LIMIT = 200;

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

  const tradeMarkers = useMemo<ChartMarker[]>(() => {
    if (trades === undefined || trades.length === 0) return [];
    const capped = trades.slice(0, MARKER_LIMIT);
    const out: ChartMarker[] = [];
    for (const trade of capped) {
      // entry marker.
      out.push({
        time: trade.entry_time,
        position: trade.direction === "long" ? "belowBar" : "aboveBar",
        color: trade.direction === "long" ? "#22c55e" : "#ef4444",
        shape: trade.direction === "long" ? "arrowUp" : "arrowDown",
        text: trade.direction === "long" ? "L" : "S",
      });
      // exit marker (closed only).
      if (trade.status === "closed" && trade.exit_time !== null) {
        out.push({
          time: trade.exit_time,
          position: "inBar",
          color: "#94a3b8",
          shape: "circle",
          text: "X",
        });
      }
    }
    return out;
  }, [trades]);

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
      </div>

      {showDrawdown && (
        <div data-testid="drawdown-pane-wrapper">
          <DrawdownPane drawdownData={drawdownData} height={bottomHeight} />
        </div>
      )}
    </div>
  );
}
