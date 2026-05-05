// Sprint 33-A (BL-150 partial) — ActivityTimelineChart 단위 테스트.
//
// 패턴: trading-chart.test.tsx 와 동일 (lightweight-charts 모듈 mock).
// 검증:
//  1) 빈 배열 → null 렌더 (defensive).
//  2) showEquity=false → 1 chart 인스턴스 (top pane only) + entries/closes 2 line series.
//  3) showEquity=true → 2 chart 인스턴스 (top + bottom equity pane).
//  4) Strict Mode 더블 invoke 없이 createChart 호출 횟수 정확.
//  5) Legend 항목 (Entries / Closes / Equity) 노출.
//  6) ErrorBoundary 미발동 — render 가 throw 하지 않음.
//  7) a11y — group role + aria-label 노출.

import { render, screen } from "@testing-library/react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import type { ChartMarker } from "@/components/charts/trading-chart";

import type {
  ActivityTimelinePoint,
  ActivityTimelineWithEquityPoint,
} from "../../utils";
import { ActivityTimelineChart } from "../activity-timeline-chart";

// --- lightweight-charts mock ---------------------------------------------

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
const lineSeriesSetDataCalls: Array<Array<{ time: number; value: number }>> = [];

vi.mock("lightweight-charts", () => {
  return {
    createChart: (...args: unknown[]) => {
      createChartMock(...args);
      const chart: ChartSpy = {
        addLineSeries: vi.fn((): SeriesSpy => {
          const series: SeriesSpy = {
            setData: vi.fn((d: unknown) => {
              lineSeriesSetDataCalls.push(
                d as Array<{ time: number; value: number }>,
              );
            }),
            applyOptions: vi.fn(),
            setMarkers: vi.fn(),
          };
          return series;
        }),
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

// jsdom ResizeObserver mock.
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

// --- fixtures ------------------------------------------------------------

const POINTS: ActivityTimelinePoint[] = [
  {
    label: new Date("2026-05-01T12:00:00Z").toLocaleString(),
    entries_in_window: 1,
    closes_in_window: 0,
  },
  {
    label: new Date("2026-05-01T12:01:00Z").toLocaleString(),
    entries_in_window: 1,
    closes_in_window: 1,
  },
];

const POINTS_WITH_EQUITY: ActivityTimelineWithEquityPoint[] = [
  {
    label: new Date("2026-05-01T12:00:00Z").toLocaleString(),
    entries_in_window: 1,
    closes_in_window: 0,
    cumulative_pnl: 0,
  },
  {
    label: new Date("2026-05-01T12:01:00Z").toLocaleString(),
    entries_in_window: 1,
    closes_in_window: 1,
    cumulative_pnl: 12.34,
  },
];

// --- tests ---------------------------------------------------------------

describe("ActivityTimelineChart (Sprint 33-A BL-150 partial)", () => {
  beforeEach(() => {
    createChartMock.mockClear();
    chartInstances.length = 0;
    lineSeriesSetDataCalls.length = 0;
    roInstances = [];
    (
      globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }
    ).ResizeObserver = MockResizeObserver;
  });

  afterEach(() => {
    delete (globalThis as unknown as { ResizeObserver?: unknown })
      .ResizeObserver;
  });

  it("renders nothing when data is empty (defensive)", () => {
    const { container } = render(
      <ActivityTimelineChart data={[]} showEquity={false} />,
    );
    expect(container).toBeEmptyDOMElement();
    expect(createChartMock).not.toHaveBeenCalled();
  });

  it("creates exactly 1 chart instance when showEquity=false (counts pane only)", () => {
    render(<ActivityTimelineChart data={POINTS} showEquity={false} />);

    expect(createChartMock).toHaveBeenCalledTimes(1);
    expect(chartInstances).toHaveLength(1);

    // counts pane = entries (main line) + closes (benchmark line) → 2 line series.
    const chart = chartInstances[0]!;
    expect(chart.addLineSeries).toHaveBeenCalledTimes(2);
  });

  it("creates 2 chart instances when showEquity=true (counts + equity pane)", () => {
    render(
      <ActivityTimelineChart data={POINTS_WITH_EQUITY} showEquity={true} />,
    );

    expect(createChartMock).toHaveBeenCalledTimes(2);
    expect(chartInstances).toHaveLength(2);

    // counts pane = 2 series (entries + closes).
    expect(chartInstances[0]!.addLineSeries).toHaveBeenCalledTimes(2);
    // equity pane = 1 series (cumulative_pnl).
    expect(chartInstances[1]!.addLineSeries).toHaveBeenCalledTimes(1);
  });

  it("legend shows Entries + Closes only when showEquity=false", () => {
    render(<ActivityTimelineChart data={POINTS} showEquity={false} />);

    expect(screen.getByText("Entries (window)")).toBeInTheDocument();
    expect(screen.getByText("Closes (window)")).toBeInTheDocument();
    expect(screen.queryByText(/Equity/)).not.toBeInTheDocument();
  });

  it("legend shows Equity (PnL) item when showEquity=true", () => {
    render(
      <ActivityTimelineChart data={POINTS_WITH_EQUITY} showEquity={true} />,
    );

    expect(screen.getByText("Entries (window)")).toBeInTheDocument();
    expect(screen.getByText("Closes (window)")).toBeInTheDocument();
    expect(screen.getByText("Equity (PnL, USDT)")).toBeInTheDocument();
  });

  it("respects 60/40 height ratio when showEquity=true (top=115, bottom=77 for height=192)", () => {
    render(
      <ActivityTimelineChart
        data={POINTS_WITH_EQUITY}
        showEquity={true}
        height={192}
      />,
    );

    const top = createChartMock.mock.calls[0]![1] as { height: number };
    const bottom = createChartMock.mock.calls[1]![1] as { height: number };
    expect(top.height).toBe(115); // round(192 * 0.6)
    expect(bottom.height).toBe(77); // round(192 * 0.4)
  });

  it("uses full height for counts pane when showEquity=false", () => {
    render(
      <ActivityTimelineChart data={POINTS} showEquity={false} height={192} />,
    );

    const top = createChartMock.mock.calls[0]![1] as { height: number };
    expect(top.height).toBe(192);
  });

  it("setData receives ascending epoch-seconds time (lightweight-charts contract)", () => {
    render(<ActivityTimelineChart data={POINTS} showEquity={false} />);

    // 첫 setData = entries main line series.
    expect(lineSeriesSetDataCalls.length).toBeGreaterThanOrEqual(1);
    const first = lineSeriesSetDataCalls[0]!;
    expect(first).toHaveLength(2);
    // time 은 number (epoch seconds).
    expect(typeof first[0]!.time).toBe("number");
    // ascending 정렬.
    expect(first[0]!.time).toBeLessThan(first[1]!.time);
  });

  it("group role + aria-label for a11y", () => {
    render(<ActivityTimelineChart data={POINTS} showEquity={false} />);

    const group = screen.getByRole("group", {
      name: /Live session activity timeline/,
    });
    expect(group).toBeInTheDocument();
  });

  it("does not throw — render completes without ErrorBoundary trigger", () => {
    // currentColor regression (Sprint 30 BL-157) 재현 방어 — 렌더 자체가 throw X.
    // trading-chart wrapper 가 hex 색상으로 명시적 변환했으므로 안전.
    expect(() => {
      render(
        <ActivityTimelineChart data={POINTS_WITH_EQUITY} showEquity={true} />,
      );
    }).not.toThrow();
  });

  it("cleanup — chart.remove() on unmount (no leak)", () => {
    const { unmount } = render(
      <ActivityTimelineChart data={POINTS_WITH_EQUITY} showEquity={true} />,
    );
    expect(chartInstances).toHaveLength(2);
    chartInstances.forEach((c) => expect(c.remove).not.toHaveBeenCalled());

    unmount();
    chartInstances.forEach((c) => expect(c.remove).toHaveBeenCalledTimes(1));
  });

  // 사용 안 하지만 marker 타입 import 가 깨지지 않는지 정적 확인.
  it("ChartMarker type is importable (compile-only sanity)", () => {
    const sample: ChartMarker = {
      time: 0,
      position: "aboveBar",
      color: "#000",
      shape: "circle",
    };
    expect(sample.shape).toBe("circle");
  });
});
