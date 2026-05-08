// 백테스트 폼 2열 layout + summary aside / preset pills 통합 테스트 — Sprint 42-polish W4
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { BacktestForm } from "../backtest-form";

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

describe("BacktestForm layout — Sprint 42-polish W4", () => {
  it("2열 grid wrapper 가 form + summary aside 양쪽 모두 렌더한다", () => {
    render(<BacktestForm />);

    const layout = screen.getByTestId("backtest-form-layout");
    expect(layout).toBeInTheDocument();
    // 모바일 1열 → md+ 2열 (2fr / 1fr) 클래스 확인
    expect(layout.className).toMatch(/grid-cols-1/);
    expect(layout.className).toMatch(/md:grid-cols-\[2fr_1fr\]/);

    // 양쪽 자식 모두 렌더
    expect(
      screen.getByRole("form", { name: "backtest-form" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("setup-summary-aside")).toBeInTheDocument();
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
