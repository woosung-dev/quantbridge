"use client";

// Sprint 30-β (W2): lightweight-charts wrapper.
// PRD §Phase 1 주 4 spec 정합 — 점진적 도입 (ADR docs/dev-log/2026-05-05-sprint30-chart-lib-decision.md).
// recharts 보존, 신규 차트만 lightweight-charts.
//
// LESSON-004 준수:
// - useEffect dep 에 RQ/Zustand 결과 객체나 unstable function ref 사용 금지.
// - render body 에서 ref.current = value 대입 금지 (H-3 의무).
// - chart instance 보관은 useEffect 안 (init effect 1회 + cleanup) 에서만.
// - Strict Mode 더블 invoke 방어: cleanup 에서 chart.remove() + observer.disconnect() 모두 실행.

import { useTheme } from "next-themes";
import { useEffect, useRef } from "react";
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type LineSeriesPartialOptions,
  type LineData,
  type AreaSeriesPartialOptions,
  type AreaData,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";

/**
 * 단순화된 시계열 포인트.
 * - time: ISO datetime 문자열 또는 epoch seconds(number) 모두 허용 → 내부에서 UTCTimestamp 로 정규화.
 * - value: 표시할 숫자값 (equity / B&H / drawdown 등 시리즈에 따라 의미 다름).
 */
export interface ChartPoint {
  time: string | number;
  value: number;
}

/** 거래 마커 — entry/exit 표시용. */
export interface ChartMarker {
  time: string | number;
  position: "aboveBar" | "belowBar" | "inBar";
  color: string;
  shape: "circle" | "square" | "arrowUp" | "arrowDown";
  text?: string;
}

/** equity 추가 영역 series 옵션 — drawdown 등 area 보조 서브시리즈. */
export interface AreaOverlay {
  data: ChartPoint[];
  options?: AreaSeriesPartialOptions;
}

export interface TradingChartProps {
  /** 메인 line series 데이터 (예: equity curve). */
  data: ChartPoint[];
  /** 메인 series 옵션 (색상 등). */
  options?: LineSeriesPartialOptions;
  /** 거래 마커 (entry/exit 등). */
  markers?: ChartMarker[];
  /** 비교용 보조 line (예: B&H benchmark). */
  benchmark?: { data: ChartPoint[]; options?: LineSeriesPartialOptions };
  /** 두 번째 비교 line (예: 다른 백테스트 Compare 오버레이). benchmark 와 독립. */
  compare?: { data: ChartPoint[]; options?: LineSeriesPartialOptions };
  /** 영역 오버레이 (예: drawdown area). */
  area?: AreaOverlay;
  /** 차트 높이. */
  height?: number;
  /** 접근성 라벨 (a11y 의무). */
  ariaLabel: string;
}

// --- helpers --------------------------------------------------------------

/**
 * lightweight-charts Time 직렬화 정규화.
 * - 문자열(ISO) → epoch seconds 변환.
 * - 숫자 → 그대로 (이미 epoch seconds 라고 가정).
 *
 * NOTE: lightweight-charts 는 number 입력 시 UTCTimestamp(seconds) 로 해석.
 * `Date.parse / 1000` 으로 통일.
 */
function toTime(value: string | number): Time {
  if (typeof value === "number") {
    return value as UTCTimestamp;
  }
  const ms = Date.parse(value);
  if (Number.isNaN(ms)) {
    return 0 as UTCTimestamp;
  }
  return Math.floor(ms / 1000) as UTCTimestamp;
}

function toLineData(points: readonly ChartPoint[]): LineData[] {
  // time ascending 정렬 의무 (lightweight-charts 가정 — 위반 시 throw).
  const mapped: LineData[] = points.map((p) => ({
    time: toTime(p.time),
    value: p.value,
  }));
  mapped.sort((a, b) => Number(a.time) - Number(b.time));
  // 동일 time 중복 제거 (lightweight-charts 가 throw 함).
  const seen = new Set<number>();
  const out: LineData[] = [];
  for (const point of mapped) {
    const t = Number(point.time);
    if (seen.has(t)) continue;
    seen.add(t);
    out.push(point);
  }
  return out;
}

function toAreaData(points: readonly ChartPoint[]): AreaData[] {
  return toLineData(points) as AreaData[];
}

function toMarkers(markers: readonly ChartMarker[]): SeriesMarker<Time>[] {
  return [...markers]
    .map((m) => ({
      time: toTime(m.time),
      position: m.position,
      color: m.color,
      shape: m.shape,
      text: m.text,
    }))
    .sort((a, b) => Number(a.time) - Number(b.time));
}

// --- component ------------------------------------------------------------

/**
 * TradingChart — lightweight-charts wrapper 단일 컴포넌트.
 *
 * 라이프사이클:
 * 1) init effect (deps `[height]`) — chart 생성 + ResizeObserver 부착. cleanup 에서 chart.remove() + observer.disconnect().
 * 2) data effect (deps `[data, options.color, ...]` — JSON.stringify 회피, primitive 만) — 데이터 갱신.
 *
 * Strict Mode 더블 invoke:
 * - effect 가 두 번 실행되어도 cleanup 이 먼저 호출 → chart.remove() 로 누수 방지.
 * - chartRef 는 cleanup 시 null 로 reset → 재invoke 시 새 chart 생성.
 *
 * jsdom 환경:
 * - lightweight-charts 는 jsdom 에서 createChart 호출 시 canvas 의존 → 실제 렌더 X (mock 의무).
 * - 본 컴포넌트의 vitest 테스트는 vi.mock('lightweight-charts') 로 createChart spy 검증.
 */
export function TradingChart({
  data,
  options,
  markers,
  benchmark,
  compare,
  area,
  height = 320,
  ariaLabel,
}: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const mainSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const benchmarkSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const compareSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const areaSeriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  // 앱 테마(next-themes) — 문자열 themeKey 만 effect dep 로 사용 (H-1: object dep 금지).
  const { resolvedTheme } = useTheme();
  const themeKey = resolvedTheme === "dark" ? "dark" : "light";

  // --- init effect: chart 생성 + ResizeObserver. height 변경 시만 재생성. ---
  useEffect(() => {
    const container = containerRef.current;
    if (container === null) {
      return;
    }

    // DESIGN.md §0: 앱 테마(.dark) 토큰을 resolved hex/rgba 로 읽어 적용.
    // lightweight-charts 는 var()/currentColor 파싱 불가(colorStringToRgba throw) →
    // getComputedStyle 로 --text-muted/--border 를 해석해 전달. themeKey 변경 시 init
    // effect 가 재실행되어 chart 재생성(아래 deps) → 토글 즉시 반영.
    const rootStyle = getComputedStyle(document.documentElement);
    const axisColor = rootStyle.getPropertyValue("--text-muted").trim() || "#767b85";
    const gridColor =
      rootStyle.getPropertyValue("--border").trim() || "rgba(127,127,127,0.12)";

    const chart = createChart(container, {
      height,
      width: container.clientWidth || 600,
      layout: {
        background: { color: "transparent" },
        textColor: axisColor,
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
      autoSize: false,
    });
    chartRef.current = chart;

    // ResizeObserver — 컨테이너 크기 변동 시 chart resize.
    let observer: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const w = entry.contentRect.width;
          if (w >= 1 && chartRef.current !== null) {
            chartRef.current.applyOptions({ width: Math.floor(w) });
          }
        }
      });
      observer.observe(container);
    }

    return () => {
      if (observer !== null) {
        observer.disconnect();
      }
      // Strict Mode 더블 invoke 방어 — chart 누수 차단.
      if (chartRef.current !== null) {
        chartRef.current.remove();
        chartRef.current = null;
      }
      mainSeriesRef.current = null;
      benchmarkSeriesRef.current = null;
      compareSeriesRef.current = null;
      areaSeriesRef.current = null;
    };
  }, [height, themeKey]);

  // --- data effect: series 추가/갱신. ---
  // dep 는 primitive 또는 stable refs 만 — LESSON-004 H-1 준수.
  // data/markers/benchmark/area 는 호출 측 책임으로 stable identity 유지 (useMemo 권장).
  useEffect(() => {
    const chart = chartRef.current;
    if (chart === null) {
      return;
    }

    // main line series — equity curve.
    if (mainSeriesRef.current === null) {
      mainSeriesRef.current = chart.addLineSeries({
        color: "#22c55e",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
        ...options,
      });
    } else {
      mainSeriesRef.current.applyOptions({ ...options });
    }
    mainSeriesRef.current.setData(toLineData(data));

    if (markers !== undefined) {
      mainSeriesRef.current.setMarkers(toMarkers(markers));
    } else {
      mainSeriesRef.current.setMarkers([]);
    }

    // benchmark line series.
    if (benchmark !== undefined) {
      if (benchmarkSeriesRef.current === null) {
        benchmarkSeriesRef.current = chart.addLineSeries({
          color: "#3b82f6",
          lineWidth: 1,
          lineStyle: 2, // dashed
          priceLineVisible: false,
          lastValueVisible: false,
          ...benchmark.options,
        });
      } else {
        benchmarkSeriesRef.current.applyOptions({ ...benchmark.options });
      }
      benchmarkSeriesRef.current.setData(toLineData(benchmark.data));
    } else if (benchmarkSeriesRef.current !== null) {
      chart.removeSeries(benchmarkSeriesRef.current);
      benchmarkSeriesRef.current = null;
    }

    // compare line series (다른 백테스트 오버레이) — benchmark 와 독립 solid 라인.
    if (compare !== undefined) {
      if (compareSeriesRef.current === null) {
        compareSeriesRef.current = chart.addLineSeries({
          color: "#8b5cf6",
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
          ...compare.options,
        });
      } else {
        compareSeriesRef.current.applyOptions({ ...compare.options });
      }
      compareSeriesRef.current.setData(toLineData(compare.data));
    } else if (compareSeriesRef.current !== null) {
      chart.removeSeries(compareSeriesRef.current);
      compareSeriesRef.current = null;
    }

    // area overlay (drawdown).
    if (area !== undefined) {
      if (areaSeriesRef.current === null) {
        areaSeriesRef.current = chart.addAreaSeries({
          topColor: "rgba(239, 68, 68, 0.25)",
          bottomColor: "rgba(239, 68, 68, 0.02)",
          lineColor: "rgba(239, 68, 68, 0.55)",
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
          ...area.options,
        });
      } else {
        areaSeriesRef.current.applyOptions({ ...area.options });
      }
      areaSeriesRef.current.setData(toAreaData(area.data));
    } else if (areaSeriesRef.current !== null) {
      chart.removeSeries(areaSeriesRef.current);
      areaSeriesRef.current = null;
    }

    chart.timeScale().fitContent();
    // themeKey: init effect 가 테마 토글 시 chart 를 재생성(series ref null) → 본 effect 가
    // 재실행되어 재생성된 chart 에 series 를 다시 채워야 함 (빈 차트 방지).
  }, [data, markers, benchmark, compare, area, options, themeKey]);

  return (
    <div
      ref={containerRef}
      role="img"
      aria-label={ariaLabel}
      style={{ width: "100%", height }}
    />
  );
}
