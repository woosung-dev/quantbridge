// LandingBento — 4 cell heading + 5 strategy bar + Pine Script + 4 live strategy
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingBento } from "../landing-bento";

describe("LandingBento", () => {
  afterEach(() => {
    cleanup();
  });

  it("section heading + 4 cell 헤더", () => {
    render(<LandingBento />);
    expect(
      screen.getByRole("heading", { level: 2, name: "한눈에 보는 플랫폼" }),
    ).toBeInTheDocument();
    for (const h of [
      "백테스트 성과 비교",
      "리스크 지표",
      "Pine Script",
      "실시간 모니터링",
    ]) {
      expect(
        screen.getByRole("heading", { level: 3, name: h }),
      ).toBeInTheDocument();
    }
  });

  it("5 strategy bar (전략A~E) + 수익률 노출", () => {
    render(<LandingBento />);
    for (const label of ["전략A", "전략B", "전략C", "전략D", "전략E"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByText("+24.5%")).toBeInTheDocument();
    expect(screen.getByText("-3.4%")).toBeInTheDocument();
  });

  it("4 라이브 전략 + 리스크 지표 3종", () => {
    render(<LandingBento />);
    for (const name of [
      "BTC MA Cross",
      "ETH Momentum",
      "SOL RSI Reversal",
      "AVAX Breakout",
    ]) {
      expect(screen.getByText(name)).toBeInTheDocument();
    }
    expect(screen.getByText("Max Drawdown")).toBeInTheDocument();
    expect(screen.getByText("VaR (95%)")).toBeInTheDocument();
    expect(screen.getByText("Sharpe Ratio")).toBeInTheDocument();
  });
});
