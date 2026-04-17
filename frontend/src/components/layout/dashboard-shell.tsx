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

// 대시보드 쉘 — 사이드바 + 헤더 + 콘텐츠
export function DashboardShell({ children }: { children: ReactNode }) {
  const { sidebarOpen, toggleSidebar } = useUiStore();
  const pathname = usePathname();

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
                    "cursor-not-allowed text-[color:var(--dash-text-muted)] opacity-50",
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
                    ? "bg-[color:var(--dash-surface-elevated)] text-[color:var(--dash-text)]"
                    : "text-[color:var(--dash-text-muted)] hover:bg-[color:var(--dash-surface-elevated)] hover:text-[color:var(--dash-text)]",
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
        <header className="sticky top-0 z-[100] flex h-16 items-center justify-between border-b border-[color:var(--dash-border)] bg-[color:var(--dash-surface)] px-4 backdrop-blur md:px-6">
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
        <main id="main-content" className="flex-1">
          {children}
        </main>
      </div>
    </div>
  );
}
