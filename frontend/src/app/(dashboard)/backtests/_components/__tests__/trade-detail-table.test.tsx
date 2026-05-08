// Sprint 43 W11 — TradeDetailTable 행 expand + pagination + CSV 버튼 검증.

import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { TradeItem } from "@/features/backtest/schemas";

import { TradeDetailTable } from "../trade-detail-table";

function mkTrade(idx: number, pnl = 10): TradeItem {
  return {
    trade_index: idx,
    direction: "long",
    status: "closed",
    entry_time: `2026-01-${String(idx).padStart(2, "0")}T00:00:00Z`,
    exit_time: `2026-01-${String(idx).padStart(2, "0")}T01:00:00Z`,
    entry_price: 100,
    exit_price: 110,
    size: 1,
    pnl,
    return_pct: 0.05,
    fees: 0.1,
  };
}

afterEach(() => {
  // jsdom URL.createObjectURL polyfill cleanup if test triggered CSV.
  vi.restoreAllMocks();
});

describe("TradeDetailTable", () => {
  it("loading state → '거래 불러오는 중…'", () => {
    render(
      <TradeDetailTable
        trades={[]}
        isLoading
        isError={false}
        filenamePrefix="bt-test"
      />,
    );
    expect(screen.getByText(/거래 불러오는 중/)).toBeInTheDocument();
  });

  it("error state → 메시지 표시", () => {
    render(
      <TradeDetailTable
        trades={[]}
        isLoading={false}
        isError
        errorMessage="500 server"
        filenamePrefix="bt-test"
      />,
    );
    expect(screen.getByText(/500 server/)).toBeInTheDocument();
  });

  it("행 expand 토글 — aria-expanded 변경 + detail 영역 노출", () => {
    render(
      <TradeDetailTable
        trades={[mkTrade(1, 100)]}
        isLoading={false}
        isError={false}
        filenamePrefix="bt-test"
      />,
    );
    const expandBtn = screen.getByLabelText("거래 #1 상세 보기");
    expect(expandBtn).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByTestId("trade-detail-expanded")).not.toBeInTheDocument();

    fireEvent.click(expandBtn);

    const closeBtn = screen.getByLabelText("거래 #1 상세 닫기");
    expect(closeBtn).toHaveAttribute("aria-expanded", "true");
    const expanded = screen.getByTestId("trade-detail-expanded");
    expect(expanded).toBeInTheDocument();
    expect(within(expanded).getByText("진입 정보")).toBeInTheDocument();
    expect(within(expanded).getByText("청산 정보")).toBeInTheDocument();
    expect(within(expanded).getByText("성과")).toBeInTheDocument();
  });

  it("pageSize 50 — 60건 입력 시 페이지 컨트롤 표시", () => {
    const trades: TradeItem[] = Array.from({ length: 60 }, (_, i) =>
      mkTrade(i + 1),
    );
    render(
      <TradeDetailTable
        trades={trades}
        isLoading={false}
        isError={false}
        filenamePrefix="bt-test"
      />,
    );
    // 페이지 컨트롤 노출
    expect(screen.getByLabelText("이전 페이지")).toBeInTheDocument();
    expect(screen.getByLabelText("다음 페이지")).toBeInTheDocument();
    // 다음 페이지로 이동
    fireEvent.click(screen.getByLabelText("다음 페이지"));
    // page 2 / 2 표시 (info bar + pagination 모두 매칭 — 최소 1개)
    expect(screen.getAllByText(/2 \/ 2/).length).toBeGreaterThanOrEqual(1);
    // 다음 페이지 버튼 disabled (마지막 페이지)
    expect(screen.getByLabelText("다음 페이지")).toBeDisabled();
  });

  it("CSV 버튼 — 0건이면 disabled", () => {
    render(
      <TradeDetailTable
        trades={[]}
        isLoading={false}
        isError={false}
        filenamePrefix="bt-test"
      />,
    );
    const btn = screen.getByLabelText("CSV 내보내기");
    expect(btn).toBeDisabled();
  });
});
