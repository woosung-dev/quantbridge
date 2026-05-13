"use client";

// Sprint 32-B (BL-169): EquityPane — top pane.
// Equity (solid green) + Buy & Hold (dashed blue) line series.
// ui-ux-pro-max 진단 P0 #2/#3 (3 series 시각 구분 불가, Y축 단위 모호) 부분 해소.
//
// Y축은 통화(USDT) 단위로 표시 (precision=2). 소수 % 기준은 계산 비용 + BE 계약상
// equity_curve 가 자본금(USDT) 단위라 그대로 표시. 단위 모호 해소는 ChartLegend
// + section heading + ariaLabel 의 명시적 설명으로 보강.
//
// LESSON-004 준수: useMemo 로 stable identity 유지. useEffect dep 에 unstable
// object 직접 지정 안 함 (TradingChart 내부에서 처리).

import {
  TradingChart,
  type ChartMarker,
  type ChartPoint,
} from "@/components/charts/trading-chart";

interface EquityPaneProps {
  /** Equity (자본 곡선) 데이터. ascending time. */
  equityData: readonly ChartPoint[];
  /** Buy & Hold 벤치마크. 빈 배열이면 series 미표시. */
  benchmarkData: readonly ChartPoint[];
  /** 거래 마커 (entry/exit). 빈 배열이면 마커 미표시. */
  markers: readonly ChartMarker[];
  /** Pane 높이 (px). */
  height: number;
}

export function EquityPane({
  equityData,
  benchmarkData,
  markers,
  height,
}: EquityPaneProps) {
  return (
    <TradingChart
      data={[...equityData]}
      markers={[...markers]}
      benchmark={
        benchmarkData.length > 0 ? { data: [...benchmarkData] } : undefined
      }
      options={{
        color: "#22c55e",
        lineWidth: 2,
        priceFormat: {
          type: "price",
          precision: 2,
          minMove: 0.01,
        },
      }}
      height={height}
      ariaLabel="자본 곡선 (Equity, 실선 녹색) 및 Buy and Hold 벤치마크 (점선 파란색) 비교 — 단위는 PnL (USDT, 시작=0)"
    />
  );
}
