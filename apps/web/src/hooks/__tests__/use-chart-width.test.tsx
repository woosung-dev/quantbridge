import { StrictMode } from "react";
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useChartWidth } from "../use-chart-width";

function Probe({ visible = true }: { visible?: boolean }) {
  const { wrapperRef, hasWidth } = useChartWidth();
  return (
    <>
      {visible ? <div ref={wrapperRef} data-testid="chart" /> : null}
      <output>{hasWidth ? "ready" : "waiting"}</output>
    </>
  );
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("useChartWidth", () => {
  it("빈 데이터 뒤에 DOM이 나타나면 그 시점에 측정한다", () => {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      width: 320,
    } as DOMRect);
    const { rerender } = render(<Probe visible={false} />);
    expect(screen.getByText("waiting")).toBeInTheDocument();
    rerender(<Probe />);
    expect(screen.getByText("ready")).toBeInTheDocument();
  });

  it("숨겨진 차트가 표시되면 준비하고 관찰자를 해제한다", () => {
    let notify: ResizeObserverCallback | undefined;
    const disconnect = vi.fn();
    const observe = vi.fn();
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(callback: ResizeObserverCallback) {
          notify = callback;
        }
        observe = observe;
        disconnect = disconnect;
      },
    );
    const { unmount } = render(<Probe />);
    expect(screen.getByText("waiting")).toBeInTheDocument();
    expect(observe).toHaveBeenCalledWith(screen.getByTestId("chart"));
    act(() =>
      notify?.([{ contentRect: { width: 320 } } as ResizeObserverEntry], {} as ResizeObserver),
    );
    expect(screen.getByText("ready")).toBeInTheDocument();
    expect(disconnect).toHaveBeenCalled();
    unmount();
    expect(disconnect).toHaveBeenCalledTimes(2);
  });

  it("크기 측정 전 제거하거나 StrictMode가 재연결해도 관찰자를 남기지 않는다", () => {
    const observers: { observe: ReturnType<typeof vi.fn>; disconnect: ReturnType<typeof vi.fn> }[] =
      [];
    vi.stubGlobal(
      "ResizeObserver",
      class {
        observe = vi.fn();
        disconnect = vi.fn();
        constructor() {
          observers.push(this);
        }
      },
    );
    const { rerender } = render(
      <StrictMode>
        <Probe />
      </StrictMode>,
    );
    rerender(
      <StrictMode>
        <Probe visible={false} />
      </StrictMode>,
    );
    expect(observers.length).toBeGreaterThan(0);
    expect(observers.every((observer) => observer.disconnect.mock.calls.length > 0)).toBe(true);
  });

  it("ResizeObserver가 없는 환경에서 너비 0이면 placeholder를 유지한다", () => {
    vi.stubGlobal("ResizeObserver", undefined);
    render(<Probe />);
    expect(screen.getByText("waiting")).toBeInTheDocument();
  });
});
