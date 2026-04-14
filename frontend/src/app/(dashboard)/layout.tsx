import type { ReactNode } from "react";
import { DashboardShell } from "@/components/layout/dashboard-shell";

// 대시보드 레이아웃 — DESIGN.md Dark Theme 스코프 적용 + Clerk 인증 보호(proxy.ts)
export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div data-theme="dash" className="min-h-screen bg-[color:var(--bg)] text-[color:var(--text-primary)]">
      <DashboardShell>{children}</DashboardShell>
    </div>
  );
}
