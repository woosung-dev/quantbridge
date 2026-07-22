// TradeLedgerTable — variant-c 단일행 10열 table.trades / 청산 사유 라벨 / 빈 상태 / CSV 확장
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { TradeItem } from "@/features/backtest/schemas";
import { tradesToCsv } from "@/features/backtest/utils";

import { TradeLedgerTable } from "@/app/(dashboard)/backtests/_components/report/trade-ledger-table";

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

describe("TradeLedgerTable (05 거래 내역)", () => {
  it("공용 table.trades + 10열 헤더 시맨틱 구조", () => {
    const { container } = render(<TradeLedgerTable trades={[trade({})]} />);
    expect(container.querySelector("table.trades")).not.toBeNull();
    expect(container.querySelectorAll("thead th")).toHaveLength(10);
    for (const h of ["번호", "진입 시각", "청산 시각", "손익", "청산 사유"]) {
      expect(screen.getByText(h)).toBeInTheDocument();
    }
  });

  it("closed 거래 = 단일행 + 방향 칩(.side.long) + 손익 abs + 수익률 + 청산 사유", () => {
    const { container } = render(
      <TradeLedgerTable trades={[trade({ exit_kind: "trailing_stop" })]} />,
    );
    expect(container.querySelectorAll("tbody tr")).toHaveLength(1);
    const sideChip = container.querySelector(".side.long");
    expect(sideChip).not.toBeNull();
    expect(sideChip).toHaveTextContent("롱");
    expect(screen.getByText("+14,195.45")).toBeInTheDocument();
    expect(screen.getByText("+0.50%")).toBeInTheDocument();
    expect(screen.getByText("추적 손절")).toBeInTheDocument();
  });

  it("exit_kind 없는 청산 = 시그널 청산, open 거래 = 청산가·청산시각 무데이터 셀", () => {
    render(
      <TradeLedgerTable
        trades={[
          trade({ trade_index: 1, exit_kind: null }),
          trade({ trade_index: 2, status: "open", exit_time: null, exit_price: null }),
        ]}
      />,
    );
    expect(screen.getByText("시그널 청산")).toBeInTheDocument();
    expect(screen.getByText("보유 중")).toBeInTheDocument();
  });

  it("거래 0건 → 빈 상태 렌더", () => {
    render(<TradeLedgerTable trades={[]} />);
    expect(screen.getByTestId("trade-ledger-empty")).toBeInTheDocument();
    expect(screen.getByText("기록된 거래가 없습니다.")).toBeInTheDocument();
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
