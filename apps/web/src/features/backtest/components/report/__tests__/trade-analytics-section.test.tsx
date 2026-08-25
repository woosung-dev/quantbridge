// TradeAnalyticsSection — KPI 4 + 거래 분포 donut 카운트 + 빈 상태 검증
// + 방향별 성과 표 (구 trades/trade-analysis.tsx 흡수분 — 정보 보존 검증, 2026-08-18 이관)
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { BacktestMetricsOut, TradeItem } from "@/features/backtest/schemas";

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

function trade(idx: number, pnl: number, direction: "long" | "short" = "long"): TradeItem {
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
    expect(screen.queryByText(/표시된 완료 거래/)).not.toBeInTheDocument();
  });

  it("trades.length < num_trades 이면 부분집합 안내를 표시한다", () => {
    render(
      <TradeAnalyticsSection
        metrics={{ ...METRICS, num_trades: 10 } as BacktestMetricsOut}
        trades={[trade(0, 10)]}
      />,
    );
    expect(screen.getByText(/표시된 완료 거래 1건 기준/)).toBeInTheDocument();
    expect(screen.getByText(/완료 10건 중/)).toBeInTheDocument();
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
    expect(screen.getByText(/거래 수 열은 미청산을 포함한 전체 기준/)).toBeInTheDocument();
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

  // BL-822 — 방향별 승률의 분모는 **완료 거래**다.
  // 미청산 거래는 pnl 이 없어 computeDirectionBreakdown 이 0 으로 강제하는데, 그러면
  // 「이기지 못한 거래」로 분모에 들어가 승률이 조용히 낮아진다 (2026-08-25 qa-sweep 추가 발견).
  describe("미청산 거래와 승률 분모 (BL-822)", () => {
    function openTrade(idx: number, direction: "long" | "short" = "long"): TradeItem {
      return {
        trade_index: idx,
        direction,
        status: "open",
        entry_time: "2026-01-03T00:00:00Z",
        exit_time: null,
        entry_price: 100,
        exit_price: null,
        size: 1,
        pnl: null,
        return_pct: null,
        fees: 0,
      } as unknown as TradeItem;
    }

    // 롱 3건 중 완료 2건(승 1 · 패 1) + 미청산 1건. long_count 는 BE override 라 3 이다.
    const SPLIT = {
      ...METRICS,
      num_trades: 3,
      completed_trades: 2,
      long_count: 3,
      short_count: 0,
    } as unknown as BacktestMetricsOut;
    const TRADES = [trade(0, 10), trade(1, -5), openTrade(2)];

    it("미청산 1건이 승률 분모에 들어가지 않는다", () => {
      render(<TradeAnalyticsSection metrics={SPLIT} trades={TRADES} />);
      const table = within(screen.getByTestId("direction-breakdown-table"));
      expect(table.getByText("50.0%")).toBeInTheDocument(); // 완료 2건 중 1승
      expect(table.queryByText("33.3%")).toBeNull(); // 미청산까지 센 옛 분모
    });

    it("거래 수 열은 미청산을 포함한 모집단(long_count)을 그대로 유지한다", () => {
      render(<TradeAnalyticsSection metrics={SPLIT} trades={TRADES} />);
      const table = within(screen.getByTestId("direction-breakdown-table"));
      expect(table.getByText("3")).toBeInTheDocument();
    });

    it("표본 축소 문구 대신 **분모가 갈린 사유**를 말한다", () => {
      // 완료 2건을 전부 실었으므로 「일부만 보여 준다」는 거짓이다. 그러나 거래 수 열(3)과
      // 승률 분모(2)는 여전히 다르므로 침묵해서도 안 된다 — 2026-08-25 화면 실측에서
      // 「롱 13건 · 승률 16.7%(=2/12)」가 아무 고지 없이 한 행에 있었다.
      render(<TradeAnalyticsSection metrics={SPLIT} trades={TRADES} />);
      expect(screen.queryByText(/표시된 완료 거래/)).not.toBeInTheDocument();
      expect(screen.getByText("승률*")).toBeInTheDocument();
      expect(screen.getByText(/승률·평균 PnL 은 완료 거래 2건 기준/)).toBeInTheDocument();
      expect(screen.getByText(/거래 수 열은 미청산 1건을 포함한 전체 기준/)).toBeInTheDocument();
    });

    it("음성 대조 — 미청산이 없고 표본도 전체면 * 도 각주도 없다", () => {
      render(
        <TradeAnalyticsSection
          metrics={{ ...SPLIT, num_trades: 2 } as unknown as BacktestMetricsOut}
          trades={[trade(0, 10), trade(1, -5)]}
        />,
      );
      expect(screen.queryByText("승률*")).toBeNull();
      expect(screen.queryByText(/거래 수 열은/)).not.toBeInTheDocument();
    });
  });
});
