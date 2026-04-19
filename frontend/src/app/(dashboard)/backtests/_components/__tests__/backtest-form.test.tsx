import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { BacktestForm } from "../backtest-form";

const strategies = {
  data: {
    items: [
      { id: "abc", name: "Test strategy", parse_status: "ok" },
      { id: "xyz", name: "Other", parse_status: "ok" },
    ],
  },
};

let mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => mockSearchParams,
}));

vi.mock("@/features/strategy/hooks", () => ({
  useStrategies: () => strategies,
}));

vi.mock("@/features/backtest/hooks", () => ({
  useCreateBacktest: () => ({ mutate: vi.fn(), isPending: false }),
}));

describe("BacktestForm — searchParams strategy_id 프리필", () => {
  it("searchParams strategy_id=abc 일 때 숨김 input value 가 'abc'", () => {
    mockSearchParams = new URLSearchParams("strategy_id=abc");
    const { container } = render(<BacktestForm />);

    const hidden = container.querySelector<HTMLInputElement>(
      'input[type="hidden"][name="strategy_id"]',
    );
    expect(hidden).not.toBeNull();
    expect(hidden?.value).toBe("abc");
  });

  it("searchParams 없을 때 초기값은 빈 문자열 (placeholder 노출)", () => {
    mockSearchParams = new URLSearchParams();
    const { container } = render(<BacktestForm />);

    const hidden = container.querySelector<HTMLInputElement>(
      'input[type="hidden"][name="strategy_id"]',
    );
    expect(hidden?.value).toBe("");
    expect(screen.getByText(/전략을 선택하세요/)).toBeInTheDocument();
  });
});
