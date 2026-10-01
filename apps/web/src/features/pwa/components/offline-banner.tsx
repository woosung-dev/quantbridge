"use client";

// 오프라인 배너 — 앱 셸 본문 맨 위(pwa.md §2.6). 연결이 끊겨도 화면은 남아 있으므로, 남은 숫자가
// 최신처럼 보이지 않게 그 사실을 말한다(데이터 캐시가 없는 대신 정직하게 알린다 — PRD §1).

import { WifiOff } from "lucide-react";

import { useIsOnline } from "../online-status";

export function OfflineBanner() {
  const online = useIsOnline();
  return online ? null : (
    <p
      role="status"
      className="flex items-center justify-center gap-2 border-b border-[color:var(--warn)]/30 bg-[color:var(--warn-soft)] px-4 py-2 text-center text-xs text-[color:var(--warn)]"
    >
      <WifiOff className="size-4 shrink-0" aria-hidden="true" />
      <span>오프라인 상태입니다. 화면의 숫자가 최신이 아닐 수 있습니다.</span>
    </p>
  );
}
