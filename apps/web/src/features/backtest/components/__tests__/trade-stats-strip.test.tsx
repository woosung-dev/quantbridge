// Sprint 43 W11 — TradeStatsStrip 집계/표시 검증.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { TradeItem } from "@/features/backtest/schemas";

import { TradeStatsStrip } from "@/features/backtest/components/trades/trade-stats-strip";

function mkTrade(overrides: Partial<TradeItem> & Pick<TradeItem, "direction" | "pnl">): TradeItem {
  return {
    trade_index: 1,
    status: "closed",
    entry_time: "2026-01-01T00:00:00Z",
    exit_time: "2026-01-01T01:00:00Z",
    entry_price: 100,
    exit_price: 110,
    size: 1,
    return_pct: 0.05,
    fees: 0,
    ...overrides,
  };
}

describe("TradeStatsStrip", () => {
  it("빈 거래 — 4 카드 모두 fallback 표시", () => {
    render(<TradeStatsStrip trades={[]} />);
    expect(screen.getByLabelText("거래 요약 통계")).toBeInTheDocument();
    // 총 거래 0
    expect(screen.getByTestId("trade-stat-총 거래")).toHaveTextContent("0");
    // 평균 수익 / 평균 손실 — 데이터 없음 fallback
    expect(screen.getAllByText("—")).toHaveLength(3); // 수익/손실/보유
  });

  it("승/패 집계 + 평균 수익률 정상", () => {
    const trades: TradeItem[] = [
      mkTrade({
        trade_index: 1,
        direction: "long",
        pnl: 100,
        return_pct: 0.04,
      }),
      mkTrade({
        trade_index: 2,
        direction: "long",
        pnl: 200,
        return_pct: 0.08,
      }),
      mkTrade({
        trade_index: 3,
        direction: "short",
        pnl: -50,
        return_pct: -0.02,
      }),
    ];
    render(<TradeStatsStrip trades={trades} />);
    expect(screen.getByTestId("trade-stat-총 거래")).toHaveTextContent("3");
    // 승률 텍스트: "2승 1패"
    expect(screen.getByText("2승 1패")).toBeInTheDocument();
    // 평균 수익률 6% (= avg of 4% / 8%)
    expect(screen.getByTestId("trade-stat-평균 수익")).toHaveTextContent(/\+?6\.00%/);
    // 평균 손실 -2%
    expect(screen.getByTestId("trade-stat-평균 손실")).toHaveTextContent(/-2\.00%/);
  });

  // ★BL-822 — 거래 목록 탭도 같은 병을 앓고 있었다. 실측(backtest 20128227)에서
  // 「총 거래 13 · 2승 10패」라 더해서 안 맞았다. 미청산은 승도 패도 아니므로 따로 센다.
  it("미청산 거래는 승/패 어느 쪽도 아니고 총계가 닫히도록 따로 적는다", () => {
    const trades: TradeItem[] = [
      mkTrade({ trade_index: 1, direction: "long", pnl: 100, return_pct: 0.04 }),
      mkTrade({ trade_index: 2, direction: "short", pnl: -50, return_pct: -0.02 }),
      // 미청산 — exit_time null, pnl 은 진입 수수료만큼 음수(non-nullable 계약).
      mkTrade({
        trade_index: 3,
        direction: "long",
        status: "open",
        exit_time: null,
        exit_price: null,
        pnl: -0.6,
        return_pct: -0.006,
        fees: 0.6,
      }),
    ];
    render(<TradeStatsStrip trades={trades} />);

    expect(screen.getByTestId("trade-stat-총 거래")).toHaveTextContent("3");
    // 1 + 1 + 1 = 3 — 종전에는 "1승 2패"(미청산이 패로 세어짐)라 총계가 닫히지 않았다.
    expect(screen.getByText("1승 1패 · 미청산 1건")).toBeInTheDocument();
    // 미청산의 음수 pnl 이 평균 손실을 오염시키지 않는다.
    expect(screen.getByTestId("trade-stat-평균 손실")).toHaveTextContent(/-2\.00%/);
  });

  it("음성 대조 — 미청산이 없으면 부기가 붙지 않는다", () => {
    const trades: TradeItem[] = [
      mkTrade({ trade_index: 1, direction: "long", pnl: 100, return_pct: 0.04 }),
      mkTrade({ trade_index: 2, direction: "short", pnl: -50, return_pct: -0.02 }),
    ];
    render(<TradeStatsStrip trades={trades} />);
    expect(screen.getByText("1승 1패")).toBeInTheDocument();
    expect(screen.queryByText(/미청산/)).toBeNull();
  });

  // C 이식 S6 — 공용 .kpi 카드 4개(role=listitem)로 렌더한다.
  it("4개 KPI 카드가 공용 .card.kpi 로 렌더된다", () => {
    render(<TradeStatsStrip trades={[]} />);
    const cards = screen.getAllByRole("listitem");
    expect(cards).toHaveLength(4);
    const valueCard = screen.getByTestId("trade-stat-총 거래").parentElement;
    expect(valueCard?.className).toContain("kpi");
  });

  it("평균 보유 시간 — 1h 단위 표시", () => {
    const trades: TradeItem[] = [
      mkTrade({
        trade_index: 1,
        direction: "long",
        pnl: 10,
        entry_time: "2026-01-01T00:00:00Z",
        exit_time: "2026-01-01T02:00:00Z", // 2h
      }),
      mkTrade({
        trade_index: 2,
        direction: "long",
        pnl: 10,
        entry_time: "2026-01-02T00:00:00Z",
        exit_time: "2026-01-02T04:00:00Z", // 4h
      }),
    ];
    render(<TradeStatsStrip trades={trades} />);
    // 평균 3h
    expect(screen.getByTestId("trade-stat-평균 보유 시간")).toHaveTextContent(/3h/);
  });
});
