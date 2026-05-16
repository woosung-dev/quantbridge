// 인증된 앱 페이지 헤더 — 모바일 햄버거 + 페이지 타이틀 slot + 모바일 UserButton.
// Sprint 45: dashboard-shell.tsx 에서 분리. pageTitle / onToggleSidebar 는 부모(Shell)에서 prop 주입.
// Sprint 44-WC1 polish: hamburger Menu lucide + 44×44 hit area + bg-alt hover transition 150ms 보존.
// Sprint 60 S4 (BL-285/300/305): 햄버거 → mobileNavOpen 토글 (drawer open) + UserButton min 36×36 wrapper.

import { UserButton } from "@clerk/nextjs";
import { Menu as MenuIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { useUiStore } from "@/store/ui-store";

type DashboardHeaderProps = {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  pageTitle: string;
};

export function DashboardHeader({ sidebarOpen, onToggleSidebar, pageTitle }: DashboardHeaderProps) {
  // BL-300: 햄버거는 mobile-only(md:hidden) → 모바일 drawer toggle 전용.
  // 데스크톱 sidebar collapse 는 별도 (현재 desktop trigger 없음).
  const mobileNavOpen = useUiStore((s) => s.mobileNavOpen);
  const setMobileNavOpen = useUiStore((s) => s.setMobileNavOpen);
  const handleHamburgerClick = () => {
    setMobileNavOpen(!mobileNavOpen);
  };
  // onToggleSidebar / sidebarOpen 는 desktop sidebar 와의 인터페이스 호환 유지 (현재 dead but kept).
  void onToggleSidebar;
  void sidebarOpen;

  return (
    <header className="sticky top-0 z-[100] flex h-16 items-center gap-3 border-b border-[color:var(--border)] bg-[color:var(--card)] px-4 backdrop-blur md:px-6">
      {/* Sprint 44-WC1 polish: mobile hamburger — Menu lucide icon + 44×44 hit area
          + bg-alt hover transition 150ms (DESIGN.md §10.3 Left 1 정합). */}
      <button
        type="button"
        onClick={handleHamburgerClick}
        aria-label="메뉴 열기"
        aria-expanded={mobileNavOpen}
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
        {/* 데스크톱에서는 사이드바 footer 의 UserButton 으로 대체. 모바일은 sidebar 가 hidden 이므로 헤더 우측에도 노출.
            BL-305 (Sprint 60): Clerk UserButton 모바일에서 0×0 collapse 방지 — wrapper 강제.
            BL-339 (Sprint 61 T-2): 36×36 → 44×44 로 확장 (Apple HIG / Material 44pt 권고).
            Mobile QA 페르소나 발견: avatar trigger 28×28 = HIG 미달 → 출퇴근 환경 오탑 빈번. */}
        <div className="inline-flex min-h-11 min-w-11 items-center justify-center md:hidden">
          {/* Sprint 60 G.3-2 (P1, auth): wrapper 만으로는 hit target 0×0 가능 (Clerk 내부 root 도 강제 size). */}
          <UserButton
            appearance={{
              elements: {
                rootBox: "shrink-0 size-11",
                userButtonTrigger: "size-11",
                avatarBox: "size-9",
              },
            }}
          />
        </div>
      </div>
    </header>
  );
}
