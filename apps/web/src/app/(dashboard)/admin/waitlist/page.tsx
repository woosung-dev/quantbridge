// Admin waitlist 페이지 (server) — 대시보드 클라이언트 로직은 WaitlistAdminView 로 위임.

import type { Metadata } from "next";

import { WaitlistAdminView } from "@/features/waitlist/components/admin/waitlist-admin-view";

// 페이지 이름 5축 일치(§4.10) — h1·<title> 모두 "Waitlist 관리"(waitlist-admin-view.tsx SSOT).
export const metadata: Metadata = {
  title: "Waitlist 관리",
};

export default function AdminWaitlistPage() {
  return <WaitlistAdminView />;
}
