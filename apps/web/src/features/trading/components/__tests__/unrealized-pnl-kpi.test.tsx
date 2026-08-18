// 미실현 손익 KPI — pos/neg 손익 톤(0 중립) 판별 가드.
// 프로토타입 screen-01:1188 은 kpi-value mono pos 로 물들인다. 옵티마이저 pnlTone 과
// 같은 0-중립 규약: 양수 pos / 음수 neg / 0·무데이터 중립.
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useUnrealizedPnlEstimate } from "@/features/live-sessions";

vi.mock("@/features/live-sessions", () => ({
  useUnrealizedPnlEstimate: vi.fn(),
}));

import { UnrealizedPnlKpi } from "../unrealized-pnl-kpi";

const mockEstimate = vi.mocked(useUnrealizedPnlEstimate);

function estimate(total: number | null) {
  return { total, isEstimating: false, latestTs: total === null ? null : Date.now() };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  mockEstimate.mockReset();
});

describe("UnrealizedPnlKpi — 손익 톤 (0 중립)", () => {
  it("양수 손익은 pos 톤으로 물들인다", () => {
    mockEstimate.mockReturnValue(estimate(142.18));
    render(<UnrealizedPnlKpi sessions={[]} />);

    const value = screen.getByTestId("kpi-unrealized-pnl");
    expect(value).toHaveClass("pos");
    expect(value).not.toHaveClass("neg");
    expect(value).toHaveTextContent("+142.18 USDT");
  });

  it("음수 손익은 neg 톤으로 물들인다", () => {
    mockEstimate.mockReturnValue(estimate(-3.5));
    render(<UnrealizedPnlKpi sessions={[]} />);

    const value = screen.getByTestId("kpi-unrealized-pnl");
    expect(value).toHaveClass("neg");
    expect(value).not.toHaveClass("pos");
  });

  it("손익 0 은 중립 — pos 도 neg 도 칠하지 않는다", () => {
    mockEstimate.mockReturnValue(estimate(0));
    render(<UnrealizedPnlKpi sessions={[]} />);

    const value = screen.getByTestId("kpi-unrealized-pnl");
    expect(value).not.toHaveClass("pos");
    expect(value).not.toHaveClass("neg");
  });

  it("무데이터(시세 수신 대기)도 중립이다", () => {
    mockEstimate.mockReturnValue(estimate(null));
    render(<UnrealizedPnlKpi sessions={[]} />);

    const value = screen.getByTestId("kpi-unrealized-pnl");
    expect(value).toHaveTextContent("시세 수신 대기");
    expect(value).not.toHaveClass("pos");
    expect(value).not.toHaveClass("neg");
  });
});
