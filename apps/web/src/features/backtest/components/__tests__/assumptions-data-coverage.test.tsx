import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AssumptionsCard } from "../assumptions-card";

describe("실제 데이터 구간", () => {
  it("중간 누락이 있으면 양 끝이 같아도 불완전한 결과임을 알린다", () => {
    render(
      <AssumptionsCard
        initialCapital={10000}
        periodStart="2024-01-01T00:00:00Z"
        periodEnd="2024-01-01T04:00:00Z"
        dataCoverage={{
          actual_start: "2024-01-01T00:00:00Z",
          actual_end: "2024-01-01T04:00:00Z",
          bar_count: 4,
          expected_bars: 5,
          missing_bars: 1,
        }}
      />,
    );
    expect(screen.getByText("요청 기간")).toBeVisible();
    expect(screen.getByText("실제 데이터 구간")).toBeVisible();
    expect(screen.getByText("4 / 5")).toBeVisible();
    expect(screen.getByTestId("backtest-data-incomplete-note")).toHaveTextContent(
      "전체 요청 기간의 성과를 보장하지 않습니다",
    );
  });
  it("과거 실행의 실제 구간을 요청 기간에서 추정하지 않는다", () => {
    render(<AssumptionsCard initialCapital={10000} dataCoverage={null} />);
    expect(screen.getByText(/미기록 — 요청 기간과 같다고 보장할 수 없습니다/)).toBeVisible();
    expect(screen.queryByTestId("backtest-data-incomplete-note")).not.toBeInTheDocument();
  });
  it("완전한 데이터에는 누락 경고가 없다", () => {
    render(
      <AssumptionsCard
        initialCapital={10000}
        dataCoverage={{
          actual_start: "2024-01-01T00:00:00Z",
          actual_end: "2024-01-01T04:00:00Z",
          bar_count: 5,
          expected_bars: 5,
          missing_bars: 0,
        }}
      />,
    );
    expect(screen.getByText("0개")).toBeVisible();
    expect(screen.queryByTestId("backtest-data-incomplete-note")).not.toBeInTheDocument();
  });
});
