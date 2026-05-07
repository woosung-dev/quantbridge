"use client";

// 인증된 앱 페이지 공통 App Shell — 사이드바(220px) + 헤더(64px) + 콘텐츠.
// Sprint 41-B2: 프로토타입 06/09/02/03 visual layout 정합 (sidebar w-[220px], 페이지 타이틀 slot,
// /trading 진입 시 data-theme="dash" 자동 토글로 Full Dark 모드).

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
  { href: "/backtests", label: "백테스트", icon: BarChartIcon, disabled: false },
  { href: "/trading", label: "트레이딩", icon: ZapIcon, disabled: false },
  { href: "/exchanges", label: "거래소", icon: GlobeIcon, disabled: true },
] as const;

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

  // 프로토타입 03 Full Dark — /trading 라우트만 dash 테마 적용 (App Shell 전체).
  const isDashTheme = pathname?.startsWith("/trading") ?? false;
  const pageTitle = derivePageTitle(pathname);

  return (
    <div
      data-theme={isDashTheme ? "dash" : undefined}
      className="flex min-h-screen bg-[color:var(--background)] text-[color:var(--foreground)]"
    >
      <aside
        className={cn(
          "hidden flex-col border-r border-[color:var(--sidebar-border)] bg-[color:var(--sidebar)] text-[color:var(--sidebar-foreground)] md:flex",
          // 프로토타입 06/09/02/03 fixed sidebar 220px (collapsed 64px, 모바일 hidden)
          sidebarOpen ? "w-[220px]" : "w-16",
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
          className="flex flex-1 flex-col gap-1 px-2 py-2"
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

        {/* 사이드바 footer — 프로필 dock (UserButton). 프로토타입 06/03 sidebar-bottom 패턴. */}
        <div className="mt-auto border-t border-[color:var(--sidebar-border)] px-3 py-3">
          <div
            className={cn(
              "flex items-center gap-2",
              sidebarOpen ? "justify-start" : "justify-center",
            )}
          >
            <UserButton appearance={{ elements: { rootBox: "shrink-0" } }} />
            {sidebarOpen && (
              <span className="text-xs text-[color:var(--muted-foreground)] truncate">계정</span>
            )}
          </div>
        </div>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="sticky top-0 z-[100] flex h-16 items-center gap-3 border-b border-[color:var(--border)] bg-[color:var(--card)] px-4 backdrop-blur md:px-6">
          <button
            type="button"
            onClick={toggleSidebar}
            className="rounded-md px-3 py-2 text-sm text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)] md:hidden"
          >
            메뉴
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
        <main id="main-content" className="flex-1">
          {children}
        </main>
      </div>
    </div>
  );
}
