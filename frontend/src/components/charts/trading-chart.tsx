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
//
// 번들: lightweight-charts 는 init effect 안에서 dynamic import — route 초기 JS 제외.
// 모듈 상단 import 는 전부 type-only (컴파일 시 제거).

import { useTheme } from "next-themes";
import { useEffect, useRef } from "react";
import type { RefObject } from "react";
import type {
  ChartOptions,
  DeepPartial,
  IChartApi,
  ISeriesApi,
  LineSeriesPartialOptions,
  LineData,
  AreaSeriesPartialOptions,
  AreaData,
  HistogramSeriesPartialOptions,
  HistogramData,
  SeriesMarker,
  Time,
  UTCTimestamp,
} from "lightweight-charts";

import { resolveChartTokens } from "@/lib/chart-tokens";

/**
 * 단순화된 시계열 포인트.
 * - time: ISO datetime 문자열 또는 epoch seconds(number) 모두 허용 → 내부에서 UTCTimestamp 로 정규화.
 * - value: 표시할 숫자값 (equity / B&H / drawdown 등 시리즈에 따라 의미 다름).
 */
export interface ChartPoint {
  time: string | number;
  value: number;
  /**
   * BL-458 — 포인트별 선 색(옵션). 미지정이면 시리즈 기본색이 그대로 쓰이고 출력이
   * **byte-identical** 하다(기존 호출자 전원 무영향). lightweight-charts 는 포인트 색을
   * 인접 세그먼트에 적용하므로 경계 세그먼트는 off-by-one 이다 — 데이터 매핑만
   * 단정하고 픽셀은 단정하지 않는다.
   */
  color?: string;
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
  data: readonly ChartPoint[];
  options?: AreaSeriesPartialOptions;
}

/** per-trade PnL 바 등 히스토그램 포인트 — color 로 per-point 녹/적 구분. */
export interface HistogramPoint extends ChartPoint {
  color?: string;
}

export interface TradingChartProps {
  /** 메인 line series 데이터 (예: equity curve). */
  data: readonly ChartPoint[];
  /** 메인 series 옵션 (색상 등). */
  options?: LineSeriesPartialOptions;
  /** 거래 마커 (entry/exit 등). */
  markers?: readonly ChartMarker[];
  /** 비교용 보조 line (예: B&H benchmark). */
  benchmark?: { data: readonly ChartPoint[]; options?: LineSeriesPartialOptions };
  /** 두 번째 비교 line (예: 다른 백테스트 Compare 오버레이). benchmark 와 독립. */
  compare?: { data: readonly ChartPoint[]; options?: LineSeriesPartialOptions };
  /** 영역 오버레이 (예: drawdown area). */
  area?: AreaOverlay;
  /** 히스토그램 오버레이 (예: per-trade PnL 바). */
  histogram?: {
    data: readonly HistogramPoint[];
    options?: HistogramSeriesPartialOptions;
  };
  /** 차트 높이. */
  height?: number;
  /** 접근성 라벨 (a11y 의무). */
  ariaLabel: string;
}

/** series 렌더에 필요한 props 부분집합 — 비동기 chart 생성 시점 스냅샷 전달용. */
type SeriesSnapshot = Pick<
  TradingChartProps,
  "data" | "options" | "markers" | "benchmark" | "compare" | "area" | "histogram"
>;

/** 컴포넌트가 보유한 series 인스턴스 refs 번들 — syncSeries 가 읽고/쓴다. */
interface SeriesRefs {
  main: RefObject<ISeriesApi<"Line"> | null>;
  benchmark: RefObject<ISeriesApi<"Line"> | null>;
  compare: RefObject<ISeriesApi<"Line"> | null>;
  area: RefObject<ISeriesApi<"Area"> | null>;
  histogram: RefObject<ISeriesApi<"Histogram"> | null>;
}

// --- helpers --------------------------------------------------------------

// lightweight-charts dynamic import 싱글턴 — 여러 chart 인스턴스가 동시에 마운트돼도
// 모듈 로드는 1회만 발생 (vitest mock 레지스트리 동시 해석 경합 회피 겸용).
interface LightweightChartsModule {
  createChart: (
    container: string | HTMLElement,
    options?: DeepPartial<ChartOptions>,
  ) => IChartApi;
}

let lwcModulePromise: Promise<LightweightChartsModule> | null = null;

function loadLightweightCharts(): Promise<LightweightChartsModule> {
  if (lwcModulePromise === null) {
    lwcModulePromise = import("lightweight-charts");
  }
  return lwcModulePromise;
}

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
  // BL-458 — per-point color 는 있을 때만 실는다. `color: undefined` 를 넣으면
  // 출력 객체 모양이 바뀌어 기존 호출자의 setData 인자가 달라진다.
  const mapped: LineData[] = points.map((p) =>
    p.color !== undefined
      ? { time: toTime(p.time), value: p.value, color: p.color }
      : { time: toTime(p.time), value: p.value },
  );
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

function toHistogramData(points: readonly HistogramPoint[]): HistogramData[] {
  // toLineData 와 동일한 정렬/중복 제거 + per-point color 보존.
  const colorByTime = new Map<number, string | undefined>();
  for (const p of points) {
    colorByTime.set(Number(toTime(p.time)), p.color);
  }
  return toLineData(points).map((d) => {
    const color = colorByTime.get(Number(d.time));
    return color !== undefined ? { ...d, color } : d;
  });
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

/**
 * series 추가/갱신 — init(비동기 chart 생성 직후) + data effect(prop 변경) 공용.
 * 모듈 레벨 함수: refs 번들을 인자로 받아 컴포넌트 스코프 클로저 dep 를 만들지 않는다.
 */
function syncSeries(chart: IChartApi, refs: SeriesRefs, snapshot: SeriesSnapshot) {
  const { data, options, markers, benchmark, compare, area, histogram } = snapshot;

  // 시리즈 기본색 — chart-tokens SSOT (호출측 options 로 override 가능).
  const palette = resolveChartTokens();

  // main line series — equity curve.
  if (refs.main.current === null) {
    refs.main.current = chart.addLineSeries({
      color: palette.equity,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      ...options,
    });
  } else {
    refs.main.current.applyOptions({ ...options });
  }
  refs.main.current.setData(toLineData(data));

  if (markers !== undefined) {
    refs.main.current.setMarkers(toMarkers(markers));
  } else {
    refs.main.current.setMarkers([]);
  }

  // benchmark line series.
  if (benchmark !== undefined) {
    if (refs.benchmark.current === null) {
      refs.benchmark.current = chart.addLineSeries({
        color: palette.benchmark,
        lineWidth: 1,
        lineStyle: 2, // dashed
        priceLineVisible: false,
        lastValueVisible: false,
        ...benchmark.options,
      });
    } else {
      refs.benchmark.current.applyOptions({ ...benchmark.options });
    }
    refs.benchmark.current.setData(toLineData(benchmark.data));
  } else if (refs.benchmark.current !== null) {
    chart.removeSeries(refs.benchmark.current);
    refs.benchmark.current = null;
  }

  // compare line series (다른 백테스트 오버레이) — benchmark 와 독립 solid 라인.
  if (compare !== undefined) {
    if (refs.compare.current === null) {
      refs.compare.current = chart.addLineSeries({
        color: palette.compare,
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        ...compare.options,
      });
    } else {
      refs.compare.current.applyOptions({ ...compare.options });
    }
    refs.compare.current.setData(toLineData(compare.data));
  } else if (refs.compare.current !== null) {
    chart.removeSeries(refs.compare.current);
    refs.compare.current = null;
  }

  // area overlay (drawdown).
  if (area !== undefined) {
    if (refs.area.current === null) {
      refs.area.current = chart.addAreaSeries({
        topColor: palette.ddTop,
        bottomColor: palette.ddBottom,
        lineColor: palette.ddLine,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        ...area.options,
      });
    } else {
      refs.area.current.applyOptions({ ...area.options });
    }
    refs.area.current.setData(toAreaData(area.data));
  } else if (refs.area.current !== null) {
    chart.removeSeries(refs.area.current);
    refs.area.current = null;
  }

  // histogram overlay (per-trade PnL 바) — per-point color 는 데이터에 포함.
  if (histogram !== undefined) {
    if (refs.histogram.current === null) {
      refs.histogram.current = chart.addHistogramSeries({
        color: palette.equity,
        priceLineVisible: false,
        lastValueVisible: false,
        ...histogram.options,
      });
    } else {
      refs.histogram.current.applyOptions({ ...histogram.options });
    }
    refs.histogram.current.setData(toHistogramData(histogram.data));
  } else if (refs.histogram.current !== null) {
    chart.removeSeries(refs.histogram.current);
    refs.histogram.current = null;
  }

  chart.timeScale().fitContent();
}

// --- component ------------------------------------------------------------

/**
 * TradingChart — lightweight-charts wrapper 단일 컴포넌트.
 *
 * 라이프사이클:
 * 1) init effect (deps `[height, themeKey]`) — dynamic import 후 chart 생성 + ResizeObserver 부착
 *    + 최신 props 스냅샷으로 초기 series sync. cleanup 에서 chart.remove() + observer.disconnect().
 * 2) data effect (deps primitive/stable refs 만 — JSON.stringify 회피) — 데이터 갱신.
 *
 * Strict Mode 더블 invoke:
 * - effect 가 두 번 실행되어도 cleanup 이 먼저 호출 → disposed 가드 + chart.remove() 로 누수 방지.
 * - chartRef 는 cleanup 시 null 로 reset → 재invoke 시 새 chart 생성.
 *
 * jsdom 환경:
 * - lightweight-charts 는 jsdom 에서 createChart 호출 시 canvas 의존 → 실제 렌더 X (mock 의무).
 * - 본 컴포넌트의 vitest 테스트는 vi.mock('lightweight-charts') 로 createChart spy 검증.
 * - chart 생성이 비동기(dynamic import)이므로 테스트는 microtask flush 후 단정 의무.
 */
export function TradingChart({
  data,
  options,
  markers,
  benchmark,
  compare,
  area,
  histogram,
  height = 320,
  ariaLabel,
}: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const mainSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const benchmarkSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const compareSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const areaSeriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const histogramSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  // 앱 테마(next-themes) — 문자열 themeKey 만 effect dep 로 사용 (H-1: object dep 금지).
  const { resolvedTheme } = useTheme();
  const themeKey = resolvedTheme === "dark" ? "dark" : "light";

  // 최신 series props 스냅샷 — chart 가 dynamic import 후 비동기로 생성되므로,
  // 생성 시점에 stale closure 가 아닌 최신 커밋 props 로 초기 시리즈를 채우기 위함.
  // deps 없는 sync useEffect 로 매 commit 갱신 (H-3 표준 패턴).
  const propsRef = useRef<SeriesSnapshot>({
    data,
    options,
    markers,
    benchmark,
    compare,
    area,
    histogram,
  });
  useEffect(() => {
    propsRef.current = { data, options, markers, benchmark, compare, area, histogram };
  });

  // --- init effect: chart 생성 + ResizeObserver. height/테마 변경 시만 재생성. ---
  useEffect(() => {
    const container = containerRef.current;
    if (container === null) {
      return;
    }

    let disposed = false;
    let observer: ResizeObserver | null = null;

    // 번들 절감: lightweight-charts 는 chart 생성 시점에만 필요 → effect 안 dynamic import
    // (route 초기 JS 에서 제외). cleanup 이 먼저 실행된 경우 disposed 가드로 생성 skip.
    void loadLightweightCharts().then(({ createChart }) => {
      if (disposed || containerRef.current === null) {
        return;
      }

      // DESIGN.md §0: 앱 테마(.dark) 토큰을 resolved hex/rgba 로 읽어 적용.
      // lightweight-charts 는 var()/currentColor 파싱 불가(colorStringToRgba throw) →
      // chart-tokens.ts SSOT 로 해석해 전달. themeKey 변경 시 init effect 가
      // 재실행되어 chart 재생성(아래 deps) → 토글 즉시 반영.
      const palette = resolveChartTokens();
      const axisColor = palette.axis;
      const gridColor = palette.grid;

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

      // 초기 시리즈 채움 — data effect 는 chart 생성 전(chartRef null)에 이미
      // 지나갔을 수 있으므로 여기서 최신 스냅샷으로 직접 sync.
      syncSeries(
        chart,
        {
          main: mainSeriesRef,
          benchmark: benchmarkSeriesRef,
          compare: compareSeriesRef,
          area: areaSeriesRef,
          histogram: histogramSeriesRef,
        },
        propsRef.current,
      );
    });

    return () => {
      disposed = true;
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
      histogramSeriesRef.current = null;
    };
  }, [height, themeKey]);

  // --- data effect: series 추가/갱신. ---
  // dep 는 primitive 또는 stable refs 만 — LESSON-004 H-1 준수.
  // data/markers/benchmark/area 는 호출 측 책임으로 stable identity 유지 (useMemo 권장).
  // chart 미생성(비동기 import 진행 중) 시 skip — 생성 직후 init effect 가 sync 담당.
  useEffect(() => {
    const chart = chartRef.current;
    if (chart === null) {
      return;
    }
    syncSeries(
      chart,
      {
        main: mainSeriesRef,
        benchmark: benchmarkSeriesRef,
        compare: compareSeriesRef,
        area: areaSeriesRef,
        histogram: histogramSeriesRef,
      },
      { data, options, markers, benchmark, compare, area, histogram },
    );
    // themeKey: init effect 가 테마 토글 시 chart 를 재생성(series ref null) → 본 effect 가
    // 재실행되어 재생성된 chart 에 series 를 다시 채워야 함 (빈 차트 방지).
  }, [data, markers, benchmark, compare, area, histogram, options, themeKey]);

  return (
    <div
      ref={containerRef}
      role="img"
      aria-label={ariaLabel}
      style={{ width: "100%", height }}
    />
  );
}
