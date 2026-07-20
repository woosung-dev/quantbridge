// 사이드바 nav 항목 리스트 — pathname 기반 active + nav-count 배지.
// C 이식 S3: 프로토타입(screen-02) nav 6개로 정렬 + disabled 2개(/templates·/exchanges) 제거.
//   시맨틱 클래스(.nav / .nav-item / .label / .nav-count)를 소비하고, 1024px 아이콘 레일은
//   순수 CSS(.label display:none)로 접힌다 — JS 분기 없음. 라벨이 숨는 레일에서도 접근 가능한
//   이름을 위해 <a> 에 aria-label 을 둔다.
//   nav-count 는 상위(sidebar)가 목록 total 을 프롭으로 주입한다 — 이 컴포넌트는 페치하지 않는다.

import Link from "next/link";
import {
  LayoutDashboard as DashboardIcon,
  Code2 as StrategyIcon,
  BarChart3 as BacktestIcon,
  Settings as OptimizerIcon,
  Activity as TradingIcon,
  ClipboardList as OrdersIcon,
  type LucideIcon,
} from "lucide-react";

// nav-count 가 붙는 항목의 데이터 키. 셸이 목록 스키마 total 로 채운다.
export type NavCountKey = "strategies" | "backtests" | "orders";
export type NavCounts = Partial<Record<NavCountKey, number>>;

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  countKey?: NavCountKey;
};

// 프로토타입 screen-02 워크스페이스 nav 6개 (순서·라벨 정합).
export const navItems: readonly NavItem[] = [
  { href: "/dashboard", label: "대시보드", icon: DashboardIcon },
  { href: "/strategies", label: "전략", icon: StrategyIcon, countKey: "strategies" },
  { href: "/backtests", label: "백테스트", icon: BacktestIcon, countKey: "backtests" },
  { href: "/optimizer", label: "옵티마이저", icon: OptimizerIcon },
  { href: "/trading", label: "트레이딩", icon: TradingIcon },
  { href: "/orders", label: "주문", icon: OrdersIcon, countKey: "orders" },
] as const;

// 주문 배지의 정직성 표기. 캐논상 nav-count 는 "미체결 수(대기+전송)"지만, 새 API 없이
// limit=1 로 재사용할 수 있는 값은 목록 total = 전체 원장 건수뿐이다 — 두 수는 다르다.
// 그래서 미체결로 표기하지 않고 툴팁으로 "전체 주문"임을 밝힌다(context-notes §nav-count).
function countTitle(key: NavCountKey, value: number): string {
  switch (key) {
    case "strategies":
      return `전략 ${value}개`;
    case "backtests":
      return `백테스트 ${value}개`;
    case "orders":
      return `전체 주문 ${value}건 (미체결 수 아님)`;
  }
}

type DashboardNavListProps = {
  pathname: string | null;
  // 미제공 시 배지를 렌더하지 않는다 (모바일 drawer 는 배지를 쓰지 않는다).
  counts?: NavCounts;
};

export function DashboardNavList({ pathname, counts }: DashboardNavListProps) {
  return (
    <nav className="nav" aria-label="주요 메뉴">
      {navItems.map((item) => {
        const isActive = pathname?.startsWith(item.href) ?? false;
        const Icon = item.icon;
        const count = item.countKey ? counts?.[item.countKey] : undefined;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-label={item.label}
            aria-current={isActive ? "page" : undefined}
            className={isActive ? "nav-item active" : "nav-item"}
          >
            {/* size 클래스를 붙이지 않는다 — .nav-item svg 시맨틱 CSS(17px·stroke 1.6)가 제어. */}
            <Icon aria-hidden="true" />
            <span className="label">{item.label}</span>
            {item.countKey && typeof count === "number" && (
              <span className="nav-count" title={countTitle(item.countKey, count)}>
                {count}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}
