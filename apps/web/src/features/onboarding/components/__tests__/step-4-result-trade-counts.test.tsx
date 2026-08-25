// BL-822 — 온보딩 결과 카드 3개가 **서로 산술적으로 맞아야** 한다.
/**
 * ## 왜 이 파일이 있나
 *
 * 카드는 「승률」과 「거래 수」를 나란히 인쇄한다. 거래 수가 BE 의 `num_trades`(미청산 포함,
 * Sprint 31-E/BL-155 override) 였을 때, 실측 backtest 20128227 은 **「13건 · 16.67%」** 를
 * 보여 줬다 — 곱하면 2.17 이라 어떤 정수 승수로도 설명되지 않는다. 게다가 그 13 옆의
 * 각주는 「진입·청산이 **완료된** 건수입니다」라고 적혀 있었다(거짓 라벨).
 *
 * 사용자가 처음 보는 결과 화면이라 제품 핵심 축(PRD §1 「결과가 정직하게 보이는가」)에 직결한다.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const mockUseBacktest = vi.fn();

vi.mock("@/features/backtest/hooks", () => ({
  useBacktest: (...args: unknown[]) => mockUseBacktest(...args),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

import { Step4Result } from "../step-4-result";

const BACKTEST_ID = "11111111-1111-4111-8111-111111111111";

function mockMetrics(metrics: Record<string, unknown> | null) {
  mockUseBacktest.mockReturnValue({
    data: metrics === null ? undefined : { metrics },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  });
}

function renderCard() {
  return render(<Step4Result backtestId={BACKTEST_ID} onFinish={() => {}} />);
}

function statValue(label: string): string {
  const stat = screen.getByText(label).closest(".ob-stat");
  return stat?.querySelector(".kpi-value")?.textContent?.trim() ?? "";
}

describe("Step4Result 결과 카드의 거래 수 (BL-822)", () => {
  it("실측 케이스 재현 — 13 이 아니라 완료 12 를 인쇄하고 승률과 곱해 정수가 된다", () => {
    // backtest 20128227: JSONB num_trades 12 · win_rate 2/12, detail API 는 13 으로 override.
    mockMetrics({
      total_return: "0.1",
      win_rate: "0.166667",
      num_trades: 13,
      completed_trades: 12,
    });
    renderCard();

    expect(statValue("거래 수")).toBe("12");
    const winRate = Number("0.166667");
    const shown = Number(statValue("거래 수"));
    expect(Math.round(winRate * shown)).toBe(2);
    // 정직성 축 — 표시된 분모로 계산한 승리 건수가 반올림 오차 0.05건 안이어야 한다.
    expect(Math.abs(winRate * shown - 2)).toBeLessThan(0.05);
  });

  it("미청산이 있으면 각주가 제외 사실을 말한다", () => {
    mockMetrics({
      total_return: "0.1",
      win_rate: "0.166667",
      num_trades: 13,
      completed_trades: 12,
    });
    renderCard();

    const foot = screen.getByText("거래 수").closest(".ob-stat")?.querySelector(".kpi-foot");
    expect(foot?.textContent).toContain("진입·청산이 완료된 건수입니다.");
    expect(foot?.textContent).toContain("미청산 1건은 제외했습니다.");
  });

  it("음성 대조 — 미청산이 없으면 제외 문구가 붙지 않는다", () => {
    mockMetrics({
      total_return: "0.1",
      win_rate: "0.5",
      num_trades: 12,
      completed_trades: 12,
    });
    renderCard();

    expect(statValue("거래 수")).toBe("12");
    const foot = screen.getByText("거래 수").closest(".ob-stat")?.querySelector(".kpi-foot");
    expect(foot?.textContent).not.toContain("미청산");
  });

  it("completed_trades 없는 구 응답도 무너지지 않는다 — num_trades 로 접는다", () => {
    mockMetrics({ total_return: "0.1", win_rate: "0.5", num_trades: 8 });
    renderCard();

    expect(statValue("거래 수")).toBe("8");
  });
});
