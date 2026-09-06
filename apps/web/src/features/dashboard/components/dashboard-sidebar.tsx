// 인증된 앱 페이지 사이드바 — brand + nav(+count 배지) + footer dock(AccountButton).
// C 이식 S3: 프로토타입(screen-02) .sidebar 구조로 재작성. position:fixed + width var(--sidebar-w),
//   1024px 아이콘 레일은 순수 CSS(globals.css @media)로 접힌다 — sidebarOpen 프롭 삭제.
//   nav-count 3개는 여기서 목록 스키마 total 을 limit=1 로 페치해 nav-list 에 프롭으로 내린다.
//   이 컴포넌트는 <main> 의 형제라, count 폴링 갱신이 페이지 트리를 리렌더하지 않는다.

import Link from "next/link";

import { useStrategies } from "@/features/strategy/hooks";
import { useBacktests } from "@/features/backtest/hooks";
import { useOpenOrdersCount } from "@/features/trading/hooks";

import { AccountButton } from "@/components/layout/account-button";
import { DashboardNavList, type NavCounts } from "@/components/layout/dashboard-nav-list";

type DashboardSidebarProps = {
  pathname: string | null;
};

export function DashboardSidebar({ pathname }: DashboardSidebarProps) {
  // nav-count = 기존 목록 스키마 total 재사용 (새 API 없음, limit=1 최소 페이로드).
  // H-2: queryKey 는 각 훅이 userId identity 로 구성한다 — getToken 미포함.
  const strategiesQ = useStrategies({ limit: 1, offset: 0, is_archived: false });
  const backtestsQ = useBacktests({ limit: 1, offset: 0 });
  const openOrdersCount = useOpenOrdersCount();

  const counts: NavCounts = {
    strategies: strategiesQ.data?.total,
    backtests: backtestsQ.data?.total,
    orders: openOrdersCount,
  };

  return (
    <aside className="sidebar" aria-label="메인 내비게이션">
      <Link href="/dashboard" className="brand" aria-label="QuantBridge 홈">
        <span className="brand-mark" aria-hidden="true">
          <svg
            aria-hidden="true"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="3 17 9 11 13 15 21 7" />
            <polyline points="15 7 21 7 21 13" />
          </svg>
        </span>
        <span className="brand-name">QuantBridge</span>
      </Link>

      <p className="nav-group-label">워크스페이스</p>
      <DashboardNavList pathname={pathname} counts={counts} />

      {/* footer dock — 계정 표시 + 로그아웃. 레일(≤1024px)에서는 CSS 가 신원을 숨겨 아바타만 남는다.
          ★프로토타입의 하드코딩 이름/부제(`woosung`·`로컬 워크스페이스`)를 재현하지 않는다는 종전
          판단은 옳았다. 다만 그 자리에 `"계정"` 이라는 **고정 문자열**을 넣은 것이 문제였다
          (2026-09-06) — 신원 자리를 차지하면서 「어느 계정으로 들어와 있나」에 답하지 못한다.
          `useAuthCtx().user` 가 실제 이름·이메일을 이미 준다(`apps/web/AGENTS.md` §2). */}
      <div className="sidebar-foot">
        <div className="account">
          <AccountButton size="sm" showIdentity />
        </div>
      </div>
    </aside>
  );
}
