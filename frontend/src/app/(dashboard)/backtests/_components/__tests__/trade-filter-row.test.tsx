// Sprint 43 W11 — TradeFilterRow 6 필터 + countActiveFilters 검증.

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  DEFAULT_FILTERS,
  type ExtendedTradeFilters,
  TradeFilterRow,
  countActiveFilters,
} from "../trade-filter-row";

describe("countActiveFilters", () => {
  it("기본값 → 0", () => {
    expect(countActiveFilters(DEFAULT_FILTERS)).toBe(0);
  });

  it("direction + result 동시 → 2", () => {
    const f: ExtendedTradeFilters = {
      ...DEFAULT_FILTERS,
      direction: "long",
      result: "win",
    };
    expect(countActiveFilters(f)).toBe(2);
  });

  it("검색 + 기간 + PnL 범위 → 5 (search/start/end/min/max)", () => {
    const f: ExtendedTradeFilters = {
      ...DEFAULT_FILTERS,
      search: "long",
      periodStart: "2026-01-01",
      periodEnd: "2026-01-31",
      pnlMinPct: -0.05,
      pnlMaxPct: 0.1,
    };
    expect(countActiveFilters(f)).toBe(5);
  });
});

describe("TradeFilterRow", () => {
  it("renders 6 filter inputs + role=group + 활성 0이면 pill 숨김", () => {
    render(
      <TradeFilterRow
        filters={DEFAULT_FILTERS}
        onFiltersChange={vi.fn()}
        sortField="entry_time"
        sortDir="desc"
        onSortChange={vi.fn()}
        activeCount={0}
        onReset={vi.fn()}
      />,
    );
    const group = screen.getByLabelText("거래 필터");
    expect(group).toBeInTheDocument();
    expect(group).toHaveAttribute("role", "group");
    // 검색 input
    expect(screen.getByLabelText("거래 검색")).toBeInTheDocument();
    // 기간 2개
    expect(screen.getByLabelText("기간 시작")).toBeInTheDocument();
    expect(screen.getByLabelText("기간 종료")).toBeInTheDocument();
    // PnL 2개
    expect(
      screen.getByLabelText(/최소 손익 비율/),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("최대 손익 비율")).toBeInTheDocument();
    // 정렬
    expect(screen.getByLabelText("정렬")).toBeInTheDocument();
    // 활성 0 → 초기화 버튼/pill 미표시
    expect(screen.queryByText("초기화")).not.toBeInTheDocument();
  });

  it("활성 필터 ≥1 → pill + 초기화 버튼 표시", () => {
    render(
      <TradeFilterRow
        filters={{ ...DEFAULT_FILTERS, direction: "long" }}
        onFiltersChange={vi.fn()}
        sortField="entry_time"
        sortDir="desc"
        onSortChange={vi.fn()}
        activeCount={1}
        onReset={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("활성 필터 1개")).toBeInTheDocument();
    expect(screen.getByText("초기화")).toBeInTheDocument();
  });
});
