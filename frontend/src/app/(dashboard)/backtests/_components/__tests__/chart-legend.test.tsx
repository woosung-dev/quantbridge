import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChartLegend } from "../chart-legend";

describe("ChartLegend (Sprint 32-B BL-169)", () => {
  it("renders all three legend items by default (Equity / Buy & Hold / Drawdown)", () => {
    render(<ChartLegend />);

    // role=list + 3 listitems.
    const legend = screen.getByRole("list", { name: "차트 범례" });
    expect(legend).toBeInTheDocument();

    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(3);

    // 라벨 텍스트 확인 — 사용자 이해도 직접 보강.
    expect(screen.getByText("Equity (자본 곡선)")).toBeInTheDocument();
    expect(screen.getByText("Buy & Hold (단순보유)")).toBeInTheDocument();
    expect(screen.getByText("Drawdown (손실 폭)")).toBeInTheDocument();
  });

  it("hides Buy & Hold item when showBenchmark=false", () => {
    render(<ChartLegend showBenchmark={false} />);

    expect(screen.getByText("Equity (자본 곡선)")).toBeInTheDocument();
    expect(screen.queryByText("Buy & Hold (단순보유)")).not.toBeInTheDocument();
    expect(screen.getByText("Drawdown (손실 폭)")).toBeInTheDocument();
  });

  it("hides Drawdown item when showDrawdown=false", () => {
    render(<ChartLegend showDrawdown={false} />);

    expect(screen.getByText("Equity (자본 곡선)")).toBeInTheDocument();
    expect(screen.getByText("Buy & Hold (단순보유)")).toBeInTheDocument();
    expect(screen.queryByText("Drawdown (손실 폭)")).not.toBeInTheDocument();
  });

  it("each legend item has descriptive aria-label for accessibility", () => {
    render(<ChartLegend />);

    expect(
      screen.getByLabelText("Equity (자본 곡선): 실선 녹색"),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Buy & Hold 벤치마크: 점선 파란색"),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Drawdown (손실 폭): 빨간 영역"),
    ).toBeInTheDocument();
  });

  it("accepts custom className", () => {
    const { container } = render(<ChartLegend className="custom-test-cls" />);
    expect(container.querySelector(".custom-test-cls")).not.toBeNull();
  });
});
