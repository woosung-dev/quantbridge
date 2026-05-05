import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ChartMarker,
  ChartPoint,
} from "@/components/charts/trading-chart";

import { EquityPane } from "../equity-pane";

// --- lightweight-charts mock ---------------------------------------------
// EquityPane → TradingChart → lightweight-charts.createChart 까지 호출 체인.
// jsdom 환경에서 canvas 미지원 → 모듈 단위 mock 으로 series 호출 검증.

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

// jsdom ResizeObserver mock (TradingChart 의 init effect 의존).
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

const EQUITY: ChartPoint[] = [
  { time: "2026-01-01T00:00:00Z", value: 10000 },
  { time: "2026-01-02T00:00:00Z", value: 10200 },
  { time: "2026-01-03T00:00:00Z", value: 10500 },
];
const BENCHMARK: ChartPoint[] = [
  { time: "2026-01-01T00:00:00Z", value: 10000 },
  { time: "2026-01-02T00:00:00Z", value: 10100 },
  { time: "2026-01-03T00:00:00Z", value: 10300 },
];
const MARKERS: ChartMarker[] = [
  {
    time: "2026-01-01T12:00:00Z",
    position: "belowBar",
    color: "#22c55e",
    shape: "arrowUp",
    text: "L",
  },
];

describe("EquityPane (Sprint 32-B BL-169)", () => {
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

  it("renders TradingChart with green color (Equity series)", () => {
    render(
      <EquityPane
        equityData={EQUITY}
        benchmarkData={BENCHMARK}
        markers={MARKERS}
        height={216}
      />,
    );

    expect(createChartMock).toHaveBeenCalledTimes(1);
    expect(chartInstances).toHaveLength(1);

    const chart = chartInstances[0]!;
    // main + benchmark = 2 line series.
    expect(chart.addLineSeries).toHaveBeenCalledTimes(2);

    // 첫 line series options 에 color #22c55e (green) 포함.
    const mainOptions = chart.addLineSeries.mock.calls[0]![0] as {
      color?: string;
      lineWidth?: number;
    };
    expect(mainOptions.color).toBe("#22c55e");
    expect(mainOptions.lineWidth).toBe(2);
  });

  it("does not render benchmark series when benchmarkData is empty", () => {
    render(
      <EquityPane
        equityData={EQUITY}
        benchmarkData={[]}
        markers={[]}
        height={216}
      />,
    );

    const chart = chartInstances[0]!;
    // main only.
    expect(chart.addLineSeries).toHaveBeenCalledTimes(1);
  });

  it("uses correct chart height (top pane)", () => {
    render(
      <EquityPane
        equityData={EQUITY}
        benchmarkData={[]}
        markers={[]}
        height={216}
      />,
    );

    // createChart 첫 인자는 container, 두번째 인자는 options.
    const callArgs = createChartMock.mock.calls[0]!;
    const opts = callArgs[1] as { height: number };
    expect(opts.height).toBe(216);
  });

  it("applies markers via series.setMarkers when provided", () => {
    render(
      <EquityPane
        equityData={EQUITY}
        benchmarkData={[]}
        markers={MARKERS}
        height={216}
      />,
    );

    const chart = chartInstances[0]!;
    const series = chart.addLineSeries.mock.results[0]!.value as SeriesSpy;
    expect(series.setMarkers).toHaveBeenCalled();
  });
});
