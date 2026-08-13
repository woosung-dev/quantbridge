// Webhook 탭 컴포넌트 vitest — W3-B 삭제분 재작성. 현행 셀렉터로 핵심 4행동을 검증한다
// (URL 복사 · secret 회전 · sessionStorage 캐시 표시 · 숨김). 저장소는 실제 모듈을 써서
// useSyncExternalStore 의 notify 가 실제 re-render 를 트리거하도록 한다.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import {
  cacheWebhookSecret,
  readWebhookSecret,
} from "@/features/strategy/webhook-secret-storage";

// react-query mutation 체인 mock — 실제 useRotateWebhookSecret 는 onSuccess 안에서
// cacheWebhookSecret 을 호출하므로, 회전 성공은 테스트에서 그 순서를 그대로 재현한다.
const mockRotateMutate = vi.fn();
let mockCapturedOpts: {
  onSuccess?: (data: { secret: string; webhook_url: string }) => void;
} = {};

vi.mock("@/features/strategy/hooks", () => ({
  useRotateWebhookSecret: (
    _strategyId: string,
    opts: { onSuccess?: (data: { secret: string; webhook_url: string }) => void } = {},
  ) => {
    mockCapturedOpts = opts;
    return { mutate: mockRotateMutate, isPending: false };
  },
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { TabWebhook } from "../tab-webhook";

const STRATEGY_ID = "550e8400-e29b-41d4-a716-446655440000";

beforeEach(() => {
  mockRotateMutate.mockReset();
  mockCapturedOpts = {};
  sessionStorage.clear();
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    writable: true,
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
  });
});

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

describe("TabWebhook", () => {
  it("Webhook URL 을 strategyId·{HMAC} 와 함께 렌더하고 URL 복사 버튼이 클립보드에 쓴다", async () => {
    render(<TabWebhook strategyId={STRATEGY_ID} />);
    const url = screen.getByText(/\/api\/v1\/webhooks\//);
    expect(url.textContent).toContain(STRATEGY_ID);
    expect(url.textContent).toContain("{HMAC}");

    fireEvent.click(screen.getByRole("button", { name: "URL 복사" }));
    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining(STRATEGY_ID),
      );
    });
  });

  it("Secret 회전: 회전 버튼 → 확인 다이얼로그 → 확정이 mutate 호출, 성공 시 1회성 secret 카드 노출", async () => {
    render(<TabWebhook strategyId={STRATEGY_ID} />);
    expect(screen.queryByTestId("webhook-secret-amber-card")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "webhook secret 회전" }));
    const confirmBtn = await screen.findByRole("button", { name: "회전 확정" });
    fireEvent.click(confirmBtn);
    expect(mockRotateMutate).toHaveBeenCalledTimes(1);

    // 실제 hooks.ts onSuccess 재현: cacheWebhookSecret(sessionStorage write + notify) 후 opts.onSuccess.
    act(() => {
      cacheWebhookSecret(STRATEGY_ID, "new-plaintext-abc-32chars-or-more");
      mockCapturedOpts.onSuccess?.({
        secret: "new-plaintext-abc-32chars-or-more",
        webhook_url: "/api/v1/webhooks/x",
      });
    });

    const card = await screen.findByTestId("webhook-secret-amber-card");
    expect(card).not.toBeNull();
    expect(screen.getByTestId("webhook-secret-plaintext").textContent).toBe(
      "new-plaintext-abc-32chars-or-more",
    );
  });

  it("sessionStorage 에 캐시된 plaintext 가 있으면 마운트 즉시 secret 카드를 표시한다", () => {
    cacheWebhookSecret(STRATEGY_ID, "cached-plaintext-from-create-flow");
    render(<TabWebhook strategyId={STRATEGY_ID} />);

    expect(screen.getByTestId("webhook-secret-amber-card")).not.toBeNull();
    expect(screen.getByTestId("webhook-secret-plaintext").textContent).toBe(
      "cached-plaintext-from-create-flow",
    );
  });

  it("숨기기: 카드가 사라지고 sessionStorage 에서 제거되어 재표시 불가", () => {
    cacheWebhookSecret(STRATEGY_ID, "to-be-hidden");
    render(<TabWebhook strategyId={STRATEGY_ID} />);
    expect(screen.queryByTestId("webhook-secret-amber-card")).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Secret 숨기기" }));

    expect(screen.queryByTestId("webhook-secret-amber-card")).toBeNull();
    expect(readWebhookSecret(STRATEGY_ID)).toBeNull();
  });
});
