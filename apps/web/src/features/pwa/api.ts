// 웹 푸시 API 호출을 한곳에 모은다 (`docs/architecture/pwa.md` §3.2 — 전부 인증 필수).
import { apiFetch } from "@/lib/api-client";

import {
  PushConfigSchema,
  PushSubscriptionSchema,
  PushTestResultSchema,
  type CreatePushSubscriptionRequest,
  type PushConfig,
  type PushSubscriptionRecord,
  type PushTestResult,
} from "./schemas";

const PUSH_PATH = "/api/v1/push";

export async function getPushConfig(token: string | null): Promise<PushConfig> {
  const raw = await apiFetch<unknown>(`${PUSH_PATH}/config`, { method: "GET", token });
  return PushConfigSchema.parse(raw);
}

export async function createPushSubscription(
  request: CreatePushSubscriptionRequest,
  token: string | null,
): Promise<PushSubscriptionRecord> {
  const raw = await apiFetch<unknown>(`${PUSH_PATH}/subscriptions`, {
    method: "POST",
    token,
    body: request,
  });
  return PushSubscriptionSchema.parse(raw);
}

/** 204. 남의 endpoint · 없는 endpoint 는 404 다(서버가 존재 여부를 흘리지 않는다). */
export async function deletePushSubscription(
  endpoint: string,
  token: string | null,
): Promise<void> {
  await apiFetch<void>(`${PUSH_PATH}/subscriptions`, {
    method: "DELETE",
    token,
    body: { endpoint },
  });
}

/** 내 구독 전부에 테스트 알림. 서버 푸시가 꺼져 있으면 409. */
export async function sendTestPush(token: string | null): Promise<PushTestResult> {
  const raw = await apiFetch<unknown>(`${PUSH_PATH}/test`, { method: "POST", token });
  return PushTestResultSchema.parse(raw);
}
