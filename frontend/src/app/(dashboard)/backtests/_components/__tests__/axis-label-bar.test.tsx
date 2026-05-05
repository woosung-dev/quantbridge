import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AxisLabelBar } from "../axis-label-bar";

describe("AxisLabelBar (Sprint 32-C BL-172)", () => {
  it("renders Y-axis and X-axis labels for equity variant", () => {
    render(
      <AxisLabelBar
        yAxisLabel="USDT (자본금)"
        xAxisLabel="시간 · 1h 단위 캔들"
        variant="equity"
      />,
    );

    expect(screen.getByTestId("axis-label-bar-equity")).toBeInTheDocument();
    expect(screen.getByTestId("y-axis-label")).toHaveTextContent(
      /USDT \(자본금\)/,
    );
    expect(screen.getByTestId("x-axis-label")).toHaveTextContent(
      /1h 단위 캔들/,
    );
  });

  it("renders drawdown variant with red dot color", () => {
    render(
      <AxisLabelBar
        yAxisLabel="% (자본 대비 손실 · 0 ~ -100%)"
        xAxisLabel="시간 · 1d 단위 캔들"
        variant="drawdown"
      />,
    );

    expect(screen.getByTestId("axis-label-bar-drawdown")).toBeInTheDocument();
    expect(screen.getByTestId("y-axis-label")).toHaveTextContent(
      /% \(자본 대비 손실/,
    );
  });

  it("includes leverage warning when y-axis label is configured for it", () => {
    render(
      <AxisLabelBar
        yAxisLabel="% (자본 대비 손실 · leverage 시 -100% 초과 가능)"
        xAxisLabel="시간"
        variant="drawdown"
      />,
    );

    expect(screen.getByTestId("y-axis-label")).toHaveTextContent(
      /leverage 시 -100% 초과 가능/,
    );
  });

  it("has accessible group role with label", () => {
    render(
      <AxisLabelBar
        yAxisLabel="USDT"
        xAxisLabel="시간"
        variant="equity"
      />,
    );

    const group = screen.getByRole("group", {
      name: /자본 곡선 차트 축 단위 안내/,
    });
    expect(group).toBeInTheDocument();
  });

  it("has accessible group role with drawdown label", () => {
    render(
      <AxisLabelBar
        yAxisLabel="%"
        xAxisLabel="시간"
        variant="drawdown"
      />,
    );

    const group = screen.getByRole("group", {
      name: /Drawdown 차트 축 단위 안내/,
    });
    expect(group).toBeInTheDocument();
  });
});
