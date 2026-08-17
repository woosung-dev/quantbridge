// 인증된 앱 페이지 공통 레이아웃 — Clerk 인증 보호(proxy.ts) + App Shell.
// DESIGN.md §11 페이지별 테마: /strategies* 는 Light, /trading 은 Dark.
// dash 테마는 이 layout에서 강제하지 않고 각 페이지(page.tsx)가 필요 시 data-theme="dash" 스코프 직접 적용.
// Sprint 44-WC1: min-h-dvh (mobile viewport 정확) — min-h-screen 은 iOS Safari address bar 변경 시 흔들림.

// [BL-786]: 셸을 `ServerIdentityProvider` 로 감싼다 — SSR 이 이미 아는 사용자 id 를 첫 렌더에
// 주지 않으면 React Query 키가 `anon` → 진짜 id 로 흔들려 목록·배지 요청이 전부 두 번 나간다.
// `getServerAuth()` 는 `React.cache` 라 같은 요청의 페이지 호출과 왕복을 공유한다.
import type { ReactNode } from "react";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { ServerIdentityProvider } from "@/components/providers/server-identity-provider";
import { ShortcutHelpDialog } from "@/components/shortcut-help-dialog";
import { getServerAuth } from "@/lib/auth-server";
export default async function DashboardLayout({ children }: { children: ReactNode }) {
  const { userId } = await getServerAuth();
  return (
    <ServerIdentityProvider userId={userId}>
      <div className="min-h-dvh bg-[color:var(--bg)] text-[color:var(--text-primary)]">
        <DashboardShell>{children}</DashboardShell>
        <ShortcutHelpDialog />
      </div>
    </ServerIdentityProvider>
  );
}
