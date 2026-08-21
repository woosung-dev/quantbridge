import { describe, expect, it } from "vitest";

import type { TradeItem } from "../schemas";
import { applyTradeFilterSort, tradesToCsv } from "../utils";

const T = (overrides: Partial<TradeItem> = {}): TradeItem => ({
  trade_index: 1,
  direction: "long",
  status: "closed",
  entry_time: "2026-01-01T00:00:00Z",
  exit_time: "2026-01-02T00:00:00Z",
  entry_price: 100,
  exit_price: 110,
  size: 1,
  pnl: 10,
  return_pct: 0.1,
  fees: 0.1,
  ...overrides,
});

describe("tradesToCsv (Sprint 30-δ)", () => {
  it("빈 입력 시 BOM + 헤더 1줄", () => {
    const csv = tradesToCsv([]);
    expect(csv.charCodeAt(0)).toBe(0xfeff); // UTF-8 BOM
    const lines = csv.slice(1).split("\n");
    expect(lines).toHaveLength(1);
    expect(lines[0]).toBe(
      "trade_index,direction,status,entry_time,exit_time,entry_price,exit_price,size,pnl,return_pct,fees,cumulative_pnl," +
        "runup_abs,drawdown_abs,bars_in_trade,fee_paid,slippage_paid,exit_kind,comment",
    );
  });

  it("19 컬럼 (TV 확장) + 누적 PnL 정확", () => {
    const csv = tradesToCsv([T({ pnl: 10 }), T({ trade_index: 2, pnl: -3 })]);
    const lines = csv.slice(1).split("\n");
    expect(lines).toHaveLength(3); // header + 2 rows
    const cols1 = lines[1]?.split(",") ?? [];
    expect(cols1).toHaveLength(19); // 기존 12 + TV 확장 7 (null = 빈 값)
    expect(cols1[11]).toBe("10.00000000");
    const cols2 = lines[2]?.split(",") ?? [];
    expect(cols2[11]).toBe("7.00000000"); // cumulative: 10 + (-3)
  });

  it("BOM 으로 시작 + LF 줄바꿈 (CRLF 아님)", () => {
    const csv = tradesToCsv([T()]);
    expect(csv.startsWith("﻿")).toBe(true);
    expect(csv.includes("\r\n")).toBe(false);
    expect(csv.includes("\n")).toBe(true);
  });

  it("non-finite pnl 은 0 처리 (cumulative 안전)", () => {
    const csv = tradesToCsv([T({ pnl: Number.NaN })]);
    const cols = csv.slice(1).split("\n")[1]?.split(",") ?? [];
    expect(cols[8]).toBe("0"); // pnl
    expect(cols[11]).toBe("0.00000000"); // cumulative
  });
});

describe("applyTradeFilterSort (Sprint 30-δ)", () => {
  const trades: TradeItem[] = [
    T({
      trade_index: 1,
      direction: "long",
      pnl: 10,
      return_pct: 0.1,
      entry_time: "2026-01-03T00:00:00Z",
    }),
    T({
      trade_index: 2,
      direction: "short",
      pnl: -5,
      return_pct: -0.05,
      entry_time: "2026-01-01T00:00:00Z",
    }),
    T({
      trade_index: 3,
      direction: "long",
      pnl: 20,
      return_pct: 0.2,
      entry_time: "2026-01-02T00:00:00Z",
    }),
  ];

  it("entry_time asc 기본 정렬", () => {
    const sorted = applyTradeFilterSort(
      trades,
      { direction: "all", result: "all" },
      "entry_time",
      "asc",
    );
    expect(sorted.map((t) => t.trade_index)).toEqual([2, 3, 1]);
  });

  it("pnl desc 정렬", () => {
    const sorted = applyTradeFilterSort(trades, { direction: "all", result: "all" }, "pnl", "desc");
    expect(sorted.map((t) => t.trade_index)).toEqual([3, 1, 2]);
  });

  it("direction=long 필터", () => {
    const sorted = applyTradeFilterSort(
      trades,
      { direction: "long", result: "all" },
      "entry_time",
      "asc",
    );
    expect(sorted.map((t) => t.trade_index)).toEqual([3, 1]);
  });

  it("result=win 필터 (pnl>0 만, 0 제외)", () => {
    const sorted = applyTradeFilterSort(
      [...trades, T({ trade_index: 4, pnl: 0, entry_time: "2026-01-04T00:00:00Z" })],
      { direction: "all", result: "win" },
      "pnl",
      "desc",
    );
    expect(sorted.map((t) => t.trade_index)).toEqual([3, 1]);
  });

  it("direction + result 조합 필터 (long + win)", () => {
    const sorted = applyTradeFilterSort(
      trades,
      { direction: "long", result: "win" },
      "pnl",
      "desc",
    );
    expect(sorted.map((t) => t.trade_index)).toEqual([3, 1]);
  });

  it("return_pct asc 정렬", () => {
    const sorted = applyTradeFilterSort(
      trades,
      { direction: "all", result: "all" },
      "return_pct",
      "asc",
    );
    expect(sorted.map((t) => t.trade_index)).toEqual([2, 1, 3]);
  });

  // BL-665 — decorate–sort–undecorate 로 바꾸면서 안정성이 계약임을 명시적으로 고정한다.
  // ★착수 전 6케이스에는 **동점이 하나도 없어서** 안정 정렬을 실제로 재고 있지 않았다.
  it("★동점 키는 입력 순서를 보존한다 (안정 정렬)", () => {
    const tied: TradeItem[] = [
      T({ trade_index: 7, pnl: 1, entry_time: "2026-02-01T00:00:00Z" }),
      T({ trade_index: 8, pnl: 1, entry_time: "2026-02-01T00:00:00Z" }),
      T({ trade_index: 9, pnl: 1, entry_time: "2026-02-01T00:00:00Z" }),
    ];
    for (const dir of ["asc", "desc"] as const) {
      const sorted = applyTradeFilterSort(
        tied,
        { direction: "all", result: "all" },
        "entry_time",
        dir,
      );
      expect(sorted.map((t) => t.trade_index)).toEqual([7, 8, 9]);
    }
  });
});
