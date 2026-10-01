// 브라우저 Push API 접착층 — 지원 판정 · 이 기기 구독 조회 · 구독 해제(+서버 행 삭제).
// 정본 = `docs/architecture/pwa.md` §2.7. 컴포넌트는 이 파일을 직접 부르지 않고 `hooks.ts` 를 쓴다
// (예외: 로그아웃 정리는 `lib/before-sign-out.ts` 로 등록된다).

import type { TokenGetter } from "@/hooks/use-auth-ctx";
import { ApiError } from "@/lib/api-client";

import { deletePushSubscription } from "./api";
import { CreatePushSubscriptionRequestSchema, type CreatePushSubscriptionRequest } from "./schemas";

/** 서비스 워커 ∧ PushManager ∧ Notification — 셋 중 하나라도 없으면 벨을 그리지 않는다. */
export function isPushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

/** 이 기기의 현재 구독. SW 가 아직 등록되지 않았으면 구독도 있을 수 없다 → null. */
export async function getDeviceSubscription(): Promise<PushSubscription | null> {
  const registration = await navigator.serviceWorker.getRegistration("/");
  return (await registration?.pushManager.getSubscription()) ?? null;
}

/** VAPID 공개 키(base64url) → `applicationServerKey` 바이트. 문자열을 못 받는 브라우저가 있다. */
export function base64UrlToBytes(value: string): Uint8Array<ArrayBuffer> {
  const padded = value + "=".repeat((4 - (value.length % 4)) % 4);
  const binary = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

/** 서버 등록 본문 — 브라우저 `toJSON()` 의 키가 선택 필드라 스키마로 좁힌다. */
export function toSubscriptionRequest(
  subscription: PushSubscription,
): CreatePushSubscriptionRequest {
  const json = subscription.toJSON();
  return CreatePushSubscriptionRequestSchema.parse({
    endpoint: json.endpoint ?? subscription.endpoint,
    keys: json.keys,
    user_agent: navigator.userAgent.slice(0, 512),
  });
}

/** 구독을 끊고 서버 행도 지운다. 서버 404 = 이미 없음(다른 사용자로 재할당 등)이라 성공으로 친다. */
export async function unsubscribeDevice(
  subscription: PushSubscription,
  token: string | null,
): Promise<void> {
  await subscription.unsubscribe();
  try {
    await deletePushSubscription(subscription.endpoint, token);
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) throw error;
  }
}

/** 로그아웃·계정 삭제 직전 정리(§2.7) — 이 기기에 구독이 없으면 아무것도 하지 않는다. */
export async function unsubscribeThisDevice(getToken: TokenGetter): Promise<void> {
  if (!isPushSupported()) return;
  const subscription = await getDeviceSubscription();
  if (!subscription) return;
  await unsubscribeDevice(subscription, await getToken());
}
