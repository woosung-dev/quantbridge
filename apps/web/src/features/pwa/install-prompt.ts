"use client";

// `beforeinstallprompt` 보관소 — **모듈 단일 구독** + `useSyncExternalStore`(pwa.md §2.6).
// 설치 버튼이 몇 개 마운트되든 window 리스너는 한 쌍이다(구독자는 Set 으로 늘어난다).
// ★리스너를 첫 마운트까지 미루지 않고 모듈 평가 시점에 붙인다 — Chromium 은 이 이벤트를 페이지
//   로드 뒤 **한 번만** 쏘고, 무거운 화면은 하이드레이션 커밋이 그보다 늦을 수 있다(놓치면 그
//   페이지 로드 동안 설치 버튼이 영영 안 뜬다).
// ★비표준(Chromium 전용)이다 — Safari·Firefox 에서는 이벤트가 오지 않아 버튼이 안 그려진다.

import { useSyncExternalStore } from "react";

/** lib.dom 에 없는 Chromium 이벤트 타입 — 쓰는 멤버만 적는다. */
interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<unknown>;
}

let deferred: BeforeInstallPromptEvent | null = null;
const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (event) => {
    // 브라우저 기본 설치 안내 대신 상단바 버튼으로 연다.
    event.preventDefault();
    deferred = event as BeforeInstallPromptEvent;
    emit();
  });
  window.addEventListener("appinstalled", () => {
    deferred = null;
    emit();
  });
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function isStandalone(): boolean {
  return (
    typeof window.matchMedia === "function" &&
    window.matchMedia("(display-mode: standalone)").matches
  );
}

function canInstallSnapshot(): boolean {
  return deferred !== null && !isStandalone();
}

/** 설치 프롬프트를 띄울 수 있는가 — 이벤트 보유 ∧ 이미 설치된 창(standalone)이 아님. */
export function useCanInstall(): boolean {
  return useSyncExternalStore(subscribe, canInstallSnapshot, () => false);
}

/** 클릭 핸들러에서만 부른다. 결과(수락·거절)와 무관하게 이벤트를 폐기한다 — `prompt()` 는 1회용이다. */
export function promptInstall(): void {
  const event = deferred;
  if (!event) return;
  deferred = null;
  emit();
  event.prompt().catch((error: unknown) => {
    console.warn("[pwa] 설치 프롬프트 실패", error);
  });
}
