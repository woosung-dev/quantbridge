// RunningProgressBar — Sprint 43 W7 prototype 09 정합 검증.
// running/cancelling: indeterminate progress bar 표시 + aria-live.
// queued: pulse dot + "대기 중…" 라벨.
// 그 외 status: null 반환 (호출 측 분기 보장).

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { RunningProgressBar } from "@/app/(dashboard)/backtests/_components/running-progress-bar";

describe("RunningProgressBar", () => {
  it("status=running → indeterminate progress bar + '실행 중…' 라벨", () => {
    render(<RunningProgressBar status="running" />);
    const bar = screen.getByTestId("running-progress-bar");
    expect(bar).toBeInTheDocument();
    expect(bar).toHaveAttribute("role", "status");
    expect(bar).toHaveAttribute("aria-live", "polite");
    expect(bar).toHaveTextContent("실행 중…");
  });

  it("status=cancelling → '취소 중…' 라벨 + role=status", () => {
    render(<RunningProgressBar status="cancelling" />);
    const bar = screen.getByTestId("running-progress-bar");
    expect(bar).toHaveTextContent("취소 중…");
  });

  it("status=queued → pulse dot + '대기 중…' 라벨 (progress bar 미표시)", () => {
    render(<RunningProgressBar status="queued" />);
    expect(screen.queryByTestId("running-progress-bar")).not.toBeInTheDocument();
    const queuedNode = screen.getByTestId("queued-pulse");
    expect(queuedNode).toBeInTheDocument();
    expect(queuedNode).toHaveTextContent("대기 중…");
  });

  it("status=completed → null 반환 (호출 측 분기 보장)", () => {
    const { container } = render(<RunningProgressBar status="completed" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("status=failed/cancelled → null 반환", () => {
    const { container: failed } = render(<RunningProgressBar status="failed" />);
    expect(failed).toBeEmptyDOMElement();
    const { container: cancelled } = render(<RunningProgressBar status="cancelled" />);
    expect(cancelled).toBeEmptyDOMElement();
  });
});
