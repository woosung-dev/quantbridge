// 오프라인 안내 라우트 — 서비스 워커가 설치 시 precache 하는 정적 화면(docs/architecture/pwa.md §2.4).
// 공개 라우트다(`proxy.ts` isPublicRoute) — 인증을 걸면 precache 가 로그인 화면을 저장한다.
import type { Metadata } from "next";

import { OfflineView } from "@/features/pwa/components/offline-view";

export const metadata: Metadata = {
  title: "오프라인",
};

export default function OfflinePage() {
  return <OfflineView />;
}
