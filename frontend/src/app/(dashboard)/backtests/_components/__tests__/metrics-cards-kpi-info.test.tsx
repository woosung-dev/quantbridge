// Sprint 61 T-7 (BL-327) — KPI tooltip 회귀 test
// Casual 페르소나 발견: Sharpe / Drawdown / Profit Factor / 승률 4종 의미 0% 해독.
// ? 아이콘 + native title (mouse hover / mobile long-press) + sr-only (screen reader) 부착.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  BacktestConfig,
  BacktestMetricsOut,
} from "@/features/backtest/schemas";

import { MetricsCards } from "../metrics-cards";

const METRICS: BacktestMetricsOut = {
  total_return: 0.5234,
  sharpe_ratio: 2.47,
  max_drawdown: -0.1234,
  win_rate: 0.684,
  num_trades: 42,
  profit_factor: 1.85,
  mdd_exceeds_capital: false,
};

const CONFIG: BacktestConfig = { leverage: 1 };

describe("MetricsCards — KPI info tooltip (Sprint 61 T-7 / BL-327)", () => {
  it("5 KPI 각 라벨에 ? 아이콘 button 이 부착된다", () => {
    render(<MetricsCards metrics={METRICS} config={CONFIG} />);
    // 5 라벨 모두 data-testid="kpi-info-<key>" 패턴 (영문 key)
    for (const key of [
      "total-return",
      "sharpe-ratio",
      "max-drawdown",
      "profit-factor",
      "win-rate",
    ]) {
      const btn = screen.getByTestId(`kpi-info-${key}`);
      expect(btn).toBeInTheDocument();
      expect(btn.tagName).toBe("BUTTON");
      // type="button" 으로 form submit 방어
      expect(btn.getAttribute("type")).toBe("button");
    }
  });

  it("? 아이콘에 native title attribute 가 있어 hover/long-press 시 설명 노출", () => {
    render(<MetricsCards metrics={METRICS} config={CONFIG} />);
    const sharpeInfo = screen.getByTestId("kpi-info-sharpe-ratio");
    expect(sharpeInfo.getAttribute("title")).toMatch(/샤프|변동성|초과수익/);
  });

  it("? 아이콘에 aria-label 이 있어 screen reader 호환", () => {
    render(<MetricsCards metrics={METRICS} config={CONFIG} />);
    const profitFactorInfo = screen.getByTestId("kpi-info-profit-factor");
    expect(profitFactorInfo.getAttribute("aria-label")).toMatch(
      /Profit Factor 설명/,
    );
    expect(profitFactorInfo.getAttribute("aria-label")).toMatch(
      /이익 계수|총 이익/,
    );
  });

  it("sr-only span 으로 screen reader 전용 텍스트 부착", () => {
    const { container } = render(
      <MetricsCards metrics={METRICS} config={CONFIG} />,
    );
    const srOnly = container.querySelectorAll(".sr-only");
    // 5 KPI × sr-only span 1개씩 → 최소 5건 (다른 곳 의도된 sr-only 있을 수 있음)
    expect(srOnly.length).toBeGreaterThanOrEqual(5);
  });

  it("MDD 카드 설명에 '최대 낙폭' 또는 '고점 대비 최대 손실' 포함", () => {
    render(<MetricsCards metrics={METRICS} config={CONFIG} />);
    const mddInfo = screen.getByTestId("kpi-info-max-drawdown");
    expect(mddInfo.getAttribute("title")).toMatch(/최대 낙폭|손실 폭/);
  });
});
