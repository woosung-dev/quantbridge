// Sprint 13 Phase A.2 — TabWebhook 컴포넌트 vitest.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

// react-query mutation 체인 mock — 실제 hooks.ts 의 useRotateWebhookSecret 가
// onSuccess 콜백을 호출해서 cacheWebhookSecret + setState 한다.
const rotateMutate = vi.fn();
let rotateOnSuccess: ((data: { secret: string; webhook_url: string }) => void) | null = null;
let rotateIsPending = false;

vi.mock("@/features/strategy/hooks", () => ({
  useRotateWebhookSecret: (
    _strategyId: string,
    opts: { onSuccess?: (data: { secret: string; webhook_url: string }) => void } = {},
  ) => {
    rotateOnSuccess = opts.onSuccess ?? null;
    return {
      mutate: rotateMutate,
      isPending: rotateIsPending,
    };
  },
}));

const cacheCalls: { strategyId: string; plaintext: string }[] = [];
const clearCalls: string[] = [];

vi.mock("@/features/strategy/webhook-secret-storage", () => ({
  cacheWebhookSecret: (strategyId: string, plaintext: string) => {
    cacheCalls.push({ strategyId, plaintext });
  },
  readWebhookSecret: (strategyId: string) => readSecretMock(strategyId),
  clearWebhookSecret: (strategyId: string) => {
    clearCalls.push(strategyId);
  },
}));

let _readReturn: string | null = null;
function readSecretMock(_strategyId: string): string | null {
  return _readReturn;
}

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { TabWebhook } from "../tab-webhook";

const STRATEGY_ID = "550e8400-e29b-41d4-a716-446655440000";

beforeEach(() => {
  rotateMutate.mockReset();
  rotateOnSuccess = null;
  rotateIsPending = false;
  cacheCalls.length = 0;
  clearCalls.length = 0;
  _readReturn = null;
  // navigator.clipboard mock
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    writable: true,
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
  });
});

afterEach(() => {
  cleanup();
});

describe("TabWebhook", () => {
  it("renders webhook URL with strategyId + clipboard copy", async () => {
    render(<TabWebhook strategyId={STRATEGY_ID} />);
    const url = screen.getByText(/\/api\/v1\/webhooks\//);
    expect(url.textContent).toContain(STRATEGY_ID);
    expect(url.textContent).toContain("{HMAC}");

    const copyBtn = screen.getByRole("button", { name: "URL 복사" });
    fireEvent.click(copyBtn);
    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining(STRATEGY_ID),
      );
    });
  });

  it("rotate button → ConfirmDialog → mutate → amber card with plaintext + sessionStorage cached", async () => {
    render(<TabWebhook strategyId={STRATEGY_ID} />);

    // 초기 상태: amber card 없음
    expect(screen.queryByTestId("webhook-secret-amber-card")).toBeNull();

    // Rotate 버튼 클릭 → ConfirmDialog 열림
    fireEvent.click(screen.getByRole("button", { name: "webhook secret 회전" }));
    const confirmBtn = await screen.findByRole("button", { name: "rotate 확정" });

    // 확정 클릭 → mutate 호출
    fireEvent.click(confirmBtn);
    expect(rotateMutate).toHaveBeenCalledTimes(1);

    // mutation onSuccess 시뮬 — hooks.ts 의 onSuccess 가 cacheWebhookSecret 호출 후 opts.onSuccess
    // 본 테스트는 컴포넌트 onSuccess 만 검증 (cache 는 hooks.ts 책임). 컴포넌트 onSuccess 가
    // setDisplayedSecret 호출하면 amber card 렌더.
    expect(rotateOnSuccess).not.toBeNull();
    rotateOnSuccess!({
      secret: "new-plaintext-abc-32chars-or-more",
      webhook_url: "/api/v1/webhooks/...",
    });

    // amber card + plaintext 표시
    const card = await screen.findByTestId("webhook-secret-amber-card");
    expect(card).not.toBeNull();
    const plaintextEl = await screen.findByTestId("webhook-secret-plaintext");
    expect(plaintextEl.textContent).toBe("new-plaintext-abc-32chars-or-more");
  });

  it("with cached plaintext (sessionStorage) → renders amber card immediately on mount", () => {
    _readReturn = "cached-plaintext-from-create-flow";
    render(<TabWebhook strategyId={STRATEGY_ID} />);

    const card = screen.getByTestId("webhook-secret-amber-card");
    expect(card).not.toBeNull();
    const plaintextEl = screen.getByTestId("webhook-secret-plaintext");
    expect(plaintextEl.textContent).toBe("cached-plaintext-from-create-flow");
  });

  it("hide button → clearWebhookSecret 호출 + amber card 사라짐 + 재표시 불가", () => {
    _readReturn = "to-be-hidden";
    render(<TabWebhook strategyId={STRATEGY_ID} />);

    expect(screen.queryByTestId("webhook-secret-amber-card")).not.toBeNull();

    const hideBtn = screen.getByRole("button", { name: "Secret 숨기기" });
    fireEvent.click(hideBtn);

    // clearWebhookSecret 호출 + amber card 사라짐
    expect(clearCalls).toEqual([STRATEGY_ID]);
    expect(screen.queryByTestId("webhook-secret-amber-card")).toBeNull();
  });
});
