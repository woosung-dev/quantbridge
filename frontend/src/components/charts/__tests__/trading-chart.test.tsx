import { render } from "@testing-library/react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { TradingChart, type ChartPoint, type ChartMarker } from "../trading-chart";

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
        addLineSeries: vi.fn((): SeriesSpy => ({
          setData: vi.fn(),
          applyOptions: vi.fn(),
          setMarkers: vi.fn(),
        })),
        addAreaSeries: vi.fn((): SeriesSpy => ({
          setData: vi.fn(),
          applyOptions: vi.fn(),
          setMarkers: vi.fn(),
        })),
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
    (
      globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }
    ).ResizeObserver = MockResizeObserver;
  });

  afterEach(() => {
    delete (globalThis as unknown as { ResizeObserver?: unknown })
      .ResizeObserver;
  });

  it("calls createChart exactly once on mount and sets main line series data", () => {
    render(
      <TradingChart
        data={POINTS}
        ariaLabel="Equity chart"
        height={300}
      />,
    );

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

  it("applies markers via series.setMarkers when markers prop is provided", () => {
    render(
      <TradingChart
        data={POINTS}
        markers={MARKERS}
        ariaLabel="Equity chart with markers"
      />,
    );

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

  it("creates benchmark line series and area overlay when props provided", () => {
    render(
      <TradingChart
        data={POINTS}
        benchmark={{ data: POINTS }}
        area={{ data: POINTS }}
        ariaLabel="Equity chart with benchmark"
      />,
    );

    const chart = chartInstances[0]!;
    // 메인 + benchmark = 2 line series.
    expect(chart.addLineSeries).toHaveBeenCalledTimes(2);
    // area overlay 1.
    expect(chart.addAreaSeries).toHaveBeenCalledTimes(1);
  });

  it("calls chart.remove() on unmount (cleanup)", () => {
    const { unmount } = render(
      <TradingChart data={POINTS} ariaLabel="Equity chart" />,
    );

    const chart = chartInstances[0]!;
    expect(chart.remove).not.toHaveBeenCalled();

    unmount();

    expect(chart.remove).toHaveBeenCalledTimes(1);
  });

  it("renders with role=img and aria-label for a11y", () => {
    const { getByRole } = render(
      <TradingChart data={POINTS} ariaLabel="Backtest equity curve" />,
    );

    const node = getByRole("img");
    expect(node).toBeInTheDocument();
    expect(node.getAttribute("aria-label")).toBe("Backtest equity curve");
  });
});
