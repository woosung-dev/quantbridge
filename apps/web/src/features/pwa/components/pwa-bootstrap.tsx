"use client";

// 서비스 워커 등록 — 루트 `layout.tsx` 에 1개(pwa.md §2.6). 아무것도 그리지 않는다.
// ★앱 로드당 1회 — 모듈 레벨 가드라 StrictMode 이중 effect·라우트 이동·재마운트에도 다시 안 부른다.
// ★`load` 이후에 등록한다 — SW 스크립트 다운로드·precache 가 첫 화면의 대역폭과 겨루지 않게 한다.
// dev 에서도 등록한다(오프라인 안내·푸시를 로컬에서 재기 위해). 미지원 브라우저는 아무것도 안 한다.

import { useEffect } from "react";

let started = false;

function registerServiceWorker(): void {
  navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch((error: unknown) => {
    console.warn("[pwa] 서비스 워커 등록 실패", error);
  });
}

export function PwaBootstrap(): null {
  useEffect(() => {
    if (started || !("serviceWorker" in navigator)) return;
    started = true;
    if (document.readyState === "complete") registerServiceWorker();
    else window.addEventListener("load", registerServiceWorker, { once: true });
  }, []);
  return null;
}
