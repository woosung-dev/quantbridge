// 설정 요약 카드 row 갱신 테스트 — Sprint 42-polish W4
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SetupSummaryAside } from "../setup-summary-aside";

describe("SetupSummaryAside", () => {
  it("formValues 변경 시 row 가 갱신됨", () => {
    const { rerender } = render(
      <SetupSummaryAside
        strategyName="MA Crossover"
        formValues={{
          symbol: "BTC/USDT",
          period_start: "2025-01-01",
          period_end: "2025-07-01",
          initial_capital: 10000,
          fees_pct: 0.001,
          slippage_pct: 0.0005,
          default_qty_type: "strategy.percent_of_equity",
          default_qty_value: 10,
          sizing_source: "manual",
        }}
      />,
    );

    expect(screen.getByTestId("setup-summary-aside")).toBeInTheDocument();
    expect(screen.getByTestId("summary-row-전략")).toHaveTextContent(
      "MA Crossover",
    );
    expect(screen.getByTestId("summary-row-심볼")).toHaveTextContent(
      "BTC/USDT",
    );
    expect(screen.getByTestId("summary-row-포지션 사이즈")).toHaveTextContent(
      "10% (자기자본)",
    );

    rerender(
      <SetupSummaryAside
        strategyName="RSI Strategy"
        formValues={{
          symbol: "ETH/USDT",
          period_start: "2025-01-01",
          period_end: "2025-07-01",
          initial_capital: 5000,
          fees_pct: 0.001,
          slippage_pct: 0.0005,
          default_qty_type: "strategy.percent_of_equity",
          default_qty_value: 50,
          sizing_source: "manual",
        }}
      />,
    );

    expect(screen.getByTestId("summary-row-전략")).toHaveTextContent(
      "RSI Strategy",
    );
    expect(screen.getByTestId("summary-row-심볼")).toHaveTextContent(
      "ETH/USDT",
    );
    expect(screen.getByTestId("summary-row-포지션 사이즈")).toHaveTextContent(
      "50% (자기자본)",
    );
  });

  it("runtime 카드 amber 강조 + 휴리스틱 출력", () => {
    render(
      <SetupSummaryAside
        formValues={{
          period_start: "2025-01-01",
          period_end: "2025-07-01",
        }}
      />,
    );

    const runtime = screen.getByTestId("summary-runtime-card");
    expect(runtime).toBeInTheDocument();
    expect(runtime.textContent).toMatch(/예상 실행 시간/);
    expect(runtime.textContent).toMatch(/~\d+\.\d+초/);
  });

  it("기간 누락 시 placeholder runtime 출력", () => {
    render(<SetupSummaryAside formValues={{}} />);
    expect(screen.getByTestId("summary-runtime-card")).toHaveTextContent(
      "~3.2초",
    );
  });
});
