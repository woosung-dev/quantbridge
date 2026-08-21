// 워크스페이스 자산 곡선 카드 테스트 (S7) — 3상태 렌더 + 렌더된 차트의 축 모드 실증.
// EquityPane 테스트(backtests)의 lightweight-charts mock 관례를 그대로 따른다.
// 핵심: 실제 렌더 경로에서 createChart 가 로그·백분율 축을 켜지 않고, 라인 series 가
// custom(배율 없는) priceFormat 을 받는지 확인한다.

import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ChartPoint } from "@/components/charts/trading-chart";
import { CHART_PALETTE_FALLBACK } from "@/lib/chart-tokens";

import { WorkspaceEquityCard } from "../workspace-equity-card";
import { PRICE_SCALE_MODE } from "../equity-chart-config";

// --- lightweight-charts mock (equity-pane.test.tsx 동형) ------------------

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

type RoCallback = (entries: Array<{ contentRect: { width: number } }>) => void;
class MockResizeObserver {
  cb: RoCallback;
  targets: Element[] = [];
  constructor(cb: RoCallback) {
    this.cb = cb;
  }
  observe(target: Element) {
    this.targets.push(target);
  }
  unobserve() {}
  disconnect() {
    this.targets = [];
  }
}

const CURVE: ChartPoint[] = [
  { time: 1700000000, value: 0 },
  { time: 1700003600, value: 42.5 },
  { time: 1700007200, value: 142.18 },
];

describe("WorkspaceEquityCard (S7)", () => {
  beforeEach(() => {
    createChartMock.mockClear();
    chartInstances.length = 0;
    (globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }).ResizeObserver =
      MockResizeObserver;
  });

  afterEach(() => {
    delete (globalThis as unknown as { ResizeObserver?: unknown }).ResizeObserver;
  });

  it("로딩 상태 — 스켈레톤을 그리고 차트를 만들지 않는다", async () => {
    render(<WorkspaceEquityCard data={[]} isLoading activeSessionCount={0} latestValue={0} />);
    await act(async () => {});
    expect(screen.getByTestId("equity-loading")).toBeInTheDocument();
    expect(createChartMock).not.toHaveBeenCalled();
  });

  it("빈 상태 — 곡선이 없으면 상태 박스를 그리고 차트를 만들지 않는다", async () => {
    render(
      <WorkspaceEquityCard data={[]} isLoading={false} activeSessionCount={0} latestValue={0} />,
    );
    await act(async () => {});
    const box = screen.getByTestId("equity-empty");
    expect(box).toBeInTheDocument();
    expect(box).toHaveAttribute("role", "status");
    expect(createChartMock).not.toHaveBeenCalled();
  });

  it("1점만 있으면 곡선으로 보지 않는다 (>=2 점 요구)", async () => {
    render(
      <WorkspaceEquityCard
        data={[{ time: 1700000000, value: 10 }]}
        isLoading={false}
        activeSessionCount={1}
        latestValue={10}
      />,
    );
    await act(async () => {});
    expect(screen.getByTestId("equity-empty")).toBeInTheDocument();
    expect(createChartMock).not.toHaveBeenCalled();
  });

  it("채워진 상태 — 차트를 만들고 범례에 최신값을 배율 없이 찍는다", async () => {
    render(
      <WorkspaceEquityCard
        data={CURVE}
        isLoading={false}
        activeSessionCount={2}
        latestValue={142.18}
      />,
    );
    await act(async () => {});
    expect(screen.getByTestId("equity-chart")).toBeInTheDocument();
    expect(createChartMock).toHaveBeenCalledTimes(1);
    // 범례 최신값 = 142.18 (×100 이면 14,218.00 이 됐을 것).
    expect(screen.getByText("142.18")).toBeInTheDocument();
  });

  it("렌더된 차트가 로그·백분율 축을 켜지 않는다 (선형 절대값 축)", async () => {
    render(
      <WorkspaceEquityCard
        data={CURVE}
        isLoading={false}
        activeSessionCount={2}
        latestValue={142.18}
      />,
    );
    await act(async () => {});

    const opts = createChartMock.mock.calls[0]![1] as {
      rightPriceScale?: { mode?: number };
      leftPriceScale?: { mode?: number };
    };
    // TradingChart 는 rightPriceScale.mode 를 설정하지 않는다 → lightweight-charts 기본 Normal(0).
    // 어느 쪽 축이 설정되더라도 로그(1)/백분율(2) 이 아님을 못박는다.
    const rightMode = opts.rightPriceScale?.mode;
    const leftMode = opts.leftPriceScale?.mode;
    for (const mode of [rightMode, leftMode]) {
      if (mode !== undefined) {
        expect(mode).not.toBe(PRICE_SCALE_MODE.LOGARITHMIC);
        expect(mode).not.toBe(PRICE_SCALE_MODE.PERCENTAGE);
      }
    }
  });

  it("라인 series 가 custom(배율 없는) priceFormat 과 equity 색을 받는다", async () => {
    render(
      <WorkspaceEquityCard
        data={CURVE}
        isLoading={false}
        activeSessionCount={2}
        latestValue={142.18}
      />,
    );
    await act(async () => {});

    const chart = chartInstances[0]!;
    expect(chart.addLineSeries).toHaveBeenCalledTimes(1);
    const lineOpts = chart.addLineSeries.mock.calls[0]![0] as {
      color?: string;
      priceFormat?: { type?: string; formatter?: (v: number) => string };
    };
    expect(lineOpts.color).toBe(CHART_PALETTE_FALLBACK.equity);
    expect(lineOpts.priceFormat?.type).toBe("custom");
    expect(lineOpts.priceFormat?.type).not.toBe("percent");
    // 포매터가 배율을 곱이지 않는다.
    expect(lineOpts.priceFormat?.formatter?.(100)).toBe("100.00");
  });
});
