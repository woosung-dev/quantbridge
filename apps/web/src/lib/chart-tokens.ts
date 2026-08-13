// 차트 색상 토큰 SSOT — globals.css CSS 변수를 차트 라이브러리용 실색상으로 해석
//
// lightweight-charts 는 `var()` 문자열 파싱 불가(colorStringToRgba throw) →
// getComputedStyle 로 해석한 hex/rgba 를 전달해야 한다. recharts/SVG 는 var()
// 문자열도 허용하지만 팔레트 일관성을 위해 동일 경로 사용.
// SSR/jsdom 폴백은 brand-palette.ts 다크 상수 — 앱 기본 테마가 다크라서
// 다크 폴백이 다수 사용자에게 무플래시 (라이트 사용자만 hydration 후 1회 flip).

"use client";

import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

import { BRAND_PALETTE } from "@/lib/brand-palette";

export interface ChartPalette {
  /** 상승/수익 (bullish) — per-point 히스토그램 등 */
  bullish: string;
  /** 하락/손실 (bearish) */
  bearish: string;
  /** equity 메인 라인 */
  equity: string;
  /** Buy & Hold 벤치마크 라인 */
  benchmark: string;
  /** Compare(다른 백테스트) 오버레이 라인 */
  compare: string;
  /** 축 텍스트 */
  axis: string;
  /** 그리드 라인 */
  grid: string;
  /** drawdown area 라인/상단/하단 */
  ddLine: string;
  ddTop: string;
  ddBottom: string;
}

/** globals.css `.dark` 토큰 값과 동일한 SSR/jsdom 폴백 (다크 디폴트 정합). */
export const CHART_PALETTE_FALLBACK: ChartPalette = {
  bullish: BRAND_PALETTE.dark.bullish,
  bearish: BRAND_PALETTE.dark.bearish,
  equity: BRAND_PALETTE.dark.chartEquity,
  benchmark: BRAND_PALETTE.dark.chartBenchmark,
  compare: BRAND_PALETTE.dark.chartCompare,
  axis: BRAND_PALETTE.dark.textMuted,
  grid: BRAND_PALETTE.dark.border,
  ddLine: BRAND_PALETTE.dark.ddLine,
  ddTop: BRAND_PALETTE.dark.ddTop,
  ddBottom: BRAND_PALETTE.dark.ddBottom,
};

/** document 루트에서 차트 팔레트 해석. 브라우저 전용 — SSR 은 폴백 반환. */
export function resolveChartTokens(): ChartPalette {
  if (typeof document === "undefined") {
    return CHART_PALETTE_FALLBACK;
  }
  const style = getComputedStyle(document.documentElement);
  const read = (name: string, fallback: string): string =>
    style.getPropertyValue(name).trim() || fallback;
  return {
    bullish: read("--bullish", CHART_PALETTE_FALLBACK.bullish),
    bearish: read("--bearish", CHART_PALETTE_FALLBACK.bearish),
    equity: read("--chart-equity", CHART_PALETTE_FALLBACK.equity),
    benchmark: read("--chart-benchmark", CHART_PALETTE_FALLBACK.benchmark),
    compare: read("--chart-compare", CHART_PALETTE_FALLBACK.compare),
    axis: read("--text-muted", CHART_PALETTE_FALLBACK.axis),
    grid: read("--border", CHART_PALETTE_FALLBACK.grid),
    ddLine: read("--chart-dd-line", CHART_PALETTE_FALLBACK.ddLine),
    ddTop: read("--chart-dd-top", CHART_PALETTE_FALLBACK.ddTop),
    ddBottom: read("--chart-dd-bottom", CHART_PALETTE_FALLBACK.ddBottom),
  };
}

// themeKey 별 해석 캐시 — useSyncExternalStore getSnapshot 의 stable identity 보장
// (매 렌더 새 객체 반환 시 무한 재렌더). 테마 토글 = themeKey 변경 → 재해석.
const paletteCache = new Map<string, ChartPalette>();

function getPaletteSnapshot(themeKey: string): ChartPalette {
  const cached = paletteCache.get(themeKey);
  if (cached !== undefined) {
    return cached;
  }
  const resolved = resolveChartTokens();
  paletteCache.set(themeKey, resolved);
  return resolved;
}

// 외부 store 구독 불필요 — 테마 토글은 useTheme 재렌더가 트리거.
const emptySubscribe = () => () => {};

/**
 * 테마 인지 차트 팔레트 훅 — 테마 토글 시 재해석 (SSR = 폴백, hydration 후 실값).
 * setState-in-effect 금지(H-1/react-hooks lint) → useSyncExternalStore 패턴.
 */
export function useChartTheme(): ChartPalette {
  const { resolvedTheme } = useTheme();
  const themeKey = resolvedTheme === "dark" ? "dark" : "light";
  return useSyncExternalStore(
    emptySubscribe,
    () => getPaletteSnapshot(themeKey),
    () => CHART_PALETTE_FALLBACK,
  );
}
