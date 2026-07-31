import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import type { StrategyResponse } from "@/features/strategy/schemas";

const updateSettingsMutate = vi.fn();

vi.mock("@/features/strategy/hooks", () => ({
  useUpdateStrategy: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateStrategySettings: () => ({
    mutate: updateSettingsMutate,
    isPending: false,
  }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { TabMetadata } from "../tab-metadata";

const strategy = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  name: "Test strategy",
  description: null,
  pine_source: "strategy('Test')",
  pine_version: "v5",
  parse_status: "ok",
  parse_errors: null,
  timeframe: "1h",
  symbol: "BTC/USDT",
  tags: [],
  trading_sessions: [],
  settings: {
    schema_version: 1,
    leverage: 2,
    margin_mode: "cross",
    position_size_pct: 10,
    max_trigger_breach_pct: 0.5,
    max_reversal_overshoot_ratio: null,
    fill_timing: "bar_close",
  },
  is_archived: false,
  created_at: "2026-07-28T00:00:00Z",
  updated_at: "2026-07-28T00:00:00Z",
} as StrategyResponse;

beforeEach(() => {
  updateSettingsMutate.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("TabMetadata trading settings", () => {
  it("상한 입력을 비우면 null 로 제출된다", async () => {
    render(<TabMetadata strategy={strategy} />);

    fireEvent.change(screen.getByLabelText("트리거 돌파 상한 (%)"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "설정 저장" }));

    await waitFor(() => {
      expect(updateSettingsMutate).toHaveBeenCalledWith(
        expect.objectContaining({ max_trigger_breach_pct: null }),
      );
    });
  });

  it("상한 숫자와 fill_timing 선택이 제출에 반영된다", async () => {
    render(<TabMetadata strategy={strategy} />);

    fireEvent.change(screen.getByLabelText("트리거 돌파 상한 (%)"), {
      target: { value: "0.25" },
    });
    fireEvent.change(screen.getByLabelText("체결 시점"), {
      target: { value: "next_bar_open" },
    });
    fireEvent.click(screen.getByRole("button", { name: "설정 저장" }));

    await waitFor(() => {
      expect(updateSettingsMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          max_trigger_breach_pct: 0.25,
          fill_timing: "next_bar_open",
        }),
      );
    });
  });
});
