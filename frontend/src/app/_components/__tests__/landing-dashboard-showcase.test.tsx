// LandingDashboardShowcase — 핵심 element smoke (KPI 4 / 포지션 4 / 봇 4 / 체결 5)
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingDashboardShowcase } from "../landing-dashboard-showcase";

describe("LandingDashboardShowcase", () => {
  afterEach(() => {
    cleanup();
  });

  it("section heading + DEMO/LIVE 토글", () => {
    render(<LandingDashboardShowcase />);
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "실시간 트레이딩 대시보드 (예시 화면)",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("DEMO")).toBeInTheDocument();
    expect(screen.getByText("LIVE")).toBeInTheDocument();
  });

  it("KPI 4 — 총 자산 / 일일 수익 / 활성 봇 / 오픈 포지션 (정직 표시)", () => {
    render(<LandingDashboardShowcase />);
    for (const label of ["총 자산", "일일 수익", "활성 봇", "오픈 포지션"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    // BL-270 정직 표시: specific 금액 → '—' placeholder + '예시 데이터' 라벨
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.getByText("7 / 12")).toBeInTheDocument();
  });

  it("포지션 4 + 봇 4 + 체결 5 노출", () => {
    render(<LandingDashboardShowcase />);
    for (const pair of ["BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT"]) {
      expect(screen.getAllByText(pair).length).toBeGreaterThan(0);
    }
    for (const bot of [
      "MA Crossover v2",
      "RSI Divergence",
      "Bollinger Band",
      "Grid Trading",
    ]) {
      expect(screen.getByText(bot)).toBeInTheDocument();
    }
    const buys = screen.getAllByText("BUY");
    const sells = screen.getAllByText("SELL");
    expect(buys.length + sells.length).toBe(5);
  });
});
