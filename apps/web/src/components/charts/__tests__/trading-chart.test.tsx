import { act, cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// chart 생성이 effect 내 dynamic import 후 비동기로 일어나므로 렌더 뒤 microtask flush 필수.
async function flushChartInit() {
  await act(async () => {});
}

import {
  TradingChart,
  type ChartPoint,
  type ChartMarker,
  type HistogramPoint,
} from "../trading-chart";

// --- lightweight-charts mock ---------------------------------------------
// jsdom 은 canvas 가 없어 createChart 가 실제로 동작 불가 → 모듈 단위로 mock.
// spy 를 통해 createChart 호출 횟수 / setData / setMarkers / remove 호출 검증.

interface SeriesSpy {
  setData: ReturnType<typeof vi.fn>;
  applyOptions: ReturnType<typeof vi.fn>;
  setMarkers: ReturnType<typeof vi.fn>;
}

interface ChartSpy {
  addLineSeries: ReturnType<typeof vi.fn>;
  addAreaSeries: ReturnType<typeof vi.fn>;
  addHistogramSeries: ReturnType<typeof vi.fn>;
  removeSeries: ReturnType<typeof vi.fn>;
  applyOptions: ReturnType<typeof vi.fn>;
  remove: ReturnType<typeof vi.fn>;
  timeScale: ReturnType<typeof vi.fn>;
}

const createChartMock = vi.fn();
const chartInstances: ChartSpy[] = [];

vi.mock("lightweight-charts", () => {
  return {
    createChart: (...args: unknown[]) => {
      createChartMock(...args);
      const chart: ChartSpy = {
        addLineSeries: vi.fn(
          (): SeriesSpy => ({
            setData: vi.fn(),
            applyOptions: vi.fn(),
            setMarkers: vi.fn(),
          }),
        ),
        addAreaSeries: vi.fn(
          (): SeriesSpy => ({
            setData: vi.fn(),
            applyOptions: vi.fn(),
            setMarkers: vi.fn(),
          }),
        ),
        addHistogramSeries: vi.fn(
          (): SeriesSpy => ({
            setData: vi.fn(),
            applyOptions: vi.fn(),
            setMarkers: vi.fn(),
          }),
        ),
        removeSeries: vi.fn(),
        applyOptions: vi.fn(),
        remove: vi.fn(),
        timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
      };
      chartInstances.push(chart);
      return chart;
    },
  };
});

// jsdom ResizeObserver mock — observer 미정의 환경 시뮬.
type RoCallback = (entries: Array<{ contentRect: { width: number } }>) => void;
let roInstances: Array<{ cb: RoCallback; targets: Element[] }> = [];

class MockResizeObserver {
  cb: RoCallback;
  targets: Element[] = [];
  constructor(cb: RoCallback) {
    this.cb = cb;
    roInstances.push({ cb, targets: this.targets });
  }
  observe(target: Element) {
    this.targets.push(target);
  }
  unobserve() {}
  disconnect() {
    this.targets = [];
  }
}

const POINTS: ChartPoint[] = [
  { time: "2026-01-01T00:00:00Z", value: 10000 },
  { time: "2026-01-02T00:00:00Z", value: 10200 },
  { time: "2026-01-03T00:00:00Z", value: 10500 },
];

const MARKERS: ChartMarker[] = [
  {
    time: "2026-01-01T12:00:00Z",
    position: "belowBar",
    color: "#22c55e",
    shape: "arrowUp",
    text: "ENTRY",
  },
];

describe("TradingChart", () => {
  beforeEach(() => {
    createChartMock.mockClear();
    chartInstances.length = 0;
    roInstances = [];
    (globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }).ResizeObserver =
      MockResizeObserver;
  });

  afterEach(() => {
    delete (globalThis as unknown as { ResizeObserver?: unknown }).ResizeObserver;
  });

  it("calls createChart exactly once on mount and sets main line series data", async () => {
    render(<TradingChart data={POINTS} ariaLabel="Equity chart" height={300} />);
    await flushChartInit();

    // createChart 호출 1회 (Strict Mode 가 아니어도 1회, Strict Mode 에서도 cleanup 후 재invoke 시 누수 없이 1회 유지).
    expect(createChartMock).toHaveBeenCalledTimes(1);
    expect(chartInstances).toHaveLength(1);
    const chart = chartInstances[0]!;
    expect(chart.addLineSeries).toHaveBeenCalledTimes(1);

    // setData 가 series 에 호출됐는지 확인.
    const seriesCall = chart.addLineSeries.mock.results[0]!.value as SeriesSpy;
    expect(seriesCall.setData).toHaveBeenCalledTimes(1);
    const dataArg = seriesCall.setData.mock.calls[0]![0] as Array<{
      time: number;
      value: number;
    }>;
    expect(dataArg).toHaveLength(3);
    // time 은 epoch seconds 로 정규화.
    expect(dataArg[0]!.time).toBe(Math.floor(Date.parse(POINTS[0]!.time as string) / 1000));
  });

  it("applies markers via series.setMarkers when markers prop is provided", async () => {
    render(<TradingChart data={POINTS} markers={MARKERS} ariaLabel="Equity chart with markers" />);
    await flushChartInit();

    const chart = chartInstances[0]!;
    const series = chart.addLineSeries.mock.results[0]!.value as SeriesSpy;
    expect(series.setMarkers).toHaveBeenCalled();
    const markerArg = series.setMarkers.mock.calls[0]![0] as Array<{
      time: number;
      shape: string;
      text?: string;
    }>;
    expect(markerArg).toHaveLength(1);
    expect(markerArg[0]!.shape).toBe("arrowUp");
    expect(markerArg[0]!.text).toBe("ENTRY");
  });

  it("creates benchmark line series and area overlay when props provided", async () => {
    render(
      <TradingChart
        data={POINTS}
        benchmark={{ data: POINTS }}
        area={{ data: POINTS }}
        ariaLabel="Equity chart with benchmark"
      />,
    );
    await flushChartInit();

    const chart = chartInstances[0]!;
    // 메인 + benchmark = 2 line series.
    expect(chart.addLineSeries).toHaveBeenCalledTimes(2);
    // area overlay 1.
    expect(chart.addAreaSeries).toHaveBeenCalledTimes(1);
  });

  it("creates histogram series with per-point colors when histogram prop provided", async () => {
    const histogramPoints: HistogramPoint[] = [
      { time: "2026-01-01T00:00:00Z", value: 120, color: "#0f9d6b" },
      { time: "2026-01-02T00:00:00Z", value: -80, color: "#e0413e" },
      { time: "2026-01-03T00:00:00Z", value: 40 },
    ];
    render(
      <TradingChart
        data={POINTS}
        histogram={{ data: histogramPoints }}
        ariaLabel="Trade PnL bars"
      />,
    );
    await flushChartInit();

    const chart = chartInstances[0]!;
    expect(chart.addHistogramSeries).toHaveBeenCalledTimes(1);
    const series = chart.addHistogramSeries.mock.results[0]!.value as SeriesSpy;
    const dataArg = series.setData.mock.calls[0]![0] as Array<{
      time: number;
      value: number;
      color?: string;
    }>;
    expect(dataArg).toHaveLength(3);
    expect(dataArg[0]!.color).toBe("#0f9d6b");
    expect(dataArg[1]!.color).toBe("#e0413e");
    expect(dataArg[2]!.color).toBeUndefined();
  });

  it("removes histogram series when histogram prop is dropped", async () => {
    const histogramPoints: HistogramPoint[] = [{ time: "2026-01-01T00:00:00Z", value: 120 }];
    const { rerender } = render(
      <TradingChart
        data={POINTS}
        histogram={{ data: histogramPoints }}
        ariaLabel="Trade PnL bars"
      />,
    );
    await flushChartInit();
    const chart = chartInstances[0]!;
    expect(chart.addHistogramSeries).toHaveBeenCalledTimes(1);

    rerender(<TradingChart data={POINTS} ariaLabel="Trade PnL bars" />);
    expect(chart.removeSeries).toHaveBeenCalledTimes(1);
  });

  it("calls chart.remove() on unmount (cleanup)", async () => {
    const { unmount } = render(<TradingChart data={POINTS} ariaLabel="Equity chart" />);
    await flushChartInit();

    const chart = chartInstances[0]!;
    expect(chart.remove).not.toHaveBeenCalled();

    unmount();

    expect(chart.remove).toHaveBeenCalledTimes(1);
  });

  it("renders with role=img and aria-label for a11y", () => {
    const { getByRole } = render(<TradingChart data={POINTS} ariaLabel="Backtest equity curve" />);

    const node = getByRole("img");
    expect(node).toBeInTheDocument();
    expect(node.getAttribute("aria-label")).toBe("Backtest equity curve");
  });

  it("BL-458 — per-point color 는 지정 시 전달되고, 미지정 시 출력이 불변이다", async () => {
    // ★후자가 이 테스트의 요점이다. `toLineData` 는 이 컴포넌트의 10여 호출자가
    // 공유하므로, 색을 안 준 경우의 setData 인자가 예전과 정확히 같아야 한다.
    // `color: undefined` 키가 끼면 그 계약이 깨진다.
    render(<TradingChart data={POINTS} ariaLabel="Equity chart" height={300} />);
    await flushChartInit();
    const plain = (chartInstances[0]!.addLineSeries.mock.results[0]!.value as SeriesSpy).setData
      .mock.calls[0]![0] as Array<Record<string, unknown>>;
    expect(plain.every((d) => !("color" in d))).toBe(true);

    cleanup();
    chartInstances.length = 0;
    createChartMock.mockClear();

    const coloured = POINTS.map((p, i) => ({
      ...p,
      color: i === 0 ? "#111111" : "#222222",
    }));
    render(<TradingChart data={coloured} ariaLabel="Equity chart" height={300} />);
    await flushChartInit();
    const withColor = (chartInstances[0]!.addLineSeries.mock.results[0]!.value as SeriesSpy).setData
      .mock.calls[0]![0] as Array<Record<string, unknown>>;
    expect(withColor.map((d) => d.color)).toEqual(["#111111", "#222222", "#222222"]);
  });
});
