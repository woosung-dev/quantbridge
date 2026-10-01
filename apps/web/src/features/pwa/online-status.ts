"use client";

// 네트워크 연결 상태 — `online`/`offline` **모듈 단일 구독** + `useSyncExternalStore`(pwa.md §2.6).
// ★`features/realtime/ws-client.ts` 의 `online` 리스너는 WS 재연결용으로 따로 있다 — 건드리지 않는다.
// 스냅샷은 매번 `navigator.onLine` 을 읽으므로 첫 구독 전에 지나간 이벤트를 놓쳐도 값은 맞다.

import { useSyncExternalStore } from "react";

const listeners = new Set<() => void>();
let attached = false;

function emit(): void {
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  if (!attached) {
    attached = true;
    window.addEventListener("online", emit);
    window.addEventListener("offline", emit);
  }
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function onlineSnapshot(): boolean {
  return navigator.onLine;
}

/** SSR·하이드레이션 첫 렌더는 「연결됨」으로 본다(배너 미표시) — 그다음 실제 값으로 맞춘다. */
export function useIsOnline(): boolean {
  return useSyncExternalStore(subscribe, onlineSnapshot, () => true);
}
