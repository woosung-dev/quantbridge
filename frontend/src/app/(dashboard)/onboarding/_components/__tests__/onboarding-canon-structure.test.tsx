// 온보딩 C 이식 시맨틱 구조 + 상태 4종 assert 테스트 (W3-E).
// 운영 계약 §4: 프로토타입 유래 핵심 시맨틱 클래스 구조(.ob-steps/.ob-stat/.state-box)를
// 못박고, KIT §6 상태 4종(스켈레톤/에러/빈·무데이터/정상)을 실제 렌더로 검증한다.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

// ── mocks ────────────────────────────────────────────────────────────────
const hoisted = vi.hoisted(() => ({
  backtestDetail: {
    value: { data: null as unknown, isError: false, isLoading: false, refetch: vi.fn() },
  },
  createPending: { value: false },
  progress: { value: null as unknown },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

vi.mock("@/features/backtest/hooks", () => ({
  useBacktest: () => hoisted.backtestDetail.value,
  useCreateBacktest: () => ({ mutate: vi.fn(), isPending: hoisted.createPending.value }),
  useBacktestProgress: () => ({ data: hoisted.progress.value }),
}));

import { ProgressStepper } from "../progress-stepper";
import { Step3Backtest } from "../step-3-backtest";
import { Step4Result } from "../step-4-result";

const STEPS = [
  { id: 1, label: "환영" },
  { id: 2, label: "샘플 전략" },
  { id: 3, label: "백테스트" },
  { id: 4, label: "결과" },
] as const;

afterEach(() => {
  cleanup();
  hoisted.backtestDetail.value = { data: null, isError: false, isLoading: false, refetch: vi.fn() };
  hoisted.createPending.value = false;
  hoisted.progress.value = null;
});

describe("ProgressStepper — C ob-steps 시맨틱 구조", () => {
  it("ob-steps / ob-step-num 렌더 + 완료·현재 상태 클래스", () => {
    const { container } = render(<ProgressStepper currentStep={4} steps={STEPS} />);
    expect(container.querySelector(".ob-steps")).not.toBeNull();
    // 반경 var(--r) 사각 배지 — 원형(rounded-full) 클래스가 아니다.
    const nums = container.querySelectorAll(".ob-step-num");
    expect(nums.length).toBe(4);
    // step 4 = 현재, step 1~3 = 완료.
    expect(container.querySelector(".ob-step.is-current")).not.toBeNull();
    expect(container.querySelectorAll(".ob-step.is-done").length).toBe(3);
  });
});

describe("Step4Result — 상태 4종 + ob-stat 구조", () => {
  it("정상: ob-stats/ob-stat/kpi-value/meter + disclaimer 렌더", () => {
    hoisted.backtestDetail.value = {
      data: { metrics: { total_return: "1.274", win_rate: "0.586", num_trades: 186 } },
      isError: false,
      isLoading: false,
      refetch: vi.fn(),
    };
    const { container } = render(
      <Step4Result backtestId="11111111-2222-4333-8444-555555555555" onFinish={vi.fn()} />,
    );
    expect(container.querySelector(".ob-stats")).not.toBeNull();
    expect(container.querySelectorAll(".ob-stat").length).toBe(3);
    // 승률은 분모가 있어 meter 를 그린다. 나머지 둘은 meter-void.
    expect(container.querySelector(".meter")).not.toBeNull();
    expect(container.querySelectorAll(".meter-void").length).toBe(2);
    expect(container.querySelector(".disclaimer")).not.toBeNull();
    expect(screen.getByText("+127.40%")).toBeInTheDocument();
    expect(screen.getByText("58.60%")).toBeInTheDocument();
    // 다음 단계 CTA + 캐논 카피 (§4.5 그리드 축약형 · B13 Bybit 데모).
    expect(container.querySelector(".cta.recommended")).not.toBeNull();
    expect(screen.getByText("그리드 9조합 (3 x 3) · 바 단위 이벤트 루프")).toBeInTheDocument();
    // 81조합 / 9x9 절대 금지 + pine_v2 미노출.
    const html = container.innerHTML;
    expect(html).not.toContain("81조합");
    expect(html).not.toContain("9x9");
    expect(html).not.toContain("9 x 9");
    expect(html).not.toContain("pine_v2");
    expect(screen.getByText(/Bybit 데모 한정/)).toBeInTheDocument();
  });

  it("에러(isError 보존): state-box failed + role=alert + 원인 A/B + state-code", () => {
    hoisted.backtestDetail.value = {
      data: null,
      isError: true,
      isLoading: false,
      refetch: vi.fn(),
    };
    const { container } = render(
      <Step4Result backtestId="11111111-2222-4333-8444-555555555555" onFinish={vi.fn()} />,
    );
    const box = container.querySelector(".state-box.failed");
    expect(box).not.toBeNull();
    expect(box?.getAttribute("role")).toBe("alert");
    // 원인 A/B 태그 2개.
    expect(container.querySelectorAll(".ob-cause-tag").length).toBe(2);
    expect(screen.getByText("원인 A")).toBeInTheDocument();
    expect(screen.getByText("원인 B")).toBeInTheDocument();
    // state-code 에 실제 엔드포인트.
    expect(screen.getByText(/GET \/api\/v1\/backtests\/11111111/)).toBeInTheDocument();
    // 완주 축하 헤드라인을 띄우지 않는다.
    expect(screen.queryByText(/첫 백테스트 완주/)).toBeNull();
  });

  it("무데이터: metrics 없음이면 KPI 값이 EMPTY_CELL(—) + title", () => {
    hoisted.backtestDetail.value = {
      data: { metrics: null },
      isError: false,
      isLoading: false,
      refetch: vi.fn(),
    };
    const { container } = render(
      <Step4Result backtestId="11111111-2222-4333-8444-555555555555" onFinish={vi.fn()} />,
    );
    const emptyCells = container.querySelectorAll(".kpi-value .dim[title]");
    expect(emptyCells.length).toBe(3);
    emptyCells.forEach((c) => expect(c.textContent).toBe("—"));
  });
});

describe("Step3Backtest — 스켈레톤 상태", () => {
  it("실행 중(create.isPending)이면 sk sk-line 스켈레톤을 렌더", () => {
    hoisted.createPending.value = true;
    const { container } = render(
      <Step3Backtest
        strategyId="11111111-2222-4333-8444-555555555555"
        onBacktestReady={vi.fn()}
        onBack={vi.fn()}
      />,
    );
    expect(container.querySelector(".sk.sk-line")).not.toBeNull();
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
  });
});
