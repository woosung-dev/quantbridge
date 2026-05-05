import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ChartMarker } from "@/components/charts/trading-chart";
import type { EquityPoint, TradeItem } from "@/features/backtest/schemas";

import { EquityChartV2 } from "../equity-chart-v2";

// --- lightweight-charts mock ---------------------------------------------
// 2-pane 구조 → createChart 가 두 번 호출 (top + bottom) 되어야 함.

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
const lineSeriesMarkerCalls: ChartMarker[][] = [];

vi.mock("lightweight-charts", () => {
  return {
    createChart: (...args: unknown[]) => {
      createChartMock(...args);
      const chart: ChartSpy = {
        addLineSeries: vi.fn((): SeriesSpy => {
          const series: SeriesSpy = {
            setData: vi.fn(),
            applyOptions: vi.fn(),
            setMarkers: vi.fn((m: unknown) => {
              lineSeriesMarkerCalls.push(m as ChartMarker[]);
            }),
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

const EQUITY: EquityPoint[] = [
  { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
  { timestamp: "2026-01-02T00:00:00Z", value: 10200 },
  { timestamp: "2026-01-03T00:00:00Z", value: 10500 },
];

const TRADES: TradeItem[] = [
  {
    trade_index: 1,
    direction: "long",
    status: "closed",
    entry_time: "2026-01-01T12:00:00Z",
    exit_time: "2026-01-02T12:00:00Z",
    entry_price: 100,
    exit_price: 110,
    size: 1,
    pnl: 10,
    return_pct: 0.1,
    fees: 0.1,
  },
];

const EXTRA_MARKERS: ChartMarker[] = [
  {
    time: "2026-01-02T18:00:00Z",
    position: "aboveBar",
    color: "#facc15",
    shape: "circle",
    text: "TP",
  },
];

describe("EquityChartV2 — 2-pane shell (Sprint 32-B BL-169+170)", () => {
  beforeEach(() => {
    createChartMock.mockClear();
    chartInstances.length = 0;
    lineSeriesMarkerCalls.length = 0;
    roInstances = [];
    (
      globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }
    ).ResizeObserver = MockResizeObserver;
  });

  afterEach(() => {
    delete (globalThis as unknown as { ResizeObserver?: unknown })
      .ResizeObserver;
  });

  it("renders empty state when equityCurve is empty", () => {
    render(<EquityChartV2 equityCurve={[]} initialCapital={10000} />);
    expect(screen.getByText(/Equity 데이터가 없습니다/)).toBeInTheDocument();
    expect(createChartMock).not.toHaveBeenCalled();
  });

  it("creates two chart instances (top Equity + bottom Drawdown panes)", () => {
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        initialCapital={10000}
        height={400}
      />,
    );

    // 2-pane = 2 createChart calls.
    expect(createChartMock).toHaveBeenCalledTimes(2);
    expect(chartInstances).toHaveLength(2);
  });

  it("renders ChartLegend without BH when buyAndHoldCurve is null/undefined", () => {
    // Sprint 34 BL-175: backend metrics.buy_and_hold_curve 가 null 시 BH series
    // 미렌더 + ChartLegend BH 항목 자동 hide. fail-closed 정책 정합 (OHLCV
    // close 1건이라도 invalid → BE 가 None → FE BH series 0).
    render(<EquityChartV2 equityCurve={EQUITY} initialCapital={10000} />);

    expect(screen.getByRole("list", { name: "차트 범례" })).toBeInTheDocument();
    expect(screen.getByText("Equity (자본 곡선)")).toBeInTheDocument();
    expect(screen.queryByText("Buy & Hold (단순보유)")).not.toBeInTheDocument();
    expect(screen.getByText("Drawdown (손실 폭)")).toBeInTheDocument();
  });

  it("renders ChartLegend with BH when buyAndHoldCurve has data (Sprint 34 BL-175)", () => {
    // backend 가 정확 BH curve 제공 시 ChartLegend BH 항목 visible + BH series 렌더.
    const BH_CURVE: EquityPoint[] = [
      { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
      { timestamp: "2026-01-02T00:00:00Z", value: 10100 },
      { timestamp: "2026-01-03T00:00:00Z", value: 10250 },
    ];
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        initialCapital={10000}
        buyAndHoldCurve={BH_CURVE}
      />,
    );

    expect(screen.getByRole("list", { name: "차트 범례" })).toBeInTheDocument();
    expect(screen.getByText("Equity (자본 곡선)")).toBeInTheDocument();
    expect(screen.getByText("Buy & Hold (단순보유)")).toBeInTheDocument();
    expect(screen.getByText("Drawdown (손실 폭)")).toBeInTheDocument();
  });

  it("hides BH series when buyAndHoldCurve is empty array (fail-closed BE response)", () => {
    // BE 가 OHLCV invalid close 발견 시 None → FE schema 가 null 로 받음.
    // 빈 배열도 동일 처리 (defensive — schema 변경 시 보호).
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        initialCapital={10000}
        buyAndHoldCurve={[]}
      />,
    );

    expect(screen.queryByText("Buy & Hold (단순보유)")).not.toBeInTheDocument();
  });

  it("computes trade markers automatically (entry + exit) for Equity pane", () => {
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        trades={TRADES}
        initialCapital={10000}
      />,
    );

    // Equity pane line series 의 setMarkers 호출 — entry + exit = 2 markers.
    // (drawdown pane 도 line series 가 있지만 markers prop 미전달 → setMarkers([]) 호출됨)
    // 가장 길이가 큰 marker call 이 trade markers 라고 가정.
    const longestCall = lineSeriesMarkerCalls.reduce<ChartMarker[]>(
      (acc, cur) => (cur.length > acc.length ? cur : acc),
      [],
    );
    expect(longestCall.length).toBe(2);
    // entry = arrowUp (long).
    expect(longestCall.some((m) => m.shape === "arrowUp")).toBe(true);
    // exit = circle.
    expect(longestCall.some((m) => m.shape === "circle")).toBe(true);
  });

  it("merges extraMarkers with auto-computed trade markers (Worker C hook)", () => {
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        trades={TRADES}
        initialCapital={10000}
        extraMarkers={EXTRA_MARKERS}
      />,
    );

    // auto markers (entry + exit = 2) + extraMarkers (1) = 3.
    const longestCall = lineSeriesMarkerCalls.reduce<ChartMarker[]>(
      (acc, cur) => (cur.length > acc.length ? cur : acc),
      [],
    );
    expect(longestCall.length).toBe(3);
    // extraMarker text "TP" 포함 확인.
    expect(longestCall.some((m) => m.text === "TP")).toBe(true);
  });

  it("respects 60/40 height ratio (top=216, bottom=144 for height=360)", () => {
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        initialCapital={10000}
        height={360}
      />,
    );

    // 첫 createChart = top pane, 두번째 = bottom pane.
    const top = createChartMock.mock.calls[0]![1] as { height: number };
    const bottom = createChartMock.mock.calls[1]![1] as { height: number };
    expect(top.height).toBe(216); // 360 * 0.6
    expect(bottom.height).toBe(144); // 360 * 0.4
  });

  it("has accessible group role and aria-label", () => {
    render(<EquityChartV2 equityCurve={EQUITY} initialCapital={10000} />);

    const group = screen.getByRole("group", {
      name: /백테스트 자본 곡선/,
    });
    expect(group).toBeInTheDocument();
  });
});
