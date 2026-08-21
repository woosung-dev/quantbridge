// 백테스트 폼 2단 layout + 요약 사이드 / 기간 프리셋 통합 테스트 — C 이식(W3-A).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { BacktestForm } from "@/features/backtest/components/forms/backtest-form";

const strategies = {
  data: {
    items: [{ id: "abc", name: "Test strategy", parse_status: "ok" }],
  },
};

let mockSearchParams = new URLSearchParams();
const routerPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: routerPush, replace: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => mockSearchParams,
}));

vi.mock("@/features/strategy/hooks", () => ({
  useStrategies: () => strategies,
  useStrategy: () => ({ data: null, isLoading: false, isError: false }),
}));

vi.mock("@/features/backtest/hooks", () => ({
  useCreateBacktest: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

beforeEach(() => {
  mockSearchParams = new URLSearchParams("strategy_id=abc");
});

afterEach(() => {
  cleanup();
});

describe("BacktestForm layout — C 이식(W3-A)", () => {
  it("setup-grid 2단 wrapper 가 form + summary aside 양쪽 모두 렌더한다", () => {
    render(<BacktestForm />);

    const layout = screen.getByTestId("backtest-form-layout");
    expect(layout).toBeInTheDocument();
    // C 디자인 언어 2단 레이아웃 클래스 (globals.css .setup-grid 이 minmax(0,1fr) 340px)
    expect(layout.className).toMatch(/setup-grid/);

    // 양쪽 자식 모두 렌더
    expect(screen.getByRole("form", { name: "backtest-form" })).toBeInTheDocument();
    expect(screen.getByTestId("setup-summary-aside")).toBeInTheDocument();

    // h1 은 동사형 화면명(5축 규약 — h1 만 동사형)
    expect(screen.getByRole("heading", { level: 1, name: "새 백테스트 실행" })).toBeInTheDocument();
  });

  it("date preset 1Y 클릭 시 시작/종료일 input 값과 summary 기간 row 가 함께 갱신된다", () => {
    render(<BacktestForm />);

    fireEvent.click(screen.getByTestId("date-preset-1y"));

    const start = screen.getByLabelText("시작일") as HTMLInputElement;
    const end = screen.getByLabelText("종료일") as HTMLInputElement;
    expect(start.value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(end.value).toMatch(/^\d{4}-\d{2}-\d{2}$/);

    // 365일 preset 이라 summary 기간 row 에 일수 표시
    expect(screen.getByTestId("summary-row-기간")).toHaveTextContent(/일\)/);
  });
});
