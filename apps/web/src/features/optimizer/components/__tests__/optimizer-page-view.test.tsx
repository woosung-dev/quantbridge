// OptimizerPageView 판정 경계 회귀 — 완료 Backtest만 picker에 남기고 선택한 방식의 폼 하나만 연다.
// 하위 폼·실행 목록은 각자 상태를 가지므로 여기서는 식별 가능한 더미로 조립만 고정한다.

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OPTIMIZATION_KIND_LABEL } from "@/features/optimizer/labels";
import type {
  BacktestListResponse,
  BacktestStatus,
  BacktestSummary,
} from "@/features/backtest/schemas";

const useBacktests = vi.fn();
vi.mock("@/features/backtest/hooks", () => ({
  useBacktests: (...a: unknown[]) => useBacktests(...a),
}));

vi.mock("../bayesian-search-form", () => ({
  BayesianSearchForm: () => <div data-testid="form-bayesian" />,
}));
vi.mock("../genetic-search-form", () => ({
  GeneticSearchForm: () => <div data-testid="form-genetic" />,
}));
vi.mock("../grid-search-form", () => ({
  GridSearchForm: () => <div data-testid="form-grid" />,
}));
vi.mock("../optimizer-run-list", () => ({
  OptimizerRunList: () => <div data-testid="optimizer-run-list" />,
}));

// Base UI popup은 jsdom에서 비결정적이므로, SelectWithDisplayName의 value/options 연결만 native button으로
// 바꾼다. 실제 helper는 그대로 렌더해 완료 Backtest 옵션 변환을 이 테스트가 검증한다.
vi.mock("@/components/ui/select", () => {
  type SelectProps = React.PropsWithChildren<{
    value?: string;
    onValueChange?: (value: string) => void;
    disabled?: boolean;
  }>;
  type ItemProps = React.PropsWithChildren<{
    value: string;
    disabled?: boolean;
  }>;

  const SelectContext = React.createContext<{
    value: string;
    onValueChange?: (value: string) => void;
  }>({ value: "" });

  function Select({ children, value = "", onValueChange }: SelectProps) {
    return (
      <SelectContext.Provider value={{ value, onValueChange }}>
        <div>{children}</div>
      </SelectContext.Provider>
    );
  }

  function SelectTrigger({
    children,
    ...props
  }: React.PropsWithChildren<Record<string, unknown>>) {
    return <div {...props}>{children}</div>;
  }

  function SelectValue({
    placeholder,
    children,
  }: {
    placeholder?: React.ReactNode;
    children?: React.ReactNode | ((value: string | null) => React.ReactNode);
  }) {
    const { value } = React.useContext(SelectContext);
    const rendered =
      typeof children === "function" ? children(value || null) : (children ?? placeholder);
    return <span>{rendered}</span>;
  }

  function SelectContent({ children }: React.PropsWithChildren) {
    return <div>{children}</div>;
  }

  function SelectItem({ value, children, disabled }: ItemProps) {
    const { onValueChange } = React.useContext(SelectContext);
    return (
      <button
        type="button"
        data-mock-select-item
        disabled={disabled}
        onClick={() => onValueChange?.(value)}
      >
        {children}
      </button>
    );
  }

  return { Select, SelectContent, SelectItem, SelectTrigger, SelectValue };
});

import { OptimizerPageView } from "../optimizer-page-view";

const COMPLETED_BACKTEST_ID = "11111111-1111-4111-a111-111111111111";

function backtest(status: BacktestStatus, id: string, symbol: string): BacktestSummary {
  return {
    id,
    strategy_id: "22222222-2222-4222-a222-222222222222",
    symbol,
    timeframe: "1h",
    period_start: "2026-01-01T00:00:00+00:00",
    period_end: "2026-01-31T00:00:00+00:00",
    status,
    created_at: "2026-02-01T00:00:00+00:00",
    completed_at: status === "completed" ? "2026-02-01T01:00:00+00:00" : null,
  };
}

const COMPLETED_BACKTEST = backtest(
  "completed",
  COMPLETED_BACKTEST_ID,
  "BTC/USDT",
);

function mockBacktests(
  items: BacktestSummary[] = [COMPLETED_BACKTEST],
  options: { isLoading?: boolean; isPending?: boolean; data?: BacktestListResponse } = {},
) {
  useBacktests.mockReturnValue({
    data:
      options.data ?? {
        items,
        total: items.length,
        limit: 100,
        offset: 0,
      },
    isLoading: options.isLoading ?? false,
    isPending: options.isPending ?? false,
  });
}

function selectBacktestAndOpenForm() {
  fireEvent.click(screen.getByRole("button", { name: /BTC\/USDT/ }));
  fireEvent.click(
    screen.getByRole("button", {
      name: `${OPTIMIZATION_KIND_LABEL.grid_search} 새 실행`,
    }),
  );
}

beforeEach(() => {
  mockBacktests();
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("OptimizerPageView", () => {
  it("로딩 중 data가 undefined여도 렌더에서 던지지 않는다", () => {
    useBacktests.mockReturnValue({ data: undefined, isPending: true });

    expect(() => render(<OptimizerPageView />)).not.toThrow();
  });

  it("completed Backtest만 picker 옵션으로 만든다", () => {
    mockBacktests([
      COMPLETED_BACKTEST,
      backtest("completed", "33333333-3333-4333-a333-333333333333", "ETH/USDT"),
      backtest("running", "44444444-4444-4444-a444-444444444444", "SOL/USDT"),
      backtest("failed", "55555555-5555-4555-a555-555555555555", "XRP/USDT"),
    ]);
    const { container } = render(<OptimizerPageView />);

    const options = container.querySelectorAll("[data-mock-select-item]");
    expect(options).toHaveLength(2);
    expect(container).toHaveTextContent("BTC/USDT");
    expect(container).toHaveTextContent("ETH/USDT");
    expect(container).not.toHaveTextContent("SOL/USDT");
    expect(container).not.toHaveTextContent("XRP/USDT");
  });

  it("완료 Backtest가 없으면 옵션 없이 안내 문구를 표시한다", () => {
    mockBacktests([
      backtest("running", "44444444-4444-4444-a444-444444444444", "SOL/USDT"),
    ]);
    const { container } = render(<OptimizerPageView />);

    expect(container.querySelectorAll("[data-mock-select-item]")).toHaveLength(0);
    expect(screen.getByText("완료된 백테스트 없음")).toBeInTheDocument();
  });

  it("기본 알고리즘은 grid_search이며 선택 후 GridSearchForm만 연다", () => {
    render(<OptimizerPageView />);

    expect(screen.getByLabelText("최적화 알고리즘")).toHaveValue("grid_search");
    selectBacktestAndOpenForm();
    expect(screen.getByTestId("form-grid")).toBeInTheDocument();
    expect(screen.queryByTestId("form-bayesian")).not.toBeInTheDocument();
    expect(screen.queryByTestId("form-genetic")).not.toBeInTheDocument();
  });

  it("알고리즘을 bayesian·genetic으로 바꾸면 선택한 폼 하나만 연다", () => {
    render(<OptimizerPageView />);
    selectBacktestAndOpenForm();

    fireEvent.change(screen.getByLabelText("최적화 알고리즘"), {
      target: { value: "bayesian" },
    });
    expect(screen.queryByTestId("form-grid")).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", {
        name: `${OPTIMIZATION_KIND_LABEL.bayesian} 새 실행`,
      }),
    );
    expect(screen.getByTestId("form-bayesian")).toBeInTheDocument();
    expect(screen.queryByTestId("form-grid")).not.toBeInTheDocument();
    expect(screen.queryByTestId("form-genetic")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("최적화 알고리즘"), {
      target: { value: "genetic" },
    });
    expect(screen.queryByTestId("form-bayesian")).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", {
        name: `${OPTIMIZATION_KIND_LABEL.genetic} 새 실행`,
      }),
    );
    expect(screen.getByTestId("form-genetic")).toBeInTheDocument();
    expect(screen.queryByTestId("form-grid")).not.toBeInTheDocument();
    expect(screen.queryByTestId("form-bayesian")).not.toBeInTheDocument();
  });

  it("알고리즘 표시 문자열은 labels.ts의 SSOT를 사용한다", () => {
    render(<OptimizerPageView />);

    for (const label of Object.values(OPTIMIZATION_KIND_LABEL)) {
      expect(screen.getByRole("option", { name: new RegExp(label) })).toBeInTheDocument();
    }
  });

  it("OptimizerRunList는 선택 및 알고리즘 상태와 무관하게 남아 있다", () => {
    render(<OptimizerPageView />);

    expect(screen.getByTestId("optimizer-run-list")).toBeInTheDocument();
    selectBacktestAndOpenForm();
    fireEvent.change(screen.getByLabelText("최적화 알고리즘"), {
      target: { value: "bayesian" },
    });
    expect(screen.getByTestId("optimizer-run-list")).toBeInTheDocument();
  });

  it("PICKER_LIMIT와 offset 0을 useBacktests의 첫 인자로 전달한다", () => {
    render(<OptimizerPageView />);

    expect(useBacktests.mock.calls[0]?.[0]).toEqual({ limit: 100, offset: 0 });
  });

  it("양성 대조: mock useBacktests가 호출되고 렌더 텍스트가 비어 있지 않다", () => {
    const { container } = render(<OptimizerPageView />);

    expect(useBacktests).toHaveBeenCalled();
    expect(container.textContent?.trim()).not.toBe("");
  });
});
