// 모바일 nav drawer — Sprint 60 S4 BL-285/300 (Sheet 기반 left-side drawer).
// 햄버거 click 시 열리고, route 변경 시 자동 close (Next 16 Link 이동 후 drawer 잔존 방지).
"use client";

import { useEffect, useRef } from "react";

import { X as CloseIcon } from "lucide-react";

import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useUiStore } from "@/store/ui-store";

import { DashboardNavList } from "./dashboard-nav-list";

type MobileNavProps = {
  pathname: string | null;
};

export function MobileNav({ pathname }: MobileNavProps) {
  const mobileNavOpen = useUiStore((s) => s.mobileNavOpen);
  const setMobileNavOpen = useUiStore((s) => s.setMobileNavOpen);

  // route 변경 시 drawer 자동 close — Link click 후 새 페이지에서 drawer 잔존 방지.
  // dep 없는 unstable 객체 회피 위해 string pathname + prev ref 비교 패턴 (frontend.md H-1).
  const lastPathRef = useRef(pathname);
  useEffect(() => {
    if (pathname !== lastPathRef.current) {
      lastPathRef.current = pathname;
      setMobileNavOpen(false);
    }
  }, [pathname, setMobileNavOpen]);

  // mobileNavOpen=false 시 Portal/nav 자체 미렌더 — 메모리 절약 + 데스크톱 sidebar 와의 label 중복 차단.
  // Sheet 의 Portal 은 닫혀있어도 children 을 mount 유지하므로 명시적으로 unmount.
  if (!mobileNavOpen) {
    return null;
  }

  return (
    <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
      {/* SheetContent 기본 = bottom slide. left-side drawer 로 override.
          showHandle=false (handle 은 bottom-sheet 시각 단서, left drawer 에는 불필요). */}
      <SheetContent
        showHandle={false}
        className="inset-y-0 left-0 right-auto bottom-auto h-dvh w-[280px] max-w-[85vw] rounded-none border-r border-t-0 p-0 pb-0 data-open:slide-in-from-left data-closed:slide-out-to-left md:hidden"
      >
        <SheetHeader className="flex flex-row items-center justify-between border-b border-[color:var(--border)] px-4 py-3">
          <SheetTitle className="font-display text-base">QuantBridge</SheetTitle>
          {/* G.3-1 (P1, a11y) — touch screen reader 사용자 escape 의무. 44×44 visible close button */}
          <SheetClose
            aria-label="메뉴 닫기"
            className="grid size-11 place-items-center rounded-md text-[color:var(--muted-foreground)] hover:bg-[color:var(--sidebar-accent)] hover:text-[color:var(--foreground)] transition-colors"
          >
            <CloseIcon className="size-5" aria-hidden="true" />
          </SheetClose>
        </SheetHeader>
        <DashboardNavList sidebarOpen={true} pathname={pathname} />
      </SheetContent>
    </Sheet>
  );
}
