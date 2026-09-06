// 인증된 앱 페이지 상단바 — 모바일 햄버거 + breadcrumb(현재 페이지) + 테마 토글 + 모바일 계정 버튼.
// C 이식 S3: 프로토타입(screen-02) .topbar 구조로 재작성. position:sticky + margin-left var(--sidebar-w).
//   죽은 prop(sidebarOpen/onToggleSidebar) 삭제 — 데스크톱 sidebar 접힘은 순수 CSS 레일이 담당.
//   햄버거는 .hamburger 시맨틱 클래스(≤768px 에서만 CSS 로 노출)로 모바일 drawer 를 연다.
//   검색창은 백엔드 검색 기능이 없어 이식하지 않는다(가짜 UI 방지).

import { Menu as MenuIcon } from "lucide-react";

import { ThemeToggle } from "@/components/ui/theme-toggle";
import { AccountButton } from "./account-button";
import { useUiStore } from "@/store/ui-store";

type DashboardHeaderProps = {
  pageTitle: string;
};

export function DashboardHeader({ pageTitle }: DashboardHeaderProps) {
  const mobileNavOpen = useUiStore((s) => s.mobileNavOpen);
  const setMobileNavOpen = useUiStore((s) => s.setMobileNavOpen);
  const handleHamburgerClick = () => {
    setMobileNavOpen(!mobileNavOpen);
  };

  return (
    <header className="topbar">
      {/* .hamburger — base display:none, ≤768px 에서 CSS 로 grid 노출 (모바일 전용). */}
      <button
        type="button"
        className="hamburger"
        onClick={handleHamburgerClick}
        aria-label="메뉴 열기"
        aria-expanded={mobileNavOpen}
      >
        <MenuIcon className="size-5" aria-hidden="true" />
      </button>

      <nav className="crumbs" aria-label="breadcrumb">
        {pageTitle && <span className="here">{pageTitle}</span>}
      </nav>

      <span className="topbar-spacer" />

      <ThemeToggle />

      {/* 계정 경로는 폭 구간마다 주인이 다르다.
            ≥1025px  풀 사이드바 footer 의 계정 버튼
            769~1024 아이콘 레일이라 사이드바 액션이 숨는다 → **이 상단바 인스턴스**
            ≤768px   사이드바 자체가 없다 → 모바일 drawer 의 계정 dock(mobile-nav.tsx)
          ★≤768 을 여기서 뺀 이유(2026-09-06 실측) — 아바타+로그아웃+「계정 지우기」가 149px 라
          320px 상단바에서 햄버거·페이지명·테마토글과 함께 서지 못하고 **문서를 1~7px 넘긴다**
          (`DESIGN.md` §4.3.2 「320px 무횡스크롤」 위반, authed 6라우트 × 2테마 전건 재현).
          drawer 로 옮기면 폭이 풀리고 파괴적 액션이 상단바에서도 빠진다.
          ★경계 표기는 min-[769px]/min-[1025px] 로 잡는다 — KITPORT 의 max-width:768/1024 는 경계
          **포함**이라 md:/lg: 나 max-[N]: 를 쓰면 정확히 그 폭에서 데드심이 난다(2026-08-18 실발화).
          터치 타깃 ≥44pt 는 AccountButton 이 size="lg" 로 보장한다 (BL-305/339 후속). */}
      <div className="hidden min-h-11 min-w-11 items-center justify-center min-[769px]:inline-flex min-[1025px]:hidden">
        <AccountButton size="lg" />
      </div>
    </header>
  );
}
