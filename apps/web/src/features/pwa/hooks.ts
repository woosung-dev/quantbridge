"use client";

// 웹 푸시 벨의 상태와 동작 — 서버 설정 조회 + 이 기기의 권한·구독 + 켜기/끄기/테스트.
// 정본 = `docs/architecture/pwa.md` §2.7.
// ★권한 요청(`Notification.requestPermission`)은 **`enable` 안에서만** 한다. `enable` 은 클릭 핸들러가
//   부른다 — 페이지 진입·effect 에서 묻지 않는다(브라우저가 사용자 제스처 없는 요청을 막고, 묻는
//   순간을 사용자가 고르게 한다).

import { useEffect, useState } from "react";
import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { useAuthCtx, type TokenGetter } from "@/hooks/use-auth-ctx";
import { describeApiError } from "@/lib/api-client";
import { setBeforeSignOut } from "@/lib/before-sign-out";

import { createPushSubscription, getPushConfig, sendTestPush } from "./api";
import {
  base64UrlToBytes,
  getDeviceSubscription,
  toSubscriptionRequest,
  unsubscribeDevice,
  unsubscribeThisDevice,
} from "./push";
import { pwaKeys } from "./query-keys";
import type { PushConfig, PushTestResult } from "./schemas";

function makeConfigFetcher(getToken: TokenGetter) {
  return async () => getPushConfig(await getToken());
}

/** `GET /api/v1/push/config`. 푸시 지원이 확인된 컴포넌트에서만 부른다(미지원 = 요청 0건). */
export function usePushConfig(): UseQueryResult<PushConfig, Error> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: pwaKeys.pushConfig(uid),
    queryFn: makeConfigFetcher(getToken),
  });
}

/**
 * 로그아웃·계정 삭제 직전에 이 기기 구독을 끊도록 등록한다(§2.7).
 * 공유층 `AccountButton` 은 features 를 import 할 수 없어 `lib/before-sign-out` 을 거친다.
 * ★서버 config 와 무관하게 등록한다 — 서버가 푸시를 끈 뒤에도 기기에 옛 구독이 남아 있을 수 있다.
 */
export function useRegisterPushSignOutCleanup(): void {
  const { getToken } = useAuthCtx();
  useEffect(() => {
    setBeforeSignOut(() => unsubscribeThisDevice(getToken));
    return () => setBeforeSignOut(null);
  }, [getToken]);
}

/**
 * 이 기기 구독을 현재 사용자에게 다시 붙인다(§2.7). `enabled` = 서버 config `enabled`.
 * ★명시적 로그아웃 없이 계정이 바뀌면(세션 만료 → /sign-in → 다른 계정) `runBeforeSignOut` 이 안 돌아
 *   기기 구독은 남고 서버 행은 이전 사용자 소유로 남는다 — 새 사용자의 스위치는 「켜짐」인데 알림 0,
 *   이 브라우저는 이전 사용자의 알림을 계속 받는다. 서버 upsert 가 같은 endpoint 를 현재 사용자로
 *   재할당하므로 사용자마다 1회 POST 한다.
 * ★권한을 묻지 않는다 — 이미 granted ∧ 기기 구독이 있을 때만 움직인다. 실패는 경고만 남긴다.
 */
export function useReclaimDeviceSubscription(enabled: boolean): void {
  const { userId, getToken } = useAuthCtx();
  useEffect(() => {
    if (!enabled || !userId || Notification.permission !== "granted") return;
    let cancelled = false;
    getDeviceSubscription()
      .then(async (subscription) => {
        if (cancelled || !subscription) return;
        await createPushSubscription(toSubscriptionRequest(subscription), await getToken());
      })
      .catch((err: unknown) => {
        console.warn("[push] 이 기기 구독을 현재 사용자에게 다시 붙이지 못했습니다", err);
      });
    return () => {
      cancelled = true;
    };
  }, [enabled, userId, getToken]);
}

export interface PushDevice {
  permission: NotificationPermission;
  /** `null` = 아직 모름(구독 조회 중). */
  subscribed: boolean | null;
  pending: boolean;
  error: string | null;
  testResult: PushTestResult | null;
  enable: () => Promise<void>;
  disable: () => Promise<void>;
  sendTest: () => Promise<void>;
}

/** 이 기기의 권한·구독. 푸시 지원이 확인된 뒤에만 마운트되는 컴포넌트에서 부른다. */
export function usePushDevice(publicKey: string): PushDevice {
  const { getToken } = useAuthCtx();
  const [permission, setPermission] = useState<NotificationPermission>(
    () => Notification.permission,
  );
  const [subscribed, setSubscribed] = useState<boolean | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<PushTestResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    getDeviceSubscription().then(
      (subscription) => {
        if (!cancelled) setSubscribed(subscription !== null);
      },
      () => {
        if (!cancelled) setSubscribed(false);
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  // `task` 는 동기로 시작한다 — `enable` 의 `requestPermission` 이 클릭의 사용자 제스처 안에서 불린다.
  const run = async (task: () => Promise<void>, fallback: string) => {
    setPending(true);
    setError(null);
    setTestResult(null);
    try {
      await task();
    } catch (err) {
      setError(describeApiError(err, fallback));
    } finally {
      setPending(false);
    }
  };

  const enable = () =>
    run(async () => {
      const result = await Notification.requestPermission();
      setPermission(result);
      if (result !== "granted") return;
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: base64UrlToBytes(publicKey),
      });
      try {
        await createPushSubscription(toSubscriptionRequest(subscription), await getToken());
      } catch (err) {
        // 서버가 모르는 구독을 기기에 남기지 않는다 — 스위치가 「켜짐」인데 알림이 안 오는 상태가 된다.
        await subscription.unsubscribe();
        throw err;
      }
      setSubscribed(true);
    }, "알림을 켜지 못했습니다");

  const disable = () =>
    run(async () => {
      const subscription = await getDeviceSubscription();
      if (subscription) await unsubscribeDevice(subscription, await getToken());
      setSubscribed(false);
    }, "알림을 끄지 못했습니다");

  const sendTest = () =>
    run(async () => {
      setTestResult(await sendTestPush(await getToken()));
    }, "테스트 알림을 보내지 못했습니다");

  return { permission, subscribed, pending, error, testResult, enable, disable, sendTest };
}
