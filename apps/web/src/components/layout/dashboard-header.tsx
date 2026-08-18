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

      {/* 풀 사이드바(≥1025px)는 footer 의 계정 버튼을 쓴다. 그 아래(모바일 + 아이콘 레일
          769~1024px)는 사이드바 계정이 숨거나 아바타만 남으므로 상단바가 로그아웃/삭제 경로를 맡는다.
          터치 타깃 ≥44pt 는 AccountButton 이 size="lg" 로 보장한다 (BL-305/339 후속).
          ★min-[1025px]:hidden — KITPORT 의 max-width:768/1024 는 경계 **포함**이라 md:/lg: 를
          쓰면 정확히 그 폭에서 양쪽이 동시에 숨는 데드심이 난다(2026-08-18 실발화). 레일 구간의
          사이드바 액션 숨김은 globals 의 `.sidebar .qb-acct-action` 스코프 규칙이 담당한다. */}
      <div className="inline-flex min-h-11 min-w-11 items-center justify-center min-[1025px]:hidden">
        <AccountButton size="lg" />
      </div>
    </header>
  );
}
