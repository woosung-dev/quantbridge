"use client";

// 인증된 앱 페이지 공통 App Shell — Sidebar(220px) + Header(64px) + 콘텐츠.
// Sprint 41-B2: 프로토타입 06/09/02/03 visual layout 정합 (sidebar w-[220px], 페이지 타이틀 slot).
// Sprint 42-polish-3 (2026-05-08): 화이트 모드 통일 — /trading 의 Full Dark scope 제거 (사용자 결정).
// Sprint 44-WC1 (2026-05-08): App Shell sidebar/header inline polish — DESIGN.md §10.2 active 스타일 정합.
// Sprint 45 (2026-05-09): 4 컴포넌트 분리 — DashboardSidebar / DashboardHeader / DashboardNavList.
//   Shell 은 useUiStore + usePathname + derivePageTitle 만 보유 (state composition root).

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { useUiStore } from "@/store/ui-store";

import { DashboardHeader } from "./dashboard-header";
import { DashboardSidebar } from "./dashboard-sidebar";
import { MobileNav } from "./mobile-nav";

// 페이지 타이틀 매핑 (헤더 slot). 없는 경로는 빈 문자열 — 헤더 좌측이 비어 보이지 않도록
// fallback="QuantBridge" 적용은 prefer X (시각적 노이즈). 미매핑 경로는 그냥 빈 슬롯.
const PAGE_TITLE_MAP: Record<string, string> = {
  "/strategies": "전략",
  "/strategies/new": "새 전략",
  "/backtests": "백테스트",
  "/backtests/new": "새 백테스트",
  "/trading": "트레이딩",
  "/onboarding": "온보딩",
};

function derivePageTitle(pathname: string | null): string {
  if (!pathname) return "";
  // exact match 우선
  if (PAGE_TITLE_MAP[pathname]) return PAGE_TITLE_MAP[pathname];
  // /backtests/[id], /strategies/[id]/edit 등 prefix
  if (pathname.startsWith("/backtests/")) return "백테스트";
  if (pathname.startsWith("/strategies/")) return "전략";
  if (pathname.startsWith("/trading")) return "트레이딩";
  return "";
}

export function DashboardShell({ children }: { children: ReactNode }) {
  const { sidebarOpen, toggleSidebar } = useUiStore();
  const pathname = usePathname();
  const pageTitle = derivePageTitle(pathname);

  return (
    <div className="flex min-h-dvh bg-[color:var(--background)] text-[color:var(--foreground)]">
      <DashboardSidebar sidebarOpen={sidebarOpen} pathname={pathname} />
      {/* Sprint 60 S4 (BL-285/300): 모바일 drawer — Sheet 기반 left-side, mobile-only (md:hidden) */}
      <MobileNav pathname={pathname} />
      <div className="flex flex-1 flex-col">
        <DashboardHeader
          sidebarOpen={sidebarOpen}
          onToggleSidebar={toggleSidebar}
          pageTitle={pageTitle}
        />
        <main id="main-content" className="flex-1">
          {children}
        </main>
      </div>
    </div>
  );
}
