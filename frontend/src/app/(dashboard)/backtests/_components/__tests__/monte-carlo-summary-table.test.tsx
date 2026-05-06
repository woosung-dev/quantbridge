// Sprint 37 BL-183: Monte Carlo 요약 통계 테이블 단위 테스트.
// fan chart 와 책임 분리 — 4 통계 (CI 95% 하한/상한, median, MDD p95) 노출.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { MonteCarloResult } from "@/features/backtest/schemas";
import { MonteCarloSummaryTable } from "../monte-carlo-summary-table";

// schema decimalString → number 변환 후 형태 (zod parse 결과 미러).
const RESULT: MonteCarloResult = {
  samples: 1000,
  ci_lower_95: 9500.5,
  ci_upper_95: 11000.25,
  median_final_equity: 10500,
  max_drawdown_mean: -0.05,
  max_drawdown_p95: -0.1234,
  equity_percentiles: {
    "5": [10000, 9800, 9500],
    "50": [10000, 10100, 10300],
    "95": [10000, 10400, 11000],
  },
};

describe("MonteCarloSummaryTable (BL-183)", () => {
  it("4 통계 row 라벨 표시", () => {
    render(<MonteCarloSummaryTable mcResult={RESULT} />);
    expect(screen.getByText(/CI 95% 하한/)).toBeInTheDocument();
    expect(screen.getByText(/CI 95% 상한/)).toBeInTheDocument();
    expect(screen.getByText(/Median final equity/)).toBeInTheDocument();
    expect(screen.getByText(/MDD p95/)).toBeInTheDocument();
  });

  // Sprint 37 Day 7 manual smoke (Playwright 자동 검증) 발견 — testid 누락으로
  // playwright `[data-testid="monte-carlo-summary-table"]` 셀렉터가 안 잡힘.
  // BL-187 의 일부로 testid 추가 → e2e 자동 검증 가능.
  it("BL-187 보강: section 에 data-testid 노출 (e2e 셀렉터)", () => {
    const { container } = render(<MonteCarloSummaryTable mcResult={RESULT} />);
    const section = container.querySelector(
      '[data-testid="monte-carlo-summary-table"]',
    );
    expect(section).not.toBeNull();
    expect(section?.getAttribute("aria-label")).toBe("Monte Carlo 요약 통계");
  });

  it("CI 하한/상한/median 은 천단위 콤마 + USDT 포맷 (소수점 2자리)", () => {
    render(<MonteCarloSummaryTable mcResult={RESULT} />);
    // formatCurrency: 9,500.50 / 11,000.25 / 10,500.00
    expect(screen.getByText(/9,500\.50 USDT/)).toBeInTheDocument();
    expect(screen.getByText(/11,000\.25 USDT/)).toBeInTheDocument();
    expect(screen.getByText(/10,500\.00 USDT/)).toBeInTheDocument();
  });

  it("MDD p95 는 percentage 포맷 (소수점 2자리)", () => {
    render(<MonteCarloSummaryTable mcResult={RESULT} />);
    // formatPercent(-0.1234, 2) → "-12.34%"
    expect(screen.getByText("-12.34%")).toBeInTheDocument();
  });

  it("samples 카운트가 표시된다 (참고 메타)", () => {
    render(<MonteCarloSummaryTable mcResult={RESULT} />);
    expect(screen.getByText(/samples 1,000/)).toBeInTheDocument();
  });

  it("mcResult=null 시 미실행 안내 표시", () => {
    render(<MonteCarloSummaryTable mcResult={null} />);
    expect(screen.getByText(/Monte Carlo 미실행/)).toBeInTheDocument();
  });

  it("mcResult=undefined 시 미실행 안내 표시", () => {
    render(<MonteCarloSummaryTable mcResult={undefined} />);
    expect(screen.getByText(/Monte Carlo 미실행/)).toBeInTheDocument();
  });

  it("aria-label 'Monte Carlo 요약 통계' a11y 적용", () => {
    render(<MonteCarloSummaryTable mcResult={RESULT} />);
    expect(
      screen.getByLabelText("Monte Carlo 요약 통계"),
    ).toBeInTheDocument();
  });

  it("role='table' 로 테이블 시멘틱 노출", () => {
    render(<MonteCarloSummaryTable mcResult={RESULT} />);
    expect(screen.getByRole("table")).toBeInTheDocument();
  });
});
