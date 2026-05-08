// Sprint 43 W10 — prototype 02 정합. 타임프레임 탭 + Buy&Hold checkbox + 드로다운 checkbox 테스트.

import { render, screen, fireEvent } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { EquityPoint } from "@/features/backtest/schemas";

import { EquityChartV2 } from "../equity-chart-v2";

// lightweight-charts mock — 본 테스트는 chart 자체보다 컨트롤 동작 검증.
vi.mock("lightweight-charts", () => ({
  createChart: () => ({
    addLineSeries: () => ({ setData: vi.fn(), applyOptions: vi.fn(), setMarkers: vi.fn() }),
    addAreaSeries: () => ({ setData: vi.fn(), applyOptions: vi.fn(), setMarkers: vi.fn() }),
    removeSeries: vi.fn(),
    applyOptions: vi.fn(),
    remove: vi.fn(),
    timeScale: () => ({ fitContent: vi.fn() }),
  }),
}));

class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const EQUITY: EquityPoint[] = Array.from({ length: 200 }, (_, i) => ({
  timestamp: new Date(2026, 0, 1 + i).toISOString(),
  value: 10000 + i * 50,
}));

const BH: EquityPoint[] = Array.from({ length: 200 }, (_, i) => ({
  timestamp: new Date(2026, 0, 1 + i).toISOString(),
  value: 10000 + i * 30,
}));

describe("EquityChartV2 — Sprint 43 W10 prototype 02 controls", () => {
  beforeEach(() => {
    (
      globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }
    ).ResizeObserver = MockResizeObserver;
  });

  afterEach(() => {
    delete (globalThis as unknown as { ResizeObserver?: unknown }).ResizeObserver;
  });

  it("타임프레임 탭 4개 (1M / 3M / 6M / 전체) 가 렌더되고 전체가 디폴트 active 다", () => {
    render(<EquityChartV2 equityCurve={EQUITY} initialCapital={10000} />);

    const tablist = screen.getByRole("tablist", { name: "차트 기간 선택" });
    expect(tablist).toBeInTheDocument();

    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(4);
    expect(tabs.map((t) => t.textContent)).toEqual(["1M", "3M", "6M", "전체"]);

    // 전체 탭이 디폴트 active.
    const allTab = screen.getByRole("tab", { name: "전체" });
    expect(allTab.getAttribute("aria-selected")).toBe("true");
  });

  it("타임프레임 탭 클릭 시 aria-selected 가 갱신된다", () => {
    render(<EquityChartV2 equityCurve={EQUITY} initialCapital={10000} />);

    const oneMonth = screen.getByRole("tab", { name: "1M" });
    fireEvent.click(oneMonth);
    expect(oneMonth.getAttribute("aria-selected")).toBe("true");

    const all = screen.getByRole("tab", { name: "전체" });
    expect(all.getAttribute("aria-selected")).toBe("false");
  });

  it("Buy & Hold 체크박스는 buyAndHoldCurve 가 있을 때만 표시된다", () => {
    const { rerender } = render(
      <EquityChartV2 equityCurve={EQUITY} initialCapital={10000} />,
    );

    expect(
      screen.queryByRole("checkbox", { name: "Buy and Hold 비교 표시" }),
    ).not.toBeInTheDocument();

    rerender(
      <EquityChartV2
        equityCurve={EQUITY}
        initialCapital={10000}
        buyAndHoldCurve={BH}
      />,
    );

    const bhCheckbox = screen.getByRole("checkbox", {
      name: "Buy and Hold 비교 표시",
    });
    expect(bhCheckbox).toBeInTheDocument();
    expect((bhCheckbox as HTMLInputElement).checked).toBe(true);
  });

  it("드로다운 영역 체크박스는 항상 표시되고 디폴트 ON 이다", () => {
    render(<EquityChartV2 equityCurve={EQUITY} initialCapital={10000} />);

    const ddCheckbox = screen.getByRole("checkbox", {
      name: "드로다운 영역 표시",
    });
    expect(ddCheckbox).toBeInTheDocument();
    expect((ddCheckbox as HTMLInputElement).checked).toBe(true);

    fireEvent.click(ddCheckbox);
    expect((ddCheckbox as HTMLInputElement).checked).toBe(false);
  });

  it("BH checkbox 를 끄면 ChartLegend 에서 BH 항목이 hide 된다", () => {
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        initialCapital={10000}
        buyAndHoldCurve={BH}
      />,
    );

    expect(screen.getByText("Buy & Hold (단순보유)")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("checkbox", { name: "Buy and Hold 비교 표시" }),
    );

    expect(screen.queryByText("Buy & Hold (단순보유)")).not.toBeInTheDocument();
  });

  it("aria-live status 영역이 현재 컨트롤 상태를 announce 한다", () => {
    render(
      <EquityChartV2
        equityCurve={EQUITY}
        initialCapital={10000}
        buyAndHoldCurve={BH}
      />,
    );

    const status = screen.getByRole("status");
    expect(status.textContent).toContain("기간 전체");
    expect(status.textContent).toContain("Buy & Hold 표시");
    expect(status.textContent).toContain("드로다운 표시");
  });
});
