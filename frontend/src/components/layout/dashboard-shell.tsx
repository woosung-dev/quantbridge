"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";
import {
  Home as HomeIcon,
  Code as CodeIcon,
  Layers as LayersIcon,
  BarChart as BarChartIcon,
  Zap as ZapIcon,
  Globe as GlobeIcon,
  type LucideIcon,
} from "lucide-react";
import { useUiStore } from "@/store/ui-store";
import { cn } from "@/lib/utils";

// 사이드바 네비게이션 — DESIGN.md §10.2 순서
// Sprint 7c: /strategies, /trading만 활성화. 나머지는 disabled ("곧 출시")
type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  disabled: boolean;
};

const navItems: readonly NavItem[] = [
  { href: "/dashboard", label: "대시보드", icon: HomeIcon, disabled: true },
  { href: "/strategies", label: "전략", icon: CodeIcon, disabled: false },
  { href: "/templates", label: "템플릿", icon: LayersIcon, disabled: true },
  { href: "/backtests", label: "백테스트", icon: BarChartIcon, disabled: true },
  { href: "/trading", label: "트레이딩", icon: ZapIcon, disabled: false },
  { href: "/exchanges", label: "거래소", icon: GlobeIcon, disabled: true },
] as const;

// 대시보드 쉘 — 사이드바 + 헤더 + 콘텐츠.
// shadcn 시맨틱 토큰 사용(--sidebar, --border, --foreground 등) → Light/Dark 자동 대응.
// DESIGN.md §10.4 App Shell 테마별 색상 준수. dash 테마는 [data-theme="dash"] 스코프에서 자동 재매핑.
export function DashboardShell({ children }: { children: ReactNode }) {
  const { sidebarOpen, toggleSidebar } = useUiStore();
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-[color:var(--background)] text-[color:var(--foreground)]">
      <aside
        className={cn(
          "hidden flex-col border-r border-[color:var(--sidebar-border)] bg-[color:var(--sidebar)] text-[color:var(--sidebar-foreground)] md:flex",
          sidebarOpen ? "w-60" : "w-16",
        )}
      >
        {/* 로고 — Plus Jakarta Sans 볼드 + primary-gradient 마크 */}
        <Link
          href="/strategies"
          className="flex h-16 items-center gap-2.5 px-4 hover:opacity-90"
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

        <nav
          aria-label="메인 내비게이션"
          className="flex flex-1 flex-col gap-1 px-2"
        >
          {navItems.map((item) => {
            const isActive = pathname?.startsWith(item.href) ?? false;
            const Icon = item.icon;
            const baseClass = cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
              sidebarOpen ? "justify-start" : "justify-center",
            );

            if (item.disabled) {
              return (
                <span
                  key={item.href}
                  aria-disabled="true"
                  title="곧 출시"
                  className={cn(
                    baseClass,
                    "cursor-not-allowed text-[color:var(--muted-foreground)] opacity-50",
                  )}
                >
                  <Icon className="size-4 shrink-0" aria-hidden="true" />
                  {sidebarOpen && <span className="truncate">{item.label}</span>}
                </span>
              );
            }

            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  baseClass,
                  isActive
                    ? "bg-[color:var(--sidebar-accent)] text-[color:var(--sidebar-accent-foreground)] font-medium"
                    : "text-[color:var(--muted-foreground)] hover:bg-[color:var(--sidebar-accent)] hover:text-[color:var(--sidebar-accent-foreground)]",
                )}
              >
                <Icon className="size-4 shrink-0" aria-hidden="true" />
                {sidebarOpen && <span className="truncate">{item.label}</span>}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="sticky top-0 z-[100] flex h-16 items-center justify-between border-b border-[color:var(--border)] bg-[color:var(--card)] px-4 backdrop-blur md:px-6">
          <button
            type="button"
            onClick={toggleSidebar}
            className="rounded-md px-3 py-2 text-sm text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)] md:hidden"
          >
            메뉴
          </button>
          <div className="ml-auto flex items-center gap-3">
            <UserButton />
          </div>
        </header>
        <main id="main-content" className="flex-1">
          {children}
        </main>
      </div>
    </div>
  );
}
