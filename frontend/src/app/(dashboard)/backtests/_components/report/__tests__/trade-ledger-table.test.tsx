// TradeLedgerTable — 2행 원장 구조 / exit_kind 라벨 / null 컬럼 hide / CSV 확장
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { TradeItem } from "@/features/backtest/schemas";
import { tradesToCsv } from "@/features/backtest/utils";

import { TradeLedgerTable } from "../trade-ledger-table";

function trade(overrides: Partial<TradeItem>): TradeItem {
  return {
    trade_index: 0,
    direction: "long",
    status: "closed",
    entry_time: "2026-07-01T06:00:00Z",
    exit_time: "2026-07-01T21:00:00Z",
    entry_price: 58622.02,
    exit_price: 58329.91,
    size: 48.6,
    pnl: 14195.447,
    return_pct: 0.005,
    fees: 100,
    ...overrides,
  } as TradeItem;
}

describe("TradeLedgerTable", () => {
  it("closed 거래 = 청산/진입 2행 + 방향 badge + 순손익 abs+%", () => {
    render(
      <TradeLedgerTable
        trades={[
          trade({
            exit_kind: "trailing_stop",
            runup_abs: 500,
            runup_pct: 0.01,
            drawdown_abs: 200,
            drawdown_pct: 0.004,
            cumulative_pnl: 14195.447,
          }),
        ]}
      />,
    );
    // 2행 구조: 청산(트레일링 라벨) 먼저, 진입 아래.
    expect(screen.getByText("청산 · 트레일링")).toBeInTheDocument();
    expect(screen.getByText("진입")).toBeInTheDocument();
    expect(screen.getByText("롱")).toBeInTheDocument();
    expect(screen.getByText("+14,195.45 USDT")).toBeInTheDocument();
    expect(screen.getByText("+0.50%")).toBeInTheDocument();
    // 신규 컬럼 (런업/드로다운/누적) 노출
    expect(screen.getByText(/런업/)).toBeInTheDocument();
    expect(screen.getByText(/드로다운/)).toBeInTheDocument();
    expect(screen.getByText("누적 PnL")).toBeInTheDocument();
  });

  it("신규 필드 전부 null (구 백테스트) → 런업/드로다운/누적 컬럼 hide", () => {
    render(<TradeLedgerTable trades={[trade({})]} />);
    expect(screen.queryByText(/런업/)).not.toBeInTheDocument();
    expect(screen.queryByText(/드로다운/)).not.toBeInTheDocument();
    expect(screen.queryByText("누적 PnL")).not.toBeInTheDocument();
  });

  it("open 거래 = 진입 1행 (보유 중)", () => {
    render(
      <TradeLedgerTable
        trades={[trade({ status: "open", exit_time: null, exit_price: null })]}
      />,
    );
    expect(screen.getByText("진입 (보유 중)")).toBeInTheDocument();
    expect(screen.queryByText("청산")).not.toBeInTheDocument();
  });
});

describe("tradesToCsv TV 확장", () => {
  it("신규 컬럼 헤더 + 값 포함, null 은 빈 값", () => {
    const csv = tradesToCsv([
      trade({
        runup_abs: 500,
        drawdown_abs: 200,
        bars_in_trade: 3,
        fee_paid: 60,
        slippage_paid: 40,
        exit_kind: "take_profit",
        comment: "Long",
        cumulative_pnl: 14195.447,
      }),
      trade({ trade_index: 1 }),
    ]);
    const [header, row1, row2] = csv.split("\n");
    expect(header).toContain("runup_abs");
    expect(header).toContain("exit_kind");
    expect(header).toContain("comment");
    expect(row1).toContain("take_profit");
    expect(row1).toContain("Long");
    expect(row1).toContain("14195.447"); // BE cumulative 우선
    expect(row2).toContain(",,"); // null 필드 빈 값
  });
});
