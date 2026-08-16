// 대시보드 자산 곡선(합산 실현 손익, USDT) 차트 축 계약 SSOT — S8 이 이 패턴을 따른다.
//
// 이 곡선의 값은 활성 세션의 누적 실현 손익(USDT 절대값, 0 근방에서 시작)이다.
// 절대 통화값이므로 축은 반드시 선형(Normal)이어야 하고, 라벨 포매터는 값에
// 어떤 배율도 곱이지 않아야 한다.
//
// BL-407 실증 배경. lightweight-charts v4 는
//   - priceFormat.type="percent" 를 써도 값에 ×100 하지 않고 '%' 만 붙인다
//     (0.05 입력 → "0.05%"). 퍼센트를 원하면 custom formatter 에서 직접 ×100 해야 한다
//     (drawdown-pane.tsx 가 그 경우다 — 비율 데이터라 의도적으로 ×100).
//   - percent 타입은 minMove 를 무시하고 precision 을 priceScale 눈금으로 양자화한다.
// 이 곡선은 반대 상황이다. 데이터가 이미 USDT 절대값이라 어떤 배율도 곱이면 안 된다.
// 그래서 type="custom" + 배율 없는 formatter 로 못박고, 아래 단위 테스트가 이를 동결한다.

import type { LineSeriesPartialOptions } from "lightweight-charts";

import { CHART_PALETTE_FALLBACK } from "@/lib/chart-tokens";

/**
 * lightweight-charts v4 `PriceScaleMode` 매핑. 런타임 enum 을 import 하면 모듈이
 * 캔버스 의존 모듈을 끌어오므로, 계약을 numeric 상수로 못박는다.
 * (Normal=0, Logarithmic=1, Percentage=2, IndexedTo100=3)
 */
export const PRICE_SCALE_MODE = {
  NORMAL: 0,
  LOGARITHMIC: 1,
  PERCENTAGE: 2,
  INDEXED_TO_100: 3,
} as const;

/** 자산 곡선 축의 계약 모드 — 절대 통화값이므로 선형(Normal) 고정. */
export const EQUITY_PRICE_SCALE_MODE = PRICE_SCALE_MODE.NORMAL;

/** 절대값 곡선에서 금지되는 축 모드 — 값을 왜곡(로그·백분율 재정규화)한다. */
export const FORBIDDEN_EQUITY_SCALE_MODES: readonly number[] = [
  PRICE_SCALE_MODE.LOGARITHMIC,
  PRICE_SCALE_MODE.PERCENTAGE,
  PRICE_SCALE_MODE.INDEXED_TO_100,
];

/**
 * 자산 곡선 y축 라벨 포매터. USDT 절대값을 천단위 구분 + 소수 2자리로 찍는다.
 * ★배율을 곱이지 않는다 — 입력값이 그대로 라벨 숫자다 (BL-407 의 percent 함정 회피).
 * lightweight-charts 의 axis tick·crosshair·lastValue 라벨이 모두 이 함수를 탄다.
 */
export function formatEquityAxis(value: number): string {
  if (!Number.isFinite(value)) {
    return "0.00";
  }
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/**
 * 자산 곡선 라인 series 옵션 — 렌더 간 identity 고정(성능: TradingChart data effect 재실행 차단).
 * 색은 chart-tokens SSOT(폴백 = globals.css --chart-equity 동일값).
 * priceFormat.type 은 절대 "percent" 가 아니다 — 배율 없는 custom formatter 로 못박는다.
 */
export const EQUITY_LINE_OPTIONS: LineSeriesPartialOptions = {
  color: CHART_PALETTE_FALLBACK.equity,
  lineWidth: 2,
  priceLineVisible: false,
  lastValueVisible: true,
  priceFormat: {
    type: "custom",
    formatter: formatEquityAxis,
    minMove: 0.01,
  },
};
