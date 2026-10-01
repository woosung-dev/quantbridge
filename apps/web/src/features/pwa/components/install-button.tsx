"use client";

// 상단바 「앱 설치」 버튼 — Chromium 의 `beforeinstallprompt` 를 보유했을 때만 그린다(pwa.md §2.6).
// 이미 설치된 창(display-mode: standalone)·`appinstalled` 뒤·Safari/Firefox 에서는 그리지 않는다.

import { MonitorDown } from "lucide-react";

import { promptInstall, useCanInstall } from "../install-prompt";

export function InstallButton() {
  const canInstall = useCanInstall();
  return canInstall ? (
    <button
      type="button"
      onClick={promptInstall}
      aria-label="앱 설치"
      title="앱 설치"
      className="inline-flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <MonitorDown className="h-5 w-5" aria-hidden="true" />
    </button>
  ) : null;
}
