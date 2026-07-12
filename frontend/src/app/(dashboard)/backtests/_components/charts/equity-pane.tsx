"use client";

// Sprint 32-B (BL-169): EquityPane — top pane.
// Equity (solid, --chart-equity) + Buy & Hold (dashed, --chart-benchmark) line series.
//
// Y축은 통화(USDT) 단위로 표시 (precision=2). 소수 % 기준은 계산 비용 + BE 계약상
// equity_curve 가 자본금(USDT) 단위라 그대로 표시. 단위 모호 해소는 ChartLegend
// + section heading + ariaLabel 의 명시적 설명으로 보강.
//
// LESSON-004 준수 + 성능: 이전 구현의 `[...data]` spread/inline object 가 부모
// 리렌더마다 새 identity 를 만들어 TradingChart data effect(setData) 를 매번
// 재실행시켰다 → readonly 배열 직접 전달 + module const options + useMemo 오버레이.

import { useMemo } from "react";

import {
  TradingChart,
  type ChartMarker,
  type ChartPoint,
} from "@/components/charts/trading-chart";
import type { LineSeriesPartialOptions } from "lightweight-charts";

interface EquityPaneProps {
  /** Equity (자본 곡선) 데이터. ascending time. */
  equityData: readonly ChartPoint[];
  /** Buy & Hold 벤치마크. 빈 배열이면 series 미표시. */
  benchmarkData: readonly ChartPoint[];
  /** 거래 마커 (entry/exit). 빈 배열이면 마커 미표시. */
  markers: readonly ChartMarker[];
  /** Compare 오버레이 (다른 백테스트). 빈/미지정이면 미표시. */
  compareData?: readonly ChartPoint[];
  /** Pane 높이 (px). */
  height: number;
  /** a11y 라벨 오버라이드 (Compare/% 모드 시 갱신). */
  ariaLabel?: string;
}

// 정적 옵션 — 렌더 간 identity 고정 (색상은 TradingChart 기본 palette.equity).
const EQUITY_LINE_OPTIONS: LineSeriesPartialOptions = {
  lineWidth: 2,
  priceFormat: {
    type: "price",
    precision: 2,
    minMove: 0.01,
  },
};

export function EquityPane({
  equityData,
  benchmarkData,
  markers,
  compareData,
  height,
  ariaLabel,
}: EquityPaneProps) {
  const benchmark = useMemo(
    () => (benchmarkData.length > 0 ? { data: benchmarkData } : undefined),
    [benchmarkData],
  );
  const compare = useMemo(
    () =>
      compareData !== undefined && compareData.length > 0
        ? { data: compareData }
        : undefined,
    [compareData],
  );

  return (
    <TradingChart
      data={equityData}
      markers={markers}
      benchmark={benchmark}
      compare={compare}
      options={EQUITY_LINE_OPTIONS}
      height={height}
      ariaLabel={
        ariaLabel ??
        "자본 곡선 (Equity, 실선 코퍼) 및 Buy and Hold 벤치마크 (점선 파란색) 비교 — 단위는 PnL (USDT, 시작=0)"
      }
    />
  );
}
