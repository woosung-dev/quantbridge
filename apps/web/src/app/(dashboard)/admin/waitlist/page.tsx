// Admin waitlist 페이지 (server) — 대시보드 클라이언트 로직은 WaitlistAdminView 로 위임.

import { WaitlistAdminView } from "./_components/waitlist-admin-view";

export default function AdminWaitlistPage() {
  return <WaitlistAdminView />;
}
