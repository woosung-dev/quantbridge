// EquityChartV2 — Sprint 37 BL-184: equity / Buy&Hold curve 가 PnL 기준 (시작=0)
// 으로 정규화되어 lightweight-charts 에 전달되는지 검증.
//
// 기존 equity-chart-v2.test.tsx 와 mock 분리 (setData 캡처 spy 재사용 어려워
// 신규 파일). BE absolute curve → FE normalize → setData([0, +200, +500]) 흐름.

import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { EquityPoint } from "@/features/backtest/schemas";

import { EquityChartV2 } from "../equity-chart-v2";

interface SeriesSpy {
  setData: ReturnType<typeof vi.fn>;
  applyOptions: ReturnType<typeof vi.fn>;
  setMarkers: ReturnType<typeof vi.fn>;
}

const lineSeriesSetDataCalls: Array<Array<{ time: unknown; value: number }>> = [];

vi.mock("lightweight-charts", () => {
  return {
    createChart: () => {
      const chart = {
        addLineSeries: vi.fn((): SeriesSpy => {
          const series: SeriesSpy = {
            setData: vi.fn((data: unknown) => {
              lineSeriesSetDataCalls.push(
                data as Array<{ time: unknown; value: number }>,
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
      return chart;
    },
  };
});

class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const EQUITY: EquityPoint[] = [
  { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
  { timestamp: "2026-01-02T00:00:00Z", value: 10200 },
  { timestamp: "2026-01-03T00:00:00Z", value: 10500 },
];

const BH_CURVE: EquityPoint[] = [
  { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
  { timestamp: "2026-01-02T00:00:00Z", value: 10100 },
  { timestamp: "2026-01-03T00:00:00Z", value: 10250 },
];

describe("EquityChartV2 — BL-184 PnL normalization (시작=0)", () => {
  beforeEach(() => {
    lineSeriesSetDataCalls.length = 0;
    (
      globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }
    ).ResizeObserver = MockResizeObserver;
  });

  afterEach(() => {
    delete (globalThis as unknown as { ResizeObserver?: unknown })
      .ResizeObserver;
  });

  it("Equity curve 의 첫 point value 가 0 으로 정규화되어 setData 에 전달", () => {
    render(<EquityChartV2 equityCurve={EQUITY} initialCapital={10000} />);

    // setData 호출 중 길이가 EQUITY 와 같은 것 = equity series.
    const equitySetData = lineSeriesSetDataCalls.find(
      (call) => call.length === EQUITY.length,
    );
    expect(equitySetData).toBeDefined();
    expect(equitySetData![0]!.value).toBe(0);
    expect(equitySetData![1]!.value).toBe(200);
    expect(equitySetData![2]!.value).toBe(500);
  });

  it("Buy & Hold curve 도 PnL 기준으로 정규화", () => {
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        initialCapital={10000}
        buyAndHoldCurve={BH_CURVE}
      />,
    );

    // 두 line series setData 호출 — equity (첫=0,200,500) + BH (첫=0,100,250).
    // 각 series 가 같은 길이라 둘 다 매칭. value 첫 element 가 0 인지 검증.
    const sameLengthCalls = lineSeriesSetDataCalls.filter(
      (call) => call.length === EQUITY.length,
    );
    expect(sameLengthCalls.length).toBeGreaterThanOrEqual(2);
    for (const call of sameLengthCalls) {
      expect(call[0]!.value).toBe(0);
    }

    // BH 의 두번째 / 세번째 = +100, +250 검증.
    const bhCall = sameLengthCalls.find(
      (call) => call[1]!.value === 100 && call[2]!.value === 250,
    );
    expect(bhCall).toBeDefined();
  });

  it("buyAndHoldCurve null fallback — 기존 회귀 안전", () => {
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        initialCapital={10000}
        buyAndHoldCurve={null}
      />,
    );
    // BH series 는 추가되지 않아야 — BH normalize 도 호출 안 됨.
    // Equity series 만 정규화 setData 호출 (첫=0).
    const equityCall = lineSeriesSetDataCalls.find(
      (call) => call.length === EQUITY.length,
    );
    expect(equityCall).toBeDefined();
    expect(equityCall![0]!.value).toBe(0);
  });

  it("buyAndHoldCurve empty array fallback", () => {
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        initialCapital={10000}
        buyAndHoldCurve={[]}
      />,
    );
    const equityCall = lineSeriesSetDataCalls.find(
      (call) => call.length === EQUITY.length,
    );
    expect(equityCall).toBeDefined();
    expect(equityCall![0]!.value).toBe(0);
  });
});
