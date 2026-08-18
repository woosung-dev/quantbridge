// TradeAnalyticsSection — KPI 4 + 거래 분포 donut 카운트 + 빈 상태 검증
// + 방향별 성과 표 (구 trades/trade-analysis.tsx 흡수분 — 정보 보존 검증, 2026-08-18 이관)
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  BacktestMetricsOut,
  TradeItem,
} from "@/features/backtest/schemas";

import { TradeAnalyticsSection } from "@/features/backtest/components/report/trade-analytics-section";

const METRICS = {
  total_return: 0.1,
  sharpe_ratio: 1,
  max_drawdown: -0.05,
  win_rate: 0.5,
  num_trades: 4,
  avg_trade_abs: 12.5,
  avg_trade_pct: 0.005,
  avg_bars_in_trade: 1.5,
  largest_win_abs: 100,
  largest_loss_abs: -40,
  best_trade_pct: 0.04,
  worst_trade_pct: -0.02,
  avg_win: 0.03,
  avg_loss: -0.015,
} as unknown as BacktestMetricsOut;

function trade(
  idx: number,
  pnl: number,
  direction: "long" | "short" = "long",
): TradeItem {
  return {
    trade_index: idx,
    direction,
    status: "closed",
    entry_time: "2026-01-01T00:00:00Z",
    exit_time: "2026-01-02T00:00:00Z",
    entry_price: 100,
    exit_price: 101,
    size: 1,
    pnl,
    return_pct: pnl / 100,
    fees: 0,
  } as unknown as TradeItem;
}

describe("TradeAnalyticsSection", () => {
  it("KPI 4종 + 거래 분포 donut 카운트 렌더", () => {
    render(
      <TradeAnalyticsSection
        metrics={METRICS}
        trades={[trade(0, 10), trade(1, -5), trade(2, 0), trade(3, 8)]}
      />,
    );
    // "평균 PnL" 은 KPI 라벨 + 방향별 성과 표 헤더 두 곳 (병합 후 구조)
    expect(screen.getAllByText("평균 PnL")).toHaveLength(2);
    expect(screen.getByText("+12.50 USDT")).toBeInTheDocument();
    expect(screen.getByText("평균 거래 바수")).toBeInTheDocument();
    expect(screen.getByText("1.5")).toBeInTheDocument();
    expect(screen.getByText("최대 수익 거래")).toBeInTheDocument();
    expect(screen.getByText("+100.00 USDT")).toBeInTheDocument();
    expect(screen.getByText("최대 손실 거래")).toBeInTheDocument();
    expect(screen.getByText("-40.00 USDT")).toBeInTheDocument();
    // donut 범례: 승 2 / 패 1 / 손익분기 1, 중앙 총 거래 4
    expect(screen.getByText("2 거래")).toBeInTheDocument();
    expect(screen.getAllByText("1 거래")).toHaveLength(2);
    expect(screen.getByText("총 거래")).toBeInTheDocument();
  });

  it("거래 0건 → 분포/도넛 빈 상태", () => {
    render(<TradeAnalyticsSection metrics={{ ...METRICS, num_trades: 0 }} trades={[]} />);
    expect(screen.getByTestId("pnl-distribution-empty")).toBeInTheDocument();
    expect(screen.getByTestId("trade-outcome-donut-empty")).toBeInTheDocument();
  });

  // ── 방향별 성과 (구 TradeAnalysis 이관 단언 — 롱/숏 고유 정보 보존 검증) ──

  it("trades 제공 시 방향별 성과 표에 거래 수/승률/평균 PnL 렌더", () => {
    render(
      <TradeAnalyticsSection
        metrics={METRICS}
        trades={[
          trade(0, 10, "long"),
          trade(1, -5, "long"),
          trade(2, 0, "long"),
          trade(3, 20, "short"),
        ]}
      />,
    );
    expect(screen.getByText("방향별 성과")).toBeInTheDocument();
    const table = within(screen.getByTestId("direction-breakdown-table"));
    expect(table.getByText("롱")).toBeInTheDocument();
    expect(table.getByText("숏")).toBeInTheDocument();
    // 롱: 3건, 승 1/3 = 33.3%, 평균 PnL (10-5+0)/3 = +1.67
    expect(table.getByText("3")).toBeInTheDocument();
    expect(table.getByText("33.3%")).toBeInTheDocument();
    expect(table.getByText("+1.67")).toBeInTheDocument();
    // 숏: 1건, 승률 100.0%, 평균 PnL +20.00
    expect(table.getByText("1")).toBeInTheDocument();
    expect(table.getByText("100.0%")).toBeInTheDocument();
    expect(table.getByText("+20.00")).toBeInTheDocument();
  });

  it("단일 방향이면 반대편 행은 0건 + 대시 렌더", () => {
    render(<TradeAnalyticsSection metrics={METRICS} trades={[trade(0, 50, "long")]} />);
    const table = within(screen.getByTestId("direction-breakdown-table"));
    expect(table.getByText("1")).toBeInTheDocument(); // 롱 1건
    expect(table.getByText("100.0%")).toBeInTheDocument();
    expect(table.getByText("+50.00")).toBeInTheDocument();
    expect(table.getByText("0")).toBeInTheDocument(); // 숏 0건 (breakdown 폴백)
    expect(table.getAllByText("—")).toHaveLength(2); // 숏 승률/평균 PnL
  });

  it("trades 가 비어도 metrics 방향 카운트(long_count/short_count)를 보존한다", () => {
    // 구 TradeAnalysis 「방향 분포」 배지의 정보 보존 축 — 거래 목록이 없어도 모집단 카운트 유지.
    render(
      <TradeAnalyticsSection
        metrics={{ ...METRICS, long_count: 5, short_count: 2 } as BacktestMetricsOut}
        trades={[]}
      />,
    );
    const table = within(screen.getByTestId("direction-breakdown-table"));
    expect(table.getByText("5")).toBeInTheDocument();
    expect(table.getByText("2")).toBeInTheDocument();
    expect(table.getAllByText("—")).toHaveLength(4); // 롱/숏 각 승률·평균 PnL 은 trades 없이는 미산출
  });

  // 구 trade-analysis.test.tsx 의 disclosure 경계 회귀 단언 이관
  // (W4 codex+Sonnet evaluator finding — `<` 가 실수로 `<=` 로 바뀌는 회귀 방지)
  it("trades.length === num_trades 이면 부분집합 안내를 표시하지 않는다", () => {
    render(
      <TradeAnalyticsSection
        metrics={METRICS}
        trades={[trade(0, 10), trade(1, -5), trade(2, 0), trade(3, 8)]}
      />,
    ); // 4 === METRICS.num_trades(4)
    expect(screen.queryByText(/표시된 거래/)).not.toBeInTheDocument();
  });

  it("trades.length < num_trades 이면 부분집합 안내를 표시한다", () => {
    render(
      <TradeAnalyticsSection
        metrics={{ ...METRICS, num_trades: 10 } as BacktestMetricsOut}
        trades={[trade(0, 10)]}
      />,
    );
    expect(screen.getByText(/표시된 거래 1건 기준/)).toBeInTheDocument();
    expect(screen.getByText(/전체 10건 중/)).toBeInTheDocument();
  });

  it("표본이 부분집합이면 승률·평균 PnL 헤더에 * 가 붙어 분모 분리를 고지한다 (codex P2)", () => {
    // 거래 수 열은 metrics 모집단, 승률·평균 PnL 은 로드된 표본 파생 — truncated 시 한 행에
    // 두 분모가 공존하므로 통계 열만 * 로 각주와 결속한다.
    render(
      <TradeAnalyticsSection
        metrics={{ ...METRICS, num_trades: 6 } as BacktestMetricsOut}
        trades={[trade(0, 10), trade(1, -5, "short")]}
      />,
    );
    expect(screen.getByText("승률*")).toBeInTheDocument();
    expect(screen.getByText("평균 PnL*")).toBeInTheDocument();
    expect(screen.getByText(/거래 수 열은 전체 기준/)).toBeInTheDocument();
  });

  it("표본 = 전체면 * 마커가 붙지 않는다", () => {
    render(
      <TradeAnalyticsSection
        metrics={METRICS}
        trades={[trade(0, 10), trade(1, -5), trade(2, 0), trade(3, 8)]}
      />,
    );
    expect(screen.queryByText("승률*")).toBeNull();
    expect(screen.queryByText("평균 PnL*")).toBeNull();
  });
});
