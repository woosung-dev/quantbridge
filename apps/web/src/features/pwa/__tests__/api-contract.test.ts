// 웹 푸시 REST 래퍼의 경로·메서드·본문·응답 파싱 계약 (pwa.md §3.2).
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import {
  createPushSubscription,
  deletePushSubscription,
  getPushConfig,
  sendTestPush,
} from "../api";

const ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc";

afterEach(() => {
  apiFetchMock.mockReset();
});

describe("push API contract", () => {
  it("config 는 인증 GET 이고 비활성 응답(public_key null)을 그대로 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ enabled: false, public_key: null });

    await expect(getPushConfig("jwt")).resolves.toEqual({ enabled: false, public_key: null });
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/push/config", {
      method: "GET",
      token: "jwt",
    });
  });

  it("config 응답에 enabled 가 없으면 throw 한다 — 벨을 추측으로 그리지 않는다", async () => {
    apiFetchMock.mockResolvedValueOnce({ public_key: "key" });

    await expect(getPushConfig("jwt")).rejects.toThrow();
  });

  it("구독 등록은 subscription.toJSON() + user_agent 를 POST 하고 {id, endpoint, created_at} 을 파싱한다", async () => {
    const body = { endpoint: ENDPOINT, keys: { p256dh: "p", auth: "a" }, user_agent: "UA" };
    const record = {
      id: "00000000-0000-4000-a000-000000000001",
      endpoint: ENDPOINT,
      created_at: "2026-10-02T00:00:00+00:00",
    };
    apiFetchMock.mockResolvedValueOnce(record);

    await expect(createPushSubscription(body, "jwt")).resolves.toEqual(record);
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/push/subscriptions", {
      method: "POST",
      token: "jwt",
      body,
    });
  });

  it("구독 해제는 DELETE 본문에 endpoint 하나만 싣는다", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);

    await expect(deletePushSubscription(ENDPOINT, "jwt")).resolves.toBeUndefined();
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/push/subscriptions", {
      method: "DELETE",
      token: "jwt",
      body: { endpoint: ENDPOINT },
    });
  });

  it("테스트 발송은 본문 없는 POST 이고 {sent, removed} 를 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ sent: 2, removed: 1 });

    await expect(sendTestPush("jwt")).resolves.toEqual({ sent: 2, removed: 1 });
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/push/test", {
      method: "POST",
      token: "jwt",
    });
  });
});
