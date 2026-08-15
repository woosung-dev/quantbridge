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

import { ApiError } from "@/lib/api-client";

// ── React Query / Clerk 환경 ──
beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
  mutateAsyncMock.mockReset();
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

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
            read_only: null,
          },
        ]}
        activeSessionsCount={0}
      />
    </QueryClientProvider>,
  );
}

function submitValidForm() {
  const strategy = screen
    .getAllByText(STRATEGY_NAME)
    .map((element) => element.closest("button"))
    .find((element): element is HTMLButtonElement => element !== null);
  if (!strategy) throw new Error("expected strategy item");
  fireEvent.click(strategy);

  const account = screen
    .getAllByText(ACCOUNT_LABEL)
    .map((element) => element.closest("button"))
    .find((element): element is HTMLButtonElement => element !== null);
  if (!account) throw new Error("expected account item");
  fireEvent.click(account);

  fireEvent.click(screen.getByTestId("live-session-submit"));
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
    expect(trigger).toHaveTextContent("Bybit 데모 계정 선택");
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
      screen.getByText("Bybit 데모 계정 없음. 먼저 등록해주세요"),
    ).toBeInTheDocument();
    // submit 버튼 disabled 검증.
    const submit = screen.getByTestId("live-session-submit");
    expect(submit).toBeDisabled();
  });
});

describe("LiveSessionForm — 읽기 전용 계정", () => {
  it("읽기 전용 계정은 표시되지만 선택할 수 없고 false·null 계정은 선택할 수 있다", () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={qc}>
        <LiveSessionForm
          strategies={[{ id: STRATEGY_ID, name: STRATEGY_NAME }]}
          exchangeAccounts={[
            {
              id: "550e8400-e29b-41d4-a716-446655440001",
              exchange: "bybit",
              mode: "demo",
              label: "read-only-demo",
              read_only: true,
            },
            {
              id: "550e8400-e29b-41d4-a716-446655440002",
              exchange: "bybit",
              mode: "demo",
              label: "writable-demo",
              read_only: false,
            },
            {
              id: "550e8400-e29b-41d4-a716-446655440003",
              exchange: "bybit",
              mode: "demo",
              label: "legacy-demo",
              read_only: null,
            },
          ]}
          activeSessionsCount={0}
        />
      </QueryClientProvider>,
    );

    expect(screen.getByRole("button", { name: "read-only-demo (읽기 전용)" })).toBeDisabled();

    const writable = screen.getByRole("button", { name: "writable-demo" });
    const legacy = screen.getByRole("button", { name: "legacy-demo" });
    expect(writable).toBeEnabled();
    expect(legacy).toBeEnabled();

    fireEvent.click(writable);
    expect(screen.getByTestId("live-session-account-trigger")).toHaveTextContent("writable-demo");
    fireEvent.click(legacy);
    expect(screen.getByTestId("live-session-account-trigger")).toHaveTextContent("legacy-demo");
  });
});

describe("LiveSessionForm — 라이브 세션 시작 거부 사유", () => {
  /** 서로 다른 422 응답을 대조해 서버 detail을 하드코딩 없이 그대로 표시함을 검증한다. */
  it("다른 422 는 자기 문구를 낸다", async () => {
    const detail = "활성 라이브 세션 한도를 초과했습니다.";
    mutateAsyncMock.mockRejectedValue(
      new ApiError(422, "live_session_quota_exceeded", "API 422 /api/v1/live-sessions", {
        detail: { code: "live_session_quota_exceeded", detail },
      }),
    );

    renderForm();
    submitValidForm();

    expect(await screen.findByTestId("live-session-form-error")).toHaveTextContent(detail);
  });

  it("detail 이 없는 응답은 폴백 문구", async () => {
    mutateAsyncMock.mockRejectedValue(new ApiError(422, "unknown", ""));

    renderForm();
    submitValidForm();

    const error = await screen.findByTestId("live-session-form-error");
    expect(error).toHaveTextContent("세션을 시작하지 못했습니다. 잠시 후 다시 시도해주세요.");
    expect(error).not.toHaveTextContent("API 422");
  });
});
