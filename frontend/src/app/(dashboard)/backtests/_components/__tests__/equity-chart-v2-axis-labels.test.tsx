import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { EquityPoint } from "@/features/backtest/schemas";

import { EquityChartV2 } from "../equity-chart-v2";

// --- lightweight-charts mock ---------------------------------------------
// 본 테스트 파일은 axis label / leverage warning 분기만 검증.
// chart 인스턴스 spy 는 equity-chart-v2.test.tsx 가 담당.

interface SeriesSpy {
  setData: ReturnType<typeof vi.fn>;
  applyOptions: ReturnType<typeof vi.fn>;
  setMarkers: ReturnType<typeof vi.fn>;
}

vi.mock("lightweight-charts", () => {
  return {
    createChart: () => ({
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
    }),
  };
});

class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const EQUITY: EquityPoint[] = [
  { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
  { timestamp: "2026-01-02T00:00:00Z", value: 10500 },
];

describe("EquityChartV2 — axis labels (Sprint 32-C BL-172)", () => {
  beforeEach(() => {
    (
      globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }
    ).ResizeObserver = MockResizeObserver;
  });

  afterEach(() => {
    delete (globalThis as unknown as { ResizeObserver?: unknown })
      .ResizeObserver;
  });

  it("renders axis label bar for equity pane (USDT)", () => {
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        initialCapital={10000}
        timeframe="1h"
      />,
    );

    const equityAxis = screen.getByTestId("axis-label-bar-equity");
    expect(equityAxis).toBeInTheDocument();
    expect(equityAxis).toHaveTextContent(/USDT \(자본금\)/);
    expect(equityAxis).toHaveTextContent(/1h 단위 캔들/);
  });

  it("renders axis label bar for drawdown pane (% with default range)", () => {
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        initialCapital={10000}
        timeframe="1d"
      />,
    );

    const ddAxis = screen.getByTestId("axis-label-bar-drawdown");
    expect(ddAxis).toBeInTheDocument();
    expect(ddAxis).toHaveTextContent(/% \(자본 대비 손실 · 0 ~ -100%\)/);
    expect(ddAxis).toHaveTextContent(/1d 단위 캔들/);
  });

  it("shows leverage warning in drawdown axis when mddExceedsCapital=true", () => {
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        initialCapital={10000}
        timeframe="15m"
        mddExceedsCapital
      />,
    );

    const ddAxis = screen.getByTestId("axis-label-bar-drawdown");
    expect(ddAxis).toHaveTextContent(/leverage 시 -100% 초과 가능/);
  });

  it("hides leverage warning when mddExceedsCapital=false", () => {
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        initialCapital={10000}
        timeframe="1h"
        mddExceedsCapital={false}
      />,
    );

    const ddAxis = screen.getByTestId("axis-label-bar-drawdown");
    expect(ddAxis).not.toHaveTextContent(/leverage 시/);
  });

  it("falls back to '시간' when timeframe is undefined", () => {
    render(<EquityChartV2 equityCurve={EQUITY} initialCapital={10000} />);

    const equityAxis = screen.getByTestId("axis-label-bar-equity");
    expect(equityAxis).toHaveTextContent(/X축:\s*시간/);
    expect(equityAxis).not.toHaveTextContent(/단위 캔들/);
  });
});
