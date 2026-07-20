"use client";

// 인증된 앱 페이지 공통 App Shell — 프로토타입(screen-02) 셸 구조.
// C 이식 S3: position:fixed .sidebar + margin-left .topbar/.main 모델로 재작성(구 flex 모델 대체).
//   sidebarOpen 토글 상태를 삭제했다 — 데스크톱 접힘은 순수 CSS 아이콘 레일(globals.css @media)이
//   담당하고, 셸은 스토어를 구독하지 않아 mobileNav 토글이 페이지 트리를 리렌더하지 않는다.
//   셸 = usePathname + derivePageTitle 만 보유(state composition root).

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { DashboardHeader } from "./dashboard-header";
import { DashboardSidebar } from "./dashboard-sidebar";
import { MobileNav } from "./mobile-nav";

// 페이지 타이틀 매핑 (상단바 breadcrumb). 미매핑 경로는 빈 슬롯.
const PAGE_TITLE_MAP: Record<string, string> = {
  "/dashboard": "대시보드",
  "/strategies": "전략",
  "/strategies/new": "새 전략",
  "/backtests": "백테스트",
  "/backtests/new": "새 백테스트",
  "/optimizer": "옵티마이저",
  "/trading": "트레이딩",
  "/orders": "주문 내역",
  "/onboarding": "온보딩",
};

function derivePageTitle(pathname: string | null): string {
  if (!pathname) return "";
  if (PAGE_TITLE_MAP[pathname]) return PAGE_TITLE_MAP[pathname];
  if (pathname.startsWith("/backtests/")) return "백테스트";
  if (pathname.startsWith("/strategies/")) return "전략";
  if (pathname.startsWith("/optimizer/")) return "옵티마이저";
  if (pathname.startsWith("/trading")) return "트레이딩";
  return "";
}

export function DashboardShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const pageTitle = derivePageTitle(pathname);

  return (
    <>
      {/* position:fixed — 문서 흐름 밖. .topbar/.main 이 margin-left 로 자리를 비운다. */}
      <DashboardSidebar pathname={pathname} />
      {/* 모바일 drawer — Sheet 기반 left-side, ≤768px 햄버거로 연다 (md:hidden). */}
      <MobileNav pathname={pathname} />
      <DashboardHeader pageTitle={pageTitle} />
      {/* #main-content = 스킵 링크 대상(app/layout.tsx). .main = margin-left 오프셋. */}
      <main id="main-content" className="main">
        {children}
      </main>
    </>
  );
}
