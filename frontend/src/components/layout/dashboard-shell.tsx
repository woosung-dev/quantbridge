"use client";

import type { ReactNode } from "react";
import { UserButton } from "@clerk/nextjs";
import { useUiStore } from "@/store/ui-store";
import { cn } from "@/lib/utils";

// 대시보드 쉘 — 사이드바 + 헤더 + 콘텐츠 (scaffold: 구조만)
export function DashboardShell({ children }: { children: ReactNode }) {
  const { sidebarOpen, toggleSidebar } = useUiStore();

  return (
    <div className="flex min-h-screen">
      <aside
        className={cn(
          "hidden flex-col border-r border-[color:var(--dash-border)] bg-[color:var(--dash-surface)] backdrop-blur md:flex",
          sidebarOpen ? "w-60" : "w-16",
        )}
      >
        <div className="flex h-16 items-center gap-2 px-4">
          <span className="font-display text-lg font-bold">QuantBridge</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-2">
          {/* Stage 3: 사이드바 네비게이션 — Strategies / Backtests / Trading / Exchanges */}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="sticky top-0 z-[var(--z-nav)] flex h-16 items-center justify-between border-b border-[color:var(--dash-border)] bg-[color:var(--dash-surface)] px-4 backdrop-blur md:px-6">
          <button
            type="button"
            onClick={toggleSidebar}
            className="rounded-md px-3 py-2 text-sm text-[color:var(--dash-text-muted)] hover:text-[color:var(--dash-text)] md:hidden"
          >
            메뉴
          </button>
          <div className="ml-auto flex items-center gap-3">
            <UserButton />
          </div>
        </header>
        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}
