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

import {
  TradingChart,
  type ChartPoint,
} from "@/components/charts/trading-chart";

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

  return (
    <TradingChart
      // main line series 는 invisible — drawdown 이 area 에 들어가므로
      // line series 는 placeholder. lineWidth=0 + transparent 색상으로 hide.
      data={[...drawdownData]}
      options={{
        color: "rgba(239, 68, 68, 0.55)",
        lineWidth: 1,
        priceFormat: {
          type: "percent",
          precision: 2,
          minMove: 0.01,
        },
        priceLineVisible: false,
        lastValueVisible: true,
      }}
      area={{
        data: [...drawdownData],
        options: {
          topColor: "rgba(239, 68, 68, 0.35)",
          bottomColor: "rgba(239, 68, 68, 0.02)",
          lineColor: "rgba(239, 68, 68, 0.55)",
          lineWidth: 1,
          priceFormat: {
            type: "percent",
            precision: 2,
            minMove: 0.01,
          },
        },
      }}
      height={height}
      ariaLabel="Drawdown (손실 폭) — 빨간 영역. 단위는 퍼센트 (음수). 0 은 신고가 회복, 음수가 클수록 깊은 낙폭"
    />
  );
}
