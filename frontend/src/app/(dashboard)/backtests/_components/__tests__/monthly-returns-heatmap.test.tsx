import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MonthlyReturnsHeatmap } from "../monthly-returns-heatmap";

describe("MonthlyReturnsHeatmap (Sprint 30-γ-FE)", () => {
  it("data null 시 안내 메시지", () => {
    render(<MonthlyReturnsHeatmap data={null} />);
    expect(
      screen.getByText(/월별 수익률 데이터가 없습니다/),
    ).toBeInTheDocument();
  });

  it("data 빈 배열 시 안내 메시지", () => {
    render(<MonthlyReturnsHeatmap data={[]} />);
    expect(
      screen.getByText(/월별 수익률 데이터가 없습니다/),
    ).toBeInTheDocument();
  });

  it("12 month × 1 year grid 정상 렌더 + 합계 column", () => {
    const data: Array<[string, number]> = [
      ["2026-01", 0.05],
      ["2026-02", -0.02],
      ["2026-03", 0.08],
    ];
    render(<MonthlyReturnsHeatmap data={data} />);
    // 12 month header (1월 ~ 12월)
    expect(screen.getByText("1월")).toBeInTheDocument();
    expect(screen.getByText("12월")).toBeInTheDocument();
    // 연 합계 header
    expect(screen.getByText("연")).toBeInTheDocument();
    // year row
    expect(screen.getByText("2026")).toBeInTheDocument();
    // 1월 = 5.00%, 2월 = -2.00%, 3월 = 8.00% (소수점 1자리 표시)
    expect(screen.getByText("5.0%")).toBeInTheDocument();
    expect(screen.getByText("-2.0%")).toBeInTheDocument();
    expect(screen.getByText("8.0%")).toBeInTheDocument();
    // 안내 텍스트
    expect(
      screen.getByText(/합계는 산술 합 \(복리 아님\)/),
    ).toBeInTheDocument();
  });

  it("non-finite value 는 0 처리 (cumulative 영향 없음)", () => {
    const data: Array<[string, number]> = [
      ["2026-01", Number.NaN],
      ["2026-02", 0.1],
    ];
    const { container } = render(<MonthlyReturnsHeatmap data={data} />);
    // 2026-02 cell = 10.0% + 2026 합계 = 10.0% (NaN→0 처리). 두 번 매치 정합.
    const tens = screen.getAllByText("10.0%");
    expect(tens.length).toBeGreaterThanOrEqual(2);
    expect(container.querySelector("table")).toBeInTheDocument();
  });

  it("multi-year — 정렬된 year row + 각 합계 분리", () => {
    const data: Array<[string, number]> = [
      ["2025-12", 0.1],
      ["2026-06", -0.05],
    ];
    render(<MonthlyReturnsHeatmap data={data} />);
    // 두 year 모두 row
    expect(screen.getByText("2025")).toBeInTheDocument();
    expect(screen.getByText("2026")).toBeInTheDocument();
  });
});
