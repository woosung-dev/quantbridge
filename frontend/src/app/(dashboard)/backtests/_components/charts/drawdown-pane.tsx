"use client";

// Sprint 32-B (BL-170): DrawdownPane — bottom pane (underwater plot).
// Drawdown (red area). ui-ux-pro-max 진단 P0 #3/#5 (Drawdown 매핑 모호, 거래
// 마커 약자 의미 0 — 본 PR 은 시각 분리만, 마커 의미 명시는 Worker C 영역).
//
// Y축은 % (0 ~ -100% 일반, leverage 시 -200% 가능 — BL-156 Worker D 영역에서
// vectorbt MDD 수학 검증 후 leverage 가정 강조 처리). priceFormat=percent 로
// lightweight-charts 가 자동 % 라벨링.
//
// 데이터: drawdown 값은 0 ~ -1 (음수 비율). priceFormat=percent 는 1=100% 가정
// 하므로 그대로 입력. 즉 -0.30 → "-30.00%" 라벨링.

import { useMemo } from "react";

import {
  TradingChart,
  type ChartPoint,
} from "@/components/charts/trading-chart";
import { CHART_PALETTE_FALLBACK } from "@/lib/chart-tokens";
import type { LineSeriesPartialOptions } from "lightweight-charts";

// 정적 옵션 — 렌더 간 identity 고정 (성능: TradingChart data effect 재실행 차단).
// 색상은 chart-tokens 폴백(= globals.css --chart-dd-* 동일값). area 색은
// TradingChart 기본 palette 가 담당.
const DD_LINE_OPTIONS: LineSeriesPartialOptions = {
  color: CHART_PALETTE_FALLBACK.ddLine,
  lineWidth: 1,
  priceFormat: {
    type: "percent",
    precision: 2,
    minMove: 0.01,
  },
  priceLineVisible: false,
  lastValueVisible: true,
};

const DD_AREA_OPTIONS = {
  lineWidth: 1 as const,
  priceFormat: {
    type: "percent" as const,
    precision: 2,
    minMove: 0.01,
  },
};

interface DrawdownPaneProps {
  /** Drawdown 데이터 — 0 ~ -1 (음수 비율). 빈 배열이면 컴포넌트가 fallback 처리. */
  drawdownData: readonly ChartPoint[];
  /** Pane 높이 (px). */
  height: number;
}

export function DrawdownPane({ drawdownData, height }: DrawdownPaneProps) {
  if (drawdownData.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-xs text-muted-foreground"
        style={{ height }}
      >
        Drawdown 데이터가 없습니다
      </div>
    );
  }

  return <DrawdownChart drawdownData={drawdownData} height={height} />;
}

function DrawdownChart({
  drawdownData,
  height,
}: {
  drawdownData: readonly ChartPoint[];
  height: number;
}) {
  // area 오버레이 — identity 를 drawdownData 에 고정 (spread 재생성 금지).
  const area = useMemo(
    () => ({ data: drawdownData, options: DD_AREA_OPTIONS }),
    [drawdownData],
  );
  return (
    <TradingChart
      // main line series 는 area 라인과 동일 색 placeholder (last value 라벨용).
      data={drawdownData}
      options={DD_LINE_OPTIONS}
      area={area}
      height={height}
      ariaLabel="Drawdown (손실 폭) — 빨간 영역. 단위는 퍼센트 (음수). 0 은 신고가 회복, 음수가 클수록 깊은 낙폭"
    />
  );
}
