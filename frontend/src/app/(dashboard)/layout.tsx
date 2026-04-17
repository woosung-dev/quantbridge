import type { ReactNode } from "react";
import { DashboardShell } from "@/components/layout/dashboard-shell";

// 인증된 앱 페이지 공통 레이아웃 — Clerk 인증 보호(proxy.ts) + App Shell.
// DESIGN.md §11 페이지별 테마: /strategies* 는 Light, /trading 은 Dark.
// dash 테마는 이 layout에서 강제하지 않고 각 페이지(page.tsx)가 필요 시 data-theme="dash" 스코프 직접 적용.
export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[color:var(--bg)] text-[color:var(--text-primary)]">
      <DashboardShell>{children}</DashboardShell>
    </div>
  );
}
