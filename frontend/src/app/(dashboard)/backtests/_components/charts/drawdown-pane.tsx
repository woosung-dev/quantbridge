// Sprint 32-B (BL-170): DrawdownPane — 하단 pane (underwater plot). Drawdown(빨간 영역)을 표시.
// ui-ux-pro-max 진단 P0 #3/#5 (Drawdown 매핑 모호, 거래
// 마커 약자 의미 0 — 본 PR 은 시각 분리만, 마커 의미 명시는 Worker C 영역).
//
// Y축은 % (0 ~ -100% 일반, leverage 시 -200% 가능 — BL-156 Worker D 영역에서
// vectorbt MDD 수학 검증 후 leverage 가정 강조 처리).
//
// BL-407: lightweight-charts v4 의 priceFormat=percent 는 값에 ×100 하지 않고
// '%' 만 붙인다 (-30 입력 = "-30%" — 이미 %단위 값을 기대). 여기에 percent 타입은
// precision 이 priceScale 눈금 양자화로 새어 들어가 0 ~ -1 비율 입력 시 눈금이
// 전부 "-0.1%" 로 붕괴한다 (minMove 는 percent 타입에서 무시됨).
// → type=custom formatter 로 데이터는 비율(0 ~ -1) 유지, 라벨에서만 ×100
//   (-0.30 → "-30.00%"). lastValueVisible 라벨도 동일 series formatter 를 탄다.

"use client";

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
// BL-407: 비율(0 ~ -1) → % 라벨 변환 formatter (line/area 공용, identity 고정).
const DD_PERCENT_FORMATTER = (p: number) => `${(p * 100).toFixed(2)}%`;

const DD_LINE_OPTIONS: LineSeriesPartialOptions = {
  color: CHART_PALETTE_FALLBACK.ddLine,
  lineWidth: 1,
  priceFormat: {
    type: "custom",
    formatter: DD_PERCENT_FORMATTER,
    minMove: 0.0001,
  },
  priceLineVisible: false,
  lastValueVisible: true,
};

const DD_AREA_OPTIONS = {
  lineWidth: 1 as const,
  priceFormat: {
    type: "custom" as const,
    formatter: DD_PERCENT_FORMATTER,
    minMove: 0.0001,
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
