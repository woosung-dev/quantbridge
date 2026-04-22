import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { EquityPoint } from "@/features/backtest/schemas";
import { EquityChart } from "../equity-chart";

// 테스트 데이터: 3 포인트 equity curve
const POINTS: EquityPoint[] = [
  { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
  { timestamp: "2026-01-02T00:00:00Z", value: 10200 },
  { timestamp: "2026-01-03T00:00:00Z", value: 10500 },
];

// jsdom 의 ResizeObserver mock — observer 콜백을 테스트에서 직접 발화시키기 위함.
type RoCallback = (entries: Array<{ contentRect: { width: number } }>) => void;
let roInstances: Array<{ cb: RoCallback; targets: Element[]; disconnect: () => void }> = [];

class MockResizeObserver {
  cb: RoCallback;
  targets: Element[] = [];
  constructor(cb: RoCallback) {
    this.cb = cb;
    roInstances.push({
      cb,
      targets: this.targets,
      disconnect: () => {
        this.targets = [];
      },
    });
  }
  observe(target: Element) {
    this.targets.push(target);
  }
  unobserve() {}
  disconnect() {
    this.targets = [];
  }
}

describe("EquityChart", () => {
  beforeEach(() => {
    roInstances = [];
    // 기본은 ResizeObserver 미정의 (jsdom 기본 동작 — width 0 으로 차트 미마운트)
    delete (globalThis as unknown as { ResizeObserver?: unknown }).ResizeObserver;
  });

  afterEach(() => {
    delete (globalThis as unknown as { ResizeObserver?: unknown }).ResizeObserver;
  });

  it("renders empty state when no points", () => {
    render(<EquityChart points={[]} />);
    expect(screen.getByText(/Equity 데이터가 없습니다/)).toBeInTheDocument();
  });

  it("does not mount ResponsiveContainer when wrapper width is 0 (no width(-1) warning)", () => {
    // jsdom 기본: getBoundingClientRect width === 0 + ResizeObserver 미정의
    // → 차트가 mount 되어선 안 되고 placeholder 만 렌더.
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const { container } = render(<EquityChart points={POINTS} />);

    // Recharts ResponsiveContainer 는 div.recharts-responsive-container 로 mount.
    // 측정 전 placeholder 단계에서는 이 노드가 존재하지 않아야 함.
    expect(
      container.querySelector(".recharts-responsive-container"),
    ).toBeNull();
    // 동일 크기 placeholder 가 렌더되어 layout shift 가 없어야 함.
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();

    // width(-1) 회귀 경고 0건 확인 (recharts 가 emit 하는 정확한 문자열).
    const hasWarn = warnSpy.mock.calls.some((args) =>
      args.some((a) => typeof a === "string" && /width\(-1\)/.test(a)),
    );
    const hasErr = errSpy.mock.calls.some((args) =>
      args.some((a) => typeof a === "string" && /width\(-1\)/.test(a)),
    );
    expect(hasWarn).toBe(false);
    expect(hasErr).toBe(false);

    warnSpy.mockRestore();
    errSpy.mockRestore();
  });

  it("mounts ResponsiveContainer when ResizeObserver reports width >= 1", () => {
    // ResizeObserver 가 width 800 을 발화하는 환경 — 실제 브라우저 분기를 등가로 검증.
    (globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }).ResizeObserver =
      MockResizeObserver;

    // 주의: jsdom 은 layout 엔진이 없어 ResponsiveContainer 자체 내부 측정에서
    // 별도 width(-1) warning 을 발생시킬 수 있음 (이 테스트의 책임 밖).
    // 본 테스트는 "wrapper width 측정 후 차트 mount 분기로 정확히 진입한다" 만 검증.
    // 실제 브라우저 환경에서의 warning 0건 확인은 Phase 4 Playwright live smoke 가 담당.
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const { container } = render(<EquityChart points={POINTS} />);

    // 1차 측정 시점에는 jsdom rect.width === 0 → 차트 미마운트.
    expect(
      container.querySelector(".recharts-responsive-container"),
    ).toBeNull();
    // wrapper 가 ResizeObserver 에 등록되어야 함.
    expect(roInstances).toHaveLength(1);

    // ResizeObserver 콜백을 width=800 으로 발화 → setHasWidth(true) → 차트 mount.
    act(() => {
      roInstances[0]!.cb([{ contentRect: { width: 800 } }]);
    });

    // 차트가 mount 되어야 함 (mount 분기 진입 확인).
    expect(
      container.querySelector(".recharts-responsive-container"),
    ).not.toBeNull();
    // placeholder 는 사라져야 함.
    expect(container.querySelector('[aria-busy="true"]')).toBeNull();

    warnSpy.mockRestore();
    errSpy.mockRestore();
  });
});
