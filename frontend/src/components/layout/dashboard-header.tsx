// 인증된 앱 페이지 헤더 — 모바일 햄버거 + 페이지 타이틀 slot + 모바일 UserButton.
// Sprint 45: dashboard-shell.tsx 에서 분리. pageTitle / onToggleSidebar 는 부모(Shell)에서 prop 주입.
// Sprint 44-WC1 polish: hamburger Menu lucide + 44×44 hit area + bg-alt hover transition 150ms 보존.

import { UserButton } from "@clerk/nextjs";
import { Menu as MenuIcon } from "lucide-react";

import { cn } from "@/lib/utils";

type DashboardHeaderProps = {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  pageTitle: string;
};

export function DashboardHeader({ sidebarOpen, onToggleSidebar, pageTitle }: DashboardHeaderProps) {
  return (
    <header className="sticky top-0 z-[100] flex h-16 items-center gap-3 border-b border-[color:var(--border)] bg-[color:var(--card)] px-4 backdrop-blur md:px-6">
      {/* Sprint 44-WC1 polish: mobile hamburger — Menu lucide icon + 44×44 hit area
          + bg-alt hover transition 150ms (DESIGN.md §10.3 Left 1 정합). */}
      <button
        type="button"
        onClick={onToggleSidebar}
        aria-label="메뉴 열기"
        aria-expanded={sidebarOpen}
        className={cn(
          "grid size-11 place-items-center rounded-md text-[color:var(--muted-foreground)]",
          "transition-[background-color,color] duration-150 ease-[cubic-bezier(0.4,0,0.2,1)]",
          "motion-reduce:transition-none",
          "hover:bg-[color:var(--sidebar-accent)] hover:text-[color:var(--foreground)]",
          "md:hidden",
        )}
      >
        <MenuIcon className="size-5" aria-hidden="true" />
      </button>
      {/* 페이지 타이틀 slot — 프로토타입 06/09/02/03 헤더 좌측 패턴.
          usePathname() 기반 (effect 없음). */}
      {pageTitle && (
        <h2 className="font-display text-base font-semibold tracking-tight text-[color:var(--foreground)]">
          {pageTitle}
        </h2>
      )}
      <div className="ml-auto flex items-center gap-3">
        {/* 데스크톱에서는 사이드바 footer 의 UserButton 으로 대체. 모바일은 sidebar 가 hidden 이므로 헤더 우측에도 노출. */}
        <div className="md:hidden">
          <UserButton />
        </div>
      </div>
    </header>
  );
}
