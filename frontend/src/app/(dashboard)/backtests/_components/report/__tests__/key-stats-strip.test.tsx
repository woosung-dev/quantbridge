// KeyStatsStrip — 01 요약 kpi-row 4 KPI(총 수익률/순손익/최대 낙폭/샤프) + net null graceful
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { BacktestMetricsOut } from "@/features/backtest/schemas";
import { EMPTY_CELL } from "@/lib/labels";

import { KeyStatsStrip } from "@/app/(dashboard)/backtests/_components/report/key-stats-strip";

const BASE_METRICS = {
  total_return: 0.1890,
  sharpe_ratio: 1.154,
  sharpe_convention: "tv_monthly_rfr2",
  max_drawdown: -0.0252,
  win_rate: 0.9898,
  num_trades: 295,
  profit_factor: 21.343,
  annual_return_pct: 0.4328,
} as unknown as BacktestMetricsOut;

describe("KeyStatsStrip (01 요약)", () => {
  it("공용 .kpi-row 안 4 KPI(총 수익률/순손익/최대 낙폭/샤프 지수) 를 카드로 렌더", () => {
    const { container } = render(
      <KeyStatsStrip
        metrics={{
          ...BASE_METRICS,
          net_profit_abs: 1890087.72,
          total_fees: 482.16,
        } as unknown as BacktestMetricsOut}
      />,
    );
    // 시맨틱 구조 — kpi-row + card kpi 4개
    expect(container.querySelector(".kpi-row")).not.toBeNull();
    expect(container.querySelectorAll(".card.kpi")).toHaveLength(4);

    expect(screen.getByText("총 수익률")).toBeInTheDocument();
    expect(screen.getByTestId("kpi-total-return")).toHaveTextContent("+18.90%");
    expect(screen.getByText("순손익")).toBeInTheDocument();
    expect(screen.getByTestId("kpi-net-profit")).toHaveTextContent("+1,890,087.72");
    expect(screen.getByText("최대 낙폭")).toBeInTheDocument();
    expect(screen.getByTestId("kpi-max-drawdown")).toHaveTextContent("-2.52%");
    expect(screen.getByText("샤프 지수")).toBeInTheDocument();
    expect(screen.getByTestId("kpi-sharpe")).toHaveTextContent("1.15");
    expect(screen.getByText("무위험 2%/년 · 월간 수익률 기준")).toBeInTheDocument();
  });

  it("샤프 산출 불가 값은 0 대신 무데이터 표기로 렌더한다", () => {
    render(
      <KeyStatsStrip
        metrics={{
          ...BASE_METRICS,
          sharpe_ratio: 0,
          sharpe_convention: "unavailable",
        } as unknown as BacktestMetricsOut}
      />,
    );

    expect(screen.getByTestId("kpi-sharpe")).toHaveTextContent(EMPTY_CELL);
    expect(screen.getByText("변동이 없거나 기간이 짧아 산출되지 않았습니다")).toBeInTheDocument();
  });

  it("샤프 기준이 없는 구 실행은 비교 불가 각주를 렌더한다", () => {
    render(
      <KeyStatsStrip
        metrics={{
          ...BASE_METRICS,
          sharpe_convention: null,
        } as unknown as BacktestMetricsOut}
      />,
    );

    expect(screen.getByText("구 기준(봉 수익률 · 무위험 0%) - 현재 기준과 비교 불가")).toBeInTheDocument();
  });

  it("net_profit_abs null (구 백테스트) → 순손익이 % 단독으로 graceful", () => {
    render(<KeyStatsStrip metrics={BASE_METRICS} />);
    // 순손익 슬롯이 % 로 표기 (USDT 절대금액 없음)
    expect(screen.getByTestId("kpi-net-profit")).toHaveTextContent("+18.90%");
  });

  it("연환산 수익률 foot + 수수료 반영 foot 을 스키마 값으로 표기", () => {
    render(
      <KeyStatsStrip
        metrics={{
          ...BASE_METRICS,
          net_profit_abs: 12740.18,
          total_fees: 482.16,
        } as unknown as BacktestMetricsOut}
      />,
    );
    expect(screen.getByText(/연환산/)).toBeInTheDocument();
    expect(screen.getByText("+43.28%")).toBeInTheDocument();
    expect(screen.getByText(/수수료/)).toBeInTheDocument();
    expect(screen.getByText("-482.16")).toBeInTheDocument();
  });
});
