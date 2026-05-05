"use client";

// Sprint 30-β (W2): EquityChartV2 — lightweight-charts 기반 equity curve.
// 기존 equity-chart.tsx (recharts) 는 보존 (rollback path). 신규 차트만 lightweight-charts.
// ADR: docs/dev-log/2026-05-05-sprint30-chart-lib-decision.md

import { useMemo } from "react";

import {
  TradingChart,
  type ChartMarker,
  type ChartPoint,
} from "@/components/charts/trading-chart";
import type { EquityPoint, TradeItem } from "@/features/backtest/schemas";
import { computeBuyAndHold } from "@/features/backtest/utils";

// 차트 마커 cap — TRADE_LIMIT 정합 (trade-table 의 200건 cap 과 동일 의미).
const MARKER_LIMIT = 200;

interface EquityChartV2Props {
  equityCurve: readonly EquityPoint[];
  trades?: readonly TradeItem[];
  initialCapital: number;
  height?: number;
}

interface DrawdownPoint {
  timestamp: string;
  value: number;
}

/**
 * equity_curve 만으로 drawdown 계산.
 * - peak = running max
 * - drawdown = (current - peak) / peak (음수, 0..-1)
 * - lightweight-charts area series 는 양수만 표시 좋아하므로 abs 변환.
 *
 * NOTE: backend 가 drawdown_curve 를 별도 응답하면 그것을 우선 사용해야 함.
 * 본 컴포넌트는 BE drawdown_curve 부재 시 자체 계산 fallback.
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
}: EquityChartV2Props) {
  const equityData = useMemo<ChartPoint[]>(
    () =>
      equityCurve.map((p) => ({
        time: p.timestamp,
        value: p.value,
      })),
    [equityCurve],
  );

  const benchmark = useMemo<ChartPoint[]>(() => {
    const bh = computeBuyAndHold(equityCurve, initialCapital);
    return bh.map((p) => ({ time: p.timestamp, value: p.value }));
  }, [equityCurve, initialCapital]);

  const drawdown = useMemo<ChartPoint[]>(() => {
    return computeDrawdownArea(equityCurve).map((p) => ({
      time: p.timestamp,
      value: p.value,
    }));
  }, [equityCurve]);

  const markers = useMemo<ChartMarker[]>(() => {
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

  if (equityCurve.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        Equity 데이터가 없습니다
      </div>
    );
  }

  return (
    <TradingChart
      data={equityData}
      markers={markers}
      benchmark={benchmark.length > 0 ? { data: benchmark } : undefined}
      area={drawdown.length > 0 ? { data: drawdown } : undefined}
      height={height}
      ariaLabel="백테스트 자산곡선 + Buy&Hold 비교 + 거래 마커"
    />
  );
}
