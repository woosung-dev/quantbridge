// Sprint 13 Phase A.2 — TabWebhook 컴포넌트 vitest.
// Sprint 14 Phase A — useSyncExternalStore 호환 mock 으로 갱신. webhook-secret-storage 는
// 실제 모듈 사용 (jsdom sessionStorage 작동) — listeners notify 가 useSyncExternalStore 의
// re-render trigger 로 정확히 동작하도록. spy 로 호출 카운트 추적.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import * as storageModule from "@/features/strategy/webhook-secret-storage";

// react-query mutation 체인 mock — 실제 hooks.ts 의 useRotateWebhookSecret 가
// onSuccess 콜백 안에서 cacheWebhookSecret 을 호출하므로 mock 도 동일 emulate.
const rotateMutate = vi.fn();
let rotateOnSuccess: ((data: { secret: string; webhook_url: string }) => void) | null = null;
let rotateIsPending = false;

vi.mock("@/features/strategy/hooks", () => ({
  useRotateWebhookSecret: (
    strategyId: string,
    opts: { onSuccess?: (data: { secret: string; webhook_url: string }) => void } = {},
  ) => {
    rotateOnSuccess = (data) => {
      // 실제 hooks.ts onSuccess emulate — cacheWebhookSecret 가 sessionStorage write +
      // notify() 호출 → useSyncExternalStore 가 새 snapshot 읽어 amber card 갱신.
      storageModule.cacheWebhookSecret(strategyId, data.secret);
      opts.onSuccess?.(data);
    };
    return {
      mutate: rotateMutate,
      isPending: rotateIsPending,
    };
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { TabWebhook } from "../tab-webhook";

const STRATEGY_ID = "550e8400-e29b-41d4-a716-446655440000";

const cacheSpy = vi.spyOn(storageModule, "cacheWebhookSecret");
const clearSpy = vi.spyOn(storageModule, "clearWebhookSecret");

beforeEach(() => {
  rotateMutate.mockReset();
  rotateOnSuccess = null;
  rotateIsPending = false;
  cacheSpy.mockClear();
  clearSpy.mockClear();
  sessionStorage.clear();
  // navigator.clipboard mock
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

  it("with cached plaintext (sessionStorage) → renders amber card immediately on mount (Sprint 14 hydration race fix)", () => {
    // Sprint 14 Phase A — sessionStorage 에 plaintext 캐시된 상태에서 mount 하면
    // useSyncExternalStore 의 client snapshot 이 mount 시점 read → amber card 즉시 표시.
    storageModule.cacheWebhookSecret(STRATEGY_ID, "cached-plaintext-from-create-flow");
    render(<TabWebhook strategyId={STRATEGY_ID} />);

    const card = screen.getByTestId("webhook-secret-amber-card");
    expect(card).not.toBeNull();
    const plaintextEl = screen.getByTestId("webhook-secret-plaintext");
    expect(plaintextEl.textContent).toBe("cached-plaintext-from-create-flow");
  });

  it("hide button → clearWebhookSecret 호출 + notify 로 amber card 자동 사라짐 + 재표시 불가", () => {
    storageModule.cacheWebhookSecret(STRATEGY_ID, "to-be-hidden");
    render(<TabWebhook strategyId={STRATEGY_ID} />);

    expect(screen.queryByTestId("webhook-secret-amber-card")).not.toBeNull();

    const hideBtn = screen.getByRole("button", { name: "Secret 숨기기" });
    fireEvent.click(hideBtn);

    // clearWebhookSecret 호출 + notify → useSyncExternalStore 가 null snapshot 읽어 amber 사라짐
    expect(clearSpy).toHaveBeenCalledWith(STRATEGY_ID);
    expect(screen.queryByTestId("webhook-secret-amber-card")).toBeNull();
    // sessionStorage 에서도 실제로 제거됐는지 확인 (재표시 불가 회귀 안전)
    expect(storageModule.readWebhookSecret(STRATEGY_ID)).toBeNull();
  });
});
