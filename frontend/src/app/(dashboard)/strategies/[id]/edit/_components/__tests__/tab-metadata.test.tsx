import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import type { StrategyResponse } from "@/features/strategy/schemas";

const updateSettingsMutate = vi.fn();
const toastError = vi.fn();

vi.mock("@/features/strategy/hooks", () => ({
  useUpdateStrategy: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateStrategySettings: () => ({
    mutate: updateSettingsMutate,
    isPending: false,
  }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: (...args: unknown[]) => toastError(...args) },
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

// ★BL-570 — 원장이 실제로 주는 형태. 기존 픽스처는 `max_trigger_breach_pct: 0.5`(non-null)라
//   nullable 필드가 만든 결함을 구조적으로 못 봤다 (외부 시스템 픽스처는 그 시스템이 실제로
//   주는 형태여야 한다). `public.strategies` 실측: cap · overshoot 둘 다 null.
const strategyWithNullCaps = {
  ...strategy,
  settings: {
    ...strategy.settings!,
    margin_mode: "isolated",
    position_size_pct: 1,
    max_trigger_breach_pct: null,
    max_reversal_overshoot_ratio: null,
  },
} as StrategyResponse;

beforeEach(() => {
  updateSettingsMutate.mockReset();
  toastError.mockReset();
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

// BL-570 — 「조용히 죽지 않는다」 층. 뿌리(RHF 가 defaultValue 를 setValueAs 에 넘겨
// `Number(null) === 0` 이 되는 것)는 **jsdom 에서 재현되지 않으므로** 여기서 잠글 수 없다 —
// 그 몫은 `e2e/authed-settings-save.spec.ts` 다. 여기서는 피드백 층만 잠근다.
describe("BL-570 검증 탈락이 침묵하지 않는다", () => {
  it("상한이 0 이면 저장이 막히고 토스트와 필드 에러가 함께 뜬다", async () => {
    render(<TabMetadata strategy={strategyWithNullCaps} />);

    // `min={0}` 이라 브라우저 네이티브 검증은 통과하고 zod `.gt(0)` 만 거부하는 입력.
    fireEvent.change(screen.getByLabelText("트리거 돌파 상한 (%)"), {
      target: { value: "0" },
    });
    fireEvent.click(screen.getByRole("button", { name: /설정 저장|설정 등록/ }));

    await waitFor(() => {
      expect(toastError).toHaveBeenCalledWith(
        "저장하지 못했습니다: 입력값을 확인해 주세요",
      );
    });
    expect(updateSettingsMutate).not.toHaveBeenCalled();
    expect(document.querySelectorAll(".field-error").length).toBeGreaterThan(0);
  });

  it("원장 형태(cap null)에서 다른 필드만 고쳐도 cap 은 null 로 제출된다", async () => {
    render(<TabMetadata strategy={strategyWithNullCaps} />);

    fireEvent.change(screen.getByLabelText("레버리지 (1 ~ 125)"), {
      target: { value: "3" },
    });
    fireEvent.click(screen.getByRole("button", { name: /설정 저장|설정 등록/ }));

    await waitFor(() => {
      expect(updateSettingsMutate).toHaveBeenCalledWith(
        expect.objectContaining({ leverage: 3, max_trigger_breach_pct: null }),
      );
    });
  });
});
