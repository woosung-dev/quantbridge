// Sprint 32-D BL-156 — MetricsCards MDD leverage 가정 inline 검증.
//
// dogfood Day 3: KPI 카드 "MDD -132.96% / -343.15%" 표시 (leverage=1 가정 하
// 자본 100% 초과 손실 = 수학 모순). 본 테스트는 BE 메타 (mdd_exceeds_capital)
// 와 config.leverage 결합 시 caption 이 사용자 신뢰 quality bar 의무 정합.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  BacktestConfig,
  BacktestMetricsOut,
} from "@/features/backtest/schemas";
import { MetricsCards, buildMddCaption } from "../metrics-cards";

function makeMetrics(overrides: Partial<BacktestMetricsOut>): BacktestMetricsOut {
  return {
    total_return: 0.1,
    sharpe_ratio: 1.0,
    max_drawdown: -0.25,
    win_rate: 0.5,
    num_trades: 10,
    ...overrides,
  } as BacktestMetricsOut;
}

describe("MetricsCards — MDD leverage caption (Sprint 32-D BL-156)", () => {
  it("leverage=1 + MDD ∈ [-100%, 0%] → caption 미표시 (정상)", () => {
    render(
      <MetricsCards metrics={makeMetrics({ max_drawdown: -0.25 })} />,
    );
    expect(screen.queryByTestId("mdd-leverage-caption")).toBeNull();
  });

  it("leverage=5 + 정상 MDD → 'leverage 5.0x 가정' caption 표시", () => {
    const config: BacktestConfig = {
      leverage: 5,
      fees: 0.001,
      slippage: 0.0005,
      include_funding: true,
    };
    render(
      <MetricsCards
        metrics={makeMetrics({ max_drawdown: -0.5 })}
        config={config}
      />,
    );
    const caption = screen.getByTestId("mdd-leverage-caption");
    expect(caption).toHaveTextContent(/leverage 5\.0x/);
    expect(caption).toHaveTextContent(/가정/);
  });

  it("MDD < -100% (자본 초과) + leverage=1 → '자본 초과 손실' 강조", () => {
    // dogfood Day 3 시나리오 재현: -132.96% MDD + 1x 현물 가정.
    render(
      <MetricsCards
        metrics={makeMetrics({
          max_drawdown: -1.3296,
          mdd_exceeds_capital: true,
          mdd_unit: "equity_ratio",
        })}
        config={{
          leverage: 1,
          fees: 0.001,
          slippage: 0.0005,
          include_funding: true,
        }}
      />,
    );
    const caption = screen.getByTestId("mdd-leverage-caption");
    expect(caption).toHaveTextContent(/자본 초과 손실/);
    expect(caption).toHaveTextContent(/leverage 1x · 현물/);
  });

  it("MDD < -100% + leverage=5 → leverage 가정으로 해석 가능", () => {
    render(
      <MetricsCards
        metrics={makeMetrics({
          max_drawdown: -2.5,
          mdd_exceeds_capital: true,
        })}
        config={{
          leverage: 5,
          fees: 0.001,
          slippage: 0.0005,
          include_funding: true,
        }}
      />,
    );
    const caption = screen.getByTestId("mdd-leverage-caption");
    expect(caption).toHaveTextContent(/leverage 5\.0x/);
    expect(caption).toHaveTextContent(/자본 초과 손실/);
  });

  it("BE 메타 mdd_exceeds_capital 누락 (legacy 응답) → 클라이언트가 max_drawdown 으로 fallback 판정", () => {
    // 레거시 backtest (Sprint 32-D 이전) 는 BE 메타 없음.
    render(
      <MetricsCards
        metrics={makeMetrics({
          max_drawdown: -1.5, // -150%
          mdd_exceeds_capital: undefined,
        })}
      />,
    );
    const caption = screen.getByTestId("mdd-leverage-caption");
    expect(caption).toHaveTextContent(/자본 초과 손실/);
  });
});

describe("buildMddCaption — leverage 가정 표시 정책 (Sprint 32-D)", () => {
  it("leverage=1 + 정상 MDD → null (caption 표시 없음)", () => {
    expect(
      buildMddCaption({
        leverage: 1,
        mddBelowCapital: false,
        mddExceedsCapital: false,
      }),
    ).toBeNull();
  });

  it("leverage=2 + 정상 MDD → 'leverage 2.0x 가정'", () => {
    expect(
      buildMddCaption({
        leverage: 2,
        mddBelowCapital: false,
        mddExceedsCapital: false,
      }),
    ).toMatch(/leverage 2\.0x.*가정/);
  });

  it("자본 초과 손실 + leverage=1 → '자본 초과 손실' 강조", () => {
    expect(
      buildMddCaption({
        leverage: 1,
        mddBelowCapital: true,
        mddExceedsCapital: true,
      }),
    ).toMatch(/자본 초과 손실/);
  });

  it("BE 메타 우선 — mddExceedsCapital=null 이면 mddBelowCapital fallback", () => {
    // 레거시 응답 (Sprint 32-D 이전) — BE 메타 없음 → 클라이언트 판정.
    expect(
      buildMddCaption({
        leverage: 1,
        mddBelowCapital: true, // -100% 초과 (예: -1.32)
        mddExceedsCapital: null,
      }),
    ).toMatch(/자본 초과 손실/);
  });

  it("BE 메타 mddExceedsCapital=false 우선 — 클라이언트 mddBelowCapital 무시", () => {
    // 정상 응답 — BE 가 명시적으로 false → 정상 판정 우선.
    expect(
      buildMddCaption({
        leverage: 1,
        mddBelowCapital: false,
        mddExceedsCapital: false,
      }),
    ).toBeNull();
  });
});
