// Sprint 38 BL-188 v3 B — 4-state Live mirror + D2 manual override toggle 검증
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";

import { BacktestForm } from "../backtest-form";
import { CreateBacktestRequestSchema } from "@/features/backtest/schemas";

// 전략 목록 (useStrategies stub) — 4 case 모두 동일.
const strategiesList = {
  data: {
    items: [
      { id: "abc", name: "Test strategy", parse_status: "ok" },
    ],
  },
};

// strategy detail (useStrategy) 가 case 별로 달라지므로 동적으로 swap.
type StrategyDetail = {
  id: string;
  trading_sessions?: string[];
  settings?: { leverage: number; position_size_pct: number; margin_mode: string; schema_version: number } | null;
  pine_declared_qty?: { type?: string | null; value?: number | null } | null;
} | null;
let mockStrategyDetail: StrategyDetail = null;

const routerPush = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: routerPush, replace: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => mockSearchParams,
}));

vi.mock("@/features/strategy/hooks", () => ({
  useStrategies: () => strategiesList,
  useStrategy: () => ({ data: mockStrategyDetail, isLoading: false, isError: false }),
}));

type CapturedOpts = {
  onSuccess?: (data: { backtest_id: string }) => void;
  onError?: (err: Error) => void;
};
const capturedOpts: { current: CapturedOpts } = { current: {} };
const mutate = vi.fn();

vi.mock("@/features/backtest/hooks", () => ({
  useCreateBacktest: (opts: CapturedOpts = {}) => {
    capturedOpts.current = opts;
    return { mutate, isPending: false };
  },
}));

const toastError = vi.fn();
const toastSuccess = vi.fn();
vi.mock("sonner", () => ({
  toast: {
    error: (...args: unknown[]) => toastError(...args),
    success: (...args: unknown[]) => toastSuccess(...args),
  },
}));

beforeEach(() => {
  mockSearchParams = new URLSearchParams("strategy_id=abc");
  routerPush.mockReset();
  mutate.mockReset();
  toastError.mockReset();
  toastSuccess.mockReset();
  capturedOpts.current = {};
  mockStrategyDetail = null;
});

afterEach(() => {
  cleanup();
});

describe("BacktestForm Live Settings mirror (BL-188 v3 B — 4-state)", () => {
  it("(1) Pine 명시 strategy → Pine override 배지 + manual 폼 disabled", async () => {
    // Pine 명시 — pine_declared_qty 가 BE A2 후 strategy detail 에 포함될 forward-ready 검증.
    mockStrategyDetail = {
      id: "abc",
      trading_sessions: [],
      settings: null,
      pine_declared_qty: { type: "strategy.cash", value: 5000 },
    };
    await act(async () => {
      render(<BacktestForm />);
    });

    expect(
      screen.getByTestId("live-settings-badge-pine"),
    ).toBeInTheDocument();
    // Pine override 시 default qty 폼 disabled.
    const qtyTypeSelect = screen.getByTestId(
      "default-qty-type-select",
    ) as HTMLSelectElement;
    expect(qtyTypeSelect.disabled).toBe(true);
    const qtyValueInput = screen.getByTestId(
      "default-qty-value-input",
    ) as HTMLInputElement;
    expect(qtyValueInput.disabled).toBe(true);
  });

  it("(2) Live 1x 30% strategy → Live mirror 배지 + position_size_pct=30 prefill", async () => {
    // Live 1x — mirror 가능, position_size_pct prefill.
    mockStrategyDetail = {
      id: "abc",
      trading_sessions: [],
      settings: {
        schema_version: 1,
        leverage: 1,
        margin_mode: "cross",
        position_size_pct: 30,
      },
    };
    await act(async () => {
      render(<BacktestForm />);
    });

    expect(
      screen.getByTestId("live-settings-badge-live"),
    ).toBeInTheDocument();
    const pctInput = screen.getByTestId(
      "position-size-pct-input",
    ) as HTMLInputElement;
    expect(pctInput.value).toBe("30");
    expect(pctInput.readOnly).toBe(true);
  });

  it("(3) Live 3x isolated strategy → Mirror 불가 배지 + manual 폼 enabled", async () => {
    // Live Nx leverage — mirror 차단, manual 입력만 가능.
    mockStrategyDetail = {
      id: "abc",
      trading_sessions: [],
      settings: {
        schema_version: 1,
        leverage: 3,
        margin_mode: "isolated",
        position_size_pct: 25,
      },
    };
    await act(async () => {
      render(<BacktestForm />);
    });

    const blockedBadge = screen.getByTestId("live-settings-badge-blocked");
    expect(blockedBadge).toBeInTheDocument();
    expect(blockedBadge.textContent).toMatch(/3x/);
    // manual 폼 enabled (sizing source 가 live_blocked_leverage 이므로 폼 활성화).
    const qtyTypeSelect = screen.getByTestId(
      "default-qty-type-select",
    ) as HTMLSelectElement;
    expect(qtyTypeSelect.disabled).toBe(false);
  });

  it("(4) Live 1x → Manual toggle → position_size_pct=null + double-sizing Zod reject", async () => {
    // Live 1x 시작 → 사용자 Manual 토글 → 두 sizing 동시 = Zod refine reject 검증.
    mockStrategyDetail = {
      id: "abc",
      trading_sessions: [],
      settings: {
        schema_version: 1,
        leverage: 1,
        margin_mode: "cross",
        position_size_pct: 50,
      },
    };
    await act(async () => {
      render(<BacktestForm />);
    });

    expect(
      screen.getByTestId("live-settings-badge-live"),
    ).toBeInTheDocument();

    // Manual 로 토글 — sizing-source-select 가 노출되어야 함.
    const sourceSelect = screen.getByTestId(
      "sizing-source-select",
    ) as HTMLSelectElement;
    await act(async () => {
      fireEvent.change(sourceSelect, { target: { value: "manual" } });
    });

    // Manual toggle 후 → manual 폼 enabled.
    expect(
      screen.getByTestId("live-settings-badge-manual"),
    ).toBeInTheDocument();
    const qtyTypeSelect = screen.getByTestId(
      "default-qty-type-select",
    ) as HTMLSelectElement;
    expect(qtyTypeSelect.disabled).toBe(false);

    // Zod schema 차원 double-sizing reject 검증 (BE _no_double_sizing parity).
    const result = CreateBacktestRequestSchema.safeParse({
      strategy_id: "00000000-0000-0000-0000-000000000000",
      symbol: "BTC/USDT",
      timeframe: "1h",
      period_start: "2026-01-01T00:00:00Z",
      period_end: "2026-02-01T00:00:00Z",
      initial_capital: 10000,
      position_size_pct: 30,
      default_qty_type: "strategy.percent_of_equity",
      default_qty_value: 10,
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      const msg = JSON.stringify(result.error.issues);
      expect(msg).toMatch(/Live mirror|동시 명시 불가/);
    }
  });
});
