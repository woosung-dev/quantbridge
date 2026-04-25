// Sprint 11 Phase C: waitlist api + schema + query-keys 검증.

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import {
  AdminApproveResponseSchema,
  CreateWaitlistApplicationSchema,
  WaitlistApplicationAcceptedResponseSchema,
} from "../schemas";
import { waitlistKeys } from "../query-keys";

describe("CreateWaitlistApplicationSchema", () => {
  it("accepts valid form body", () => {
    const parsed = CreateWaitlistApplicationSchema.parse({
      email: "alice@example.com",
      tv_subscription: "pro_plus",
      exchange_capital: "1k_to_10k",
      pine_experience: "beginner",
      existing_tool: null,
      pain_point: "Manual copy-paste of alerts is painful.",
    });
    expect(parsed.email).toBe("alice@example.com");
    expect(parsed.tv_subscription).toBe("pro_plus");
  });

  it("rejects pain_point shorter than 3 chars", () => {
    expect(() =>
      CreateWaitlistApplicationSchema.parse({
        email: "a@b.com",
        tv_subscription: "pro",
        exchange_capital: "under_1k",
        pine_experience: "none",
        pain_point: "hi",
      }),
    ).toThrow();
  });

  it("rejects non-pro TradingView subscription (free)", () => {
    expect(() =>
      CreateWaitlistApplicationSchema.parse({
        email: "a@b.com",
        tv_subscription: "free" as unknown as "pro",
        exchange_capital: "under_1k",
        pine_experience: "none",
        pain_point: "Need automation for my strategy.",
      }),
    ).toThrow();
  });
});

describe("waitlistKeys", () => {
  it("different userId produces different admin list keys", () => {
    const a = waitlistKeys.adminList("user_a", { status: "pending" });
    const b = waitlistKeys.adminList("user_b", { status: "pending" });
    expect(a).not.toEqual(b);
  });

  it("admin list key includes 'admin' discriminator", () => {
    const key = waitlistKeys.adminList("user_x", { status: "invited" });
    expect(key).toEqual([
      "waitlist",
      "user_x",
      "admin",
      "list",
      { status: "invited" },
    ]);
  });
});

describe("submitWaitlist api", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts parsed payload to /api/v1/waitlist and validates response", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(
          JSON.stringify({
            id: "11111111-1111-4111-8111-111111111111",
            status: "pending",
          }),
          {
            status: 202,
            headers: { "content-type": "application/json" },
          },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { submitWaitlist } = await import("../api");
    const result = await submitWaitlist({
      email: "alice@example.com",
      tv_subscription: "pro_plus",
      exchange_capital: "1k_to_10k",
      pine_experience: "intermediate",
      pain_point: "Need unified backtest/live parity.",
    });

    // schema round-trip 검증
    expect(() =>
      WaitlistApplicationAcceptedResponseSchema.parse(result),
    ).not.toThrow();
    expect(result.status).toBe("pending");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const firstCall = fetchMock.mock.calls[0];
    expect(firstCall).toBeDefined();
    if (firstCall) {
      const [url, init] = firstCall;
      expect(String(url)).toContain("/api/v1/waitlist");
      expect((init as RequestInit).method).toBe("POST");
    }
  });
});

describe("AdminApproveResponseSchema", () => {
  it("parses invited response with ISO datetime", () => {
    const parsed = AdminApproveResponseSchema.parse({
      id: "22222222-2222-4222-8222-222222222222",
      status: "invited",
      email: "alice@example.com",
      invite_sent_at: "2026-04-25T12:00:00+00:00",
    });
    expect(parsed.status).toBe("invited");
  });
});
