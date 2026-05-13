// 인증된 앱 페이지 사이드바 — 로고 + nav + footer dock(UserButton).
// Sprint 45: dashboard-shell.tsx 에서 분리. props 로 sidebarOpen, pathname 받음.
// Sprint 41-B2 sidebar 220px (collapsed 64px, 모바일 hidden) + Sprint 44-WC1 logo opacity transition 보존.

import Link from "next/link";
import { UserButton } from "@clerk/nextjs";

import { cn } from "@/lib/utils";

import { DashboardNavList } from "./dashboard-nav-list";

type DashboardSidebarProps = {
  sidebarOpen: boolean;
  pathname: string | null;
};

export function DashboardSidebar({ sidebarOpen, pathname }: DashboardSidebarProps) {
  return (
    <aside
      className={cn(
        "hidden flex-col border-r border-[color:var(--sidebar-border)] bg-[color:var(--sidebar)] text-[color:var(--sidebar-foreground)] md:flex",
        // 프로토타입 06/09/02/03 fixed sidebar 220px (collapsed 64px, 모바일 hidden)
        sidebarOpen ? "w-[220px]" : "w-16",
      )}
    >
      {/* 로고 — Plus Jakarta Sans 볼드 + primary-gradient 마크.
          Sprint 44-WC1 polish: opacity transition 150ms + motion-reduce. */}
      <Link
        href="/strategies"
        className={cn(
          "flex h-16 items-center gap-2.5 px-4 hover:opacity-90",
          "transition-opacity duration-150 motion-reduce:transition-none",
        )}
        aria-label="QuantBridge 홈"
      >
        <span className="grid size-7 place-items-center rounded-md bg-gradient-to-br from-[color:var(--primary)] to-[color:var(--primary-hover)] text-white shadow-sm">
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M2 16h20" />
            <path d="M5 16V9" />
            <path d="M19 16V9" />
            <path d="M5 9c2 0 4-2 7-2s5 2 7 2" />
            <path d="M9 16v4" />
            <path d="M15 16v4" />
          </svg>
        </span>
        {sidebarOpen && (
          <span className="font-display text-base font-bold tracking-tight">QuantBridge</span>
        )}
      </Link>

      <DashboardNavList sidebarOpen={sidebarOpen} pathname={pathname} />

      {/* 사이드바 footer — 프로필 dock (UserButton). 프로토타입 06/03 sidebar-bottom 패턴.
          Sprint 60 S4 BL-305: min 36×36 wrapper 로 Clerk inner span collapse 방지 (mobile header 와 동일 패턴). */}
      <div className="mt-auto border-t border-[color:var(--sidebar-border)] px-3 py-3">
        <div
          className={cn(
            "flex items-center gap-2",
            sidebarOpen ? "justify-start" : "justify-center",
          )}
        >
          <div className="inline-flex min-h-9 min-w-9 items-center justify-center">
            {/* G.3-2 (P1): wrapper 만으로는 hit target 0×0 가능, Clerk elements size-9 강제 */}
            <UserButton
              appearance={{
                elements: {
                  rootBox: "shrink-0 size-9",
                  userButtonTrigger: "size-9",
                  avatarBox: "size-9",
                },
              }}
            />
          </div>
          {sidebarOpen && (
            <span className="text-xs text-[color:var(--muted-foreground)] truncate">계정</span>
          )}
        </div>
      </div>
    </aside>
  );
}
