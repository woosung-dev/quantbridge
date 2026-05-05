// Sprint 33 BL-164 — live-session-form dropdown UUID 노출 차단 회귀.
//
// 검증 범위:
//   1) strategy dropdown trigger 가 placeholder (이름)을 표시. 초기 UUID 노출 X.
//   2) strategy 선택 후 trigger 가 strategy.name 을 표시 (UUID 미노출).
//   3) exchange dropdown trigger 가 placeholder + 선택 후 label 을 표시.
//   4) UUID 가 trigger DOM 어디에도 표시되지 않음 (회귀 가드).
//
// base-ui Select 의 비결정적 popup 을 회피하기 위해 native <select> 로 mock.
// 헬퍼 SelectWithDisplayName 은 mock 된 SelectValue 의 children 함수형
// render prop 을 호출 → label 표시. 이 흐름이 깨지면 테스트 실패.

import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// ── React Query / Clerk 환경 ──
beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ userId: "u1", getToken: async () => "test-token" }),
}));

// ── useRegisterLiveSession mock ──
const mutateAsyncMock = vi.fn();
vi.mock("../../hooks", () => ({
  useRegisterLiveSession: () => ({
    mutateAsync: mutateAsyncMock,
    isPending: false,
  }),
}));

// ── sonner toast mock ──
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// ── base-ui Select 를 native <select> 로 mock ──
//
// 헬퍼 SelectWithDisplayName 은 다음과 같이 SelectValue 를 호출:
//   <SelectValue placeholder={...}>{() => selectedLabel ?? placeholder}</SelectValue>
// → mock 에서 children 이 함수면 호출 결과를, 아니면 placeholder 를 표시.
vi.mock("@/components/ui/select", () => {
  type SelectProps = React.PropsWithChildren<{
    value?: string;
    onValueChange?: (v: string) => void;
    disabled?: boolean;
  }>;
  type ChildrenLike =
    | React.ReactNode
    | ((value: string | null) => React.ReactNode);
  type ValueProps = {
    placeholder?: React.ReactNode;
    children?: ChildrenLike;
  };
  type ItemProps = React.PropsWithChildren<{
    value: string;
    disabled?: boolean;
  }>;

  // value/onValueChange 를 SelectItem 으로 전달.
  const Ctx = React.createContext<{
    value: string;
    onValueChange?: (v: string) => void;
  }>({ value: "" });

  const Select = ({ children, value = "", onValueChange }: SelectProps) => (
    <Ctx.Provider value={{ value, onValueChange }}>
      <div data-testid="mock-select">{children}</div>
    </Ctx.Provider>
  );
  const SelectTrigger = ({
    children,
    ...rest
  }: React.PropsWithChildren<Record<string, unknown>>) => (
    <div data-mock-select-trigger {...rest}>
      {children}
    </div>
  );
  const SelectValue = ({ placeholder, children }: ValueProps) => {
    const ctx = React.useContext(Ctx);
    const rendered =
      typeof children === "function"
        ? (children as (v: string | null) => React.ReactNode)(ctx.value || null)
        : (children ?? placeholder);
    return <span data-mock-select-value>{rendered}</span>;
  };
  const SelectContent = ({ children }: React.PropsWithChildren) => (
    <div>{children}</div>
  );
  const SelectItem = ({ value, children, disabled }: ItemProps) => {
    const ctx = React.useContext(Ctx);
    return (
      <button
        type="button"
        data-mock-select-item
        data-value={value}
        disabled={disabled}
        onClick={() => ctx.onValueChange?.(value)}
      >
        {children}
      </button>
    );
  };

  return {
    Select,
    SelectTrigger,
    SelectValue,
    SelectContent,
    SelectItem,
  };
});

import { LiveSessionForm } from "../live-session-form";

const STRATEGY_ID = "11111111-1111-4111-a111-111111111111";
const STRATEGY_NAME = "BTC Momentum v2";
const ACCOUNT_ID = "550e8400-e29b-41d4-a716-446655440000";
const ACCOUNT_LABEL = "main-demo";

function renderForm() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <LiveSessionForm
        strategies={[{ id: STRATEGY_ID, name: STRATEGY_NAME }]}
        exchangeAccounts={[
          {
            id: ACCOUNT_ID,
            exchange: "bybit",
            mode: "demo",
            label: ACCOUNT_LABEL,
          },
        ]}
        activeSessionsCount={0}
      />
    </QueryClientProvider>,
  );
}

describe("LiveSessionForm — BL-164 dropdown UUID 노출 차단", () => {
  it("strategy dropdown trigger 가 초기에는 placeholder 를 표시 (UUID 노출 X)", () => {
    renderForm();
    const trigger = screen.getByTestId("live-session-strategy-trigger");
    expect(trigger).toHaveTextContent("전략 선택");
    expect(trigger).not.toHaveTextContent(STRATEGY_ID);
  });

  it("strategy 선택 후 trigger 가 strategy.name 을 표시 (UUID 미노출)", () => {
    renderForm();
    // 헬퍼 내 SelectItem 은 mock 의 button 으로 렌더 → 클릭으로 onValueChange 트리거.
    const items = screen
      .getAllByText(STRATEGY_NAME)
      .map((el) => el.closest("button"))
      .filter((el): el is HTMLButtonElement => el !== null);
    // dropdown content 안의 button 1개 (trigger 는 div).
    expect(items.length).toBeGreaterThanOrEqual(1);
    const firstItem = items[0];
    if (!firstItem) throw new Error("expected at least 1 select item");
    fireEvent.click(firstItem);

    const trigger = screen.getByTestId("live-session-strategy-trigger");
    expect(trigger).toHaveTextContent(STRATEGY_NAME);
    expect(trigger).not.toHaveTextContent(STRATEGY_ID);
  });

  it("exchange dropdown trigger 가 초기에는 placeholder, 선택 후 label 을 표시 (UUID 미노출)", () => {
    renderForm();
    const trigger = screen.getByTestId("live-session-account-trigger");
    expect(trigger).toHaveTextContent("Bybit Demo 계정 선택");
    expect(trigger).not.toHaveTextContent(ACCOUNT_ID);

    const items = screen
      .getAllByText(ACCOUNT_LABEL)
      .map((el) => el.closest("button"))
      .filter((el): el is HTMLButtonElement => el !== null);
    expect(items.length).toBeGreaterThanOrEqual(1);
    const firstItem = items[0];
    if (!firstItem) throw new Error("expected at least 1 select item");
    fireEvent.click(firstItem);

    expect(trigger).toHaveTextContent(ACCOUNT_LABEL);
    expect(trigger).not.toHaveTextContent(ACCOUNT_ID);
  });

  it("회귀 가드 — UUID 가 두 trigger 어디에도 표시되지 않음 (선택 후)", () => {
    renderForm();
    // strategy + exchange 각각 선택.
    const strategyItems = screen
      .getAllByText(STRATEGY_NAME)
      .map((el) => el.closest("button"))
      .filter((el): el is HTMLButtonElement => el !== null);
    const firstStrategy = strategyItems[0];
    if (!firstStrategy) throw new Error("expected strategy item");
    fireEvent.click(firstStrategy);

    const accountItems = screen
      .getAllByText(ACCOUNT_LABEL)
      .map((el) => el.closest("button"))
      .filter((el): el is HTMLButtonElement => el !== null);
    const firstAccount = accountItems[0];
    if (!firstAccount) throw new Error("expected account item");
    fireEvent.click(firstAccount);

    const strategyTrigger = screen.getByTestId("live-session-strategy-trigger");
    const accountTrigger = screen.getByTestId("live-session-account-trigger");
    expect(strategyTrigger.textContent ?? "").not.toContain(STRATEGY_ID);
    expect(accountTrigger.textContent ?? "").not.toContain(ACCOUNT_ID);
  });
});

describe("LiveSessionForm — BL-164 emptyMessage", () => {
  it("Bybit Demo 계정이 0개일 때 emptyMessage 가 표시되고 disabled", () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={qc}>
        <LiveSessionForm
          strategies={[{ id: STRATEGY_ID, name: STRATEGY_NAME }]}
          exchangeAccounts={[]}
          activeSessionsCount={0}
        />
      </QueryClientProvider>,
    );
    expect(
      screen.getByText("Bybit Demo 계정 없음 — 먼저 등록해주세요"),
    ).toBeInTheDocument();
    // submit 버튼 disabled 검증.
    const submit = screen.getByTestId("live-session-submit");
    expect(submit).toBeDisabled();
  });
});
