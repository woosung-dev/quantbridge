// 설정 요약 사이드 — C 이식(W3-A) 백드 행 + 제출 액션 + 무데이터 셀 테스트.
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SetupSummaryAside } from "@/app/(dashboard)/backtests/_components/setup-summary-aside";

describe("SetupSummaryAside — C 이식(W3-A)", () => {
  it("formValues 변경 시 백드 요약 행이 갱신된다", () => {
    const { rerender } = render(
      <SetupSummaryAside
        formId="test-form"
        strategyName="MA Crossover"
        formValues={{
          symbol: "BTC/USDT",
          timeframe: "1h",
          period_start: "2025-01-01",
          period_end: "2025-07-01",
          initial_capital: 10000,
          fees_pct: 0.001,
          slippage_pct: 0.0005,
          fill_timing: "bar_close",
          default_qty_type: "strategy.percent_of_equity",
          default_qty_value: 10,
          sizing_source: "manual",
        }}
      />,
    );

    expect(screen.getByTestId("setup-summary-aside")).toBeInTheDocument();
    expect(screen.getByTestId("summary-row-전략")).toHaveTextContent("MA Crossover");
    expect(screen.getByTestId("summary-row-심볼")).toHaveTextContent("BTC/USDT");
    expect(screen.getByTestId("summary-row-포지션 사이징")).toHaveTextContent(
      "10% · 자기자본",
    );
    // 수수료는 소수 저장값을 백분율로 파생 렌더한다.
    expect(screen.getByTestId("summary-row-수수료")).toHaveTextContent(
      "테이커 0.1% · 양방향",
    );

    rerender(
      <SetupSummaryAside
        formId="test-form"
        strategyName="RSI Strategy"
        formValues={{
          symbol: "ETH/USDT",
          timeframe: "4h",
          period_start: "2025-01-01",
          period_end: "2025-07-01",
          initial_capital: 5000,
          fees_pct: 0.001,
          slippage_pct: 0.0005,
          fill_timing: "next_bar_open",
          default_qty_type: "strategy.percent_of_equity",
          default_qty_value: 50,
          sizing_source: "manual",
        }}
      />,
    );

    expect(screen.getByTestId("summary-row-전략")).toHaveTextContent("RSI Strategy");
    expect(screen.getByTestId("summary-row-심볼")).toHaveTextContent("ETH/USDT");
    expect(screen.getByTestId("summary-row-포지션 사이징")).toHaveTextContent(
      "50% · 자기자본",
    );
    expect(screen.getByTestId("summary-row-체결 시점")).toHaveTextContent(
      "시그널 다음 봉 시가",
    );
  });

  it("기간과 타임프레임이 있으면 봉 수를 순수 파생으로 렌더한다 (181일 × 24)", () => {
    render(
      <SetupSummaryAside
        formId="test-form"
        formValues={{
          timeframe: "1h",
          period_start: "2025-01-01",
          period_end: "2025-07-01",
        }}
      />,
    );

    // 181일 × 24 봉/일 = 4,344개
    expect(screen.getByTestId("summary-row-기간")).toHaveTextContent(/181일\)/);
    expect(screen.getByTestId("summary-row-봉 수")).toHaveTextContent("4,344개");
  });

  it("기간이 없으면 봉 수는 무데이터 셀(—) + title 이유", () => {
    render(<SetupSummaryAside formId="test-form" formValues={{}} />);
    const cell = screen.getByTestId("summary-row-봉 수");
    expect(cell).toHaveTextContent("—");
    expect(cell.getAttribute("title")).toMatch(/봉 수를 계산/);
    // 추정 소요 시간 카드는 제거됐다(§4.9 서버 미보고 값 미렌더).
    expect(screen.queryByTestId("summary-runtime-card")).not.toBeInTheDocument();
  });

  it("제출 버튼은 폼과 연결되고 submitting 시 비활성화된다", () => {
    const { rerender } = render(
      <SetupSummaryAside formId="bt-form" formValues={{}} submitting={false} />,
    );
    const btn = screen.getByTestId("backtest-submit") as HTMLButtonElement;
    expect(btn.getAttribute("form")).toBe("bt-form");
    expect(btn.disabled).toBe(false);

    rerender(
      <SetupSummaryAside formId="bt-form" formValues={{}} submitting={true} />,
    );
    expect((screen.getByTestId("backtest-submit") as HTMLButtonElement).disabled).toBe(
      true,
    );
  });

  it("검증 오류가 있으면 실행 전 경고 문구를 띄운다", () => {
    render(
      <SetupSummaryAside formId="bt-form" formValues={{}} errorCount={2} />,
    );
    const warn = screen.getByTestId("summary-validation-warn");
    expect(warn).toHaveTextContent("입력값 2건");
  });
});
