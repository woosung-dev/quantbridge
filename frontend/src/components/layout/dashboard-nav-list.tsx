// 사이드바 nav 항목 리스트 — pathname 기반 active state + disabled 항목 표시.
// Sprint 45: dashboard-shell.tsx 에서 분리. props 로 sidebarOpen, pathname 받음.
// Sprint 44-WC1 active 스타일 (primary-light bg + primary text + 3px border-left + pl-9px) 보존.

import Link from "next/link";
import {
  Home as HomeIcon,
  Code as CodeIcon,
  Layers as LayersIcon,
  BarChart as BarChartIcon,
  Zap as ZapIcon,
  Globe as GlobeIcon,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  disabled: boolean;
};

export const navItems: readonly NavItem[] = [
  { href: "/dashboard", label: "대시보드", icon: HomeIcon, disabled: true },
  { href: "/strategies", label: "전략", icon: CodeIcon, disabled: false },
  { href: "/templates", label: "템플릿", icon: LayersIcon, disabled: true },
  { href: "/backtests", label: "백테스트", icon: BarChartIcon, disabled: false },
  { href: "/trading", label: "트레이딩", icon: ZapIcon, disabled: false },
  { href: "/exchanges", label: "거래소", icon: GlobeIcon, disabled: true },
] as const;

type DashboardNavListProps = {
  sidebarOpen: boolean;
  pathname: string | null;
};

export function DashboardNavList({ sidebarOpen, pathname }: DashboardNavListProps) {
  return (
    <nav
      aria-label="메인 내비게이션"
      className="flex flex-1 flex-col gap-1 px-2 py-2"
    >
      {navItems.map((item) => {
        const isActive = pathname?.startsWith(item.href) ?? false;
        const Icon = item.icon;
        // Sprint 44-WC1: motion-safe transition 200ms (DESIGN.md §10.2 prototype 06).
        // motion-reduce:transition-none → prefers-reduced-motion 보호.
        const baseClass = cn(
          "relative flex items-center gap-3 rounded-md px-3 py-2 text-sm",
          "transition-[background-color,color,padding-left] duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]",
          "motion-reduce:transition-none",
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

        // Sprint 44-WC1: active = primary-light bg + primary text + 3px border-left
        // + pl-9px (DESIGN.md §10.2 / prototype 06 .nav-item.active 정합).
        // hover = bg-alt (sidebar-accent) — active 와 명확히 구분.
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              baseClass,
              isActive
                ? "bg-[color:var(--primary-light)] text-[color:var(--primary)] font-medium border-l-[3px] border-[color:var(--primary)] pl-[9px]"
                : "text-[color:var(--muted-foreground)] hover:bg-[color:var(--sidebar-accent)] hover:text-[color:var(--sidebar-accent-foreground)]",
            )}
          >
            <Icon
              className={cn(
                "size-4 shrink-0",
                isActive && "stroke-[color:var(--primary)]",
              )}
              aria-hidden="true"
            />
            {sidebarOpen && <span className="truncate">{item.label}</span>}
          </Link>
        );
      })}
    </nav>
  );
}
