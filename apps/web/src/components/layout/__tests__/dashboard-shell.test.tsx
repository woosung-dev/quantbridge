// DashboardShell — C 이식 S3 (프로토타입 셸 구조) 단위 테스트.
// breadcrumb pageTitle 자동 derivation + nav 6개(disabled 0) + nav-count 배지 정직성.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { DashboardShell } from "@/components/layout/dashboard-shell";

// usePathname 만 가변 → mock 모듈 export 를 변수로 통제.
let mockPathname = "/strategies";
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
  // AccountButton(구 Clerk UserButton 자리)이 로그아웃 후 이동에 useRouter 를 쓴다 — ADR-034.
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn(), push: vi.fn() }),
}));

// tier-c: 셸이 RealtimeBridge 를 mount — 셸 단위 테스트는 브리지를 null 로 치환
// (브리지 자체 동작은 features/realtime 테스트가 소유).
vi.mock("@/features/realtime/realtime-bridge", () => ({
  RealtimeBridge: () => null,
}));

// C 이식 S3: 스토어에서 sidebarOpen/toggleSidebar/setSidebarOpen 삭제 — mobileNav 만 남는다.
const mockUiState = {
  mobileNavOpen: false,
  setMobileNavOpen: () => {},
};
vi.mock("@/store/ui-store", () => ({
  useUiStore: <T,>(selector?: (s: typeof mockUiState) => T) =>
    selector ? selector(mockUiState) : mockUiState,
}));

// nav-count 3개 = 목록 스키마 total 재사용. 셸 테스트는 데이터 페치를 격리하려 훅을 mock.
vi.mock("@/features/strategy/hooks", () => ({
  useStrategies: () => ({ data: { total: 12 } }),
}));
vi.mock("@/features/backtest/hooks", () => ({
  useBacktests: () => ({ data: { total: 48 } }),
}));
vi.mock("@/features/trading/hooks", () => ({
  useOpenOrdersCount: () => 7,
}));

afterEach(() => {
  cleanup();
  mockPathname = "/strategies";
});

describe("DashboardShell — C 이식 S3 프로토타입 셸", () => {
  it("/strategies 에서 breadcrumb 에 '전략' 이 노출된다", () => {
    mockPathname = "/strategies";
    render(
      <DashboardShell>
        <p>content</p>
      </DashboardShell>,
    );
    // crumbs 의 .here + nav aria-label 이 겹칠 수 있어 텍스트 존재만 확인.
    expect(screen.getAllByText("전략").length).toBeGreaterThan(0);
  });

  it("/backtests/abc 에서 prefix 매칭으로 breadcrumb '백테스트' 가 노출된다", () => {
    mockPathname = "/backtests/abc-123";
    render(
      <DashboardShell>
        <p>content</p>
      </DashboardShell>,
    );
    expect(screen.getAllByText("백테스트").length).toBeGreaterThan(0);
  });

  it("data-theme=\"dash\" 스코프가 새지 않는다 (라이트/다크 앱 전역 토글)", () => {
    mockPathname = "/trading";
    const { container } = render(
      <DashboardShell>
        <p>content</p>
      </DashboardShell>,
    );
    expect(container.querySelector("[data-theme=\"dash\"]")).toBeNull();
  });

  it("nav 6개가 모두 링크로 렌더되고 disabled(곧 출시) 항목이 없다", () => {
    const { container } = render(
      <DashboardShell>
        <p>content</p>
      </DashboardShell>,
    );
    // 프로토타입 6개 — 전부 실제 라우트(링크). 데스크톱 sidebar 만 렌더(모바일 drawer 는 닫힘).
    for (const label of ["대시보드", "전략", "백테스트", "옵티마이저", "트레이딩", "주문"]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
    // disabled 항목 제거 확인 — aria-disabled 요소 0.
    expect(container.querySelectorAll('[aria-disabled="true"]').length).toBe(0);
  });

  it("nav-count 배지 3개가 목록 total 로 렌더되고, 주문 배지는 미체결 수를 밝힌다", () => {
    const { container } = render(
      <DashboardShell>
        <p>content</p>
      </DashboardShell>,
    );
    const badges = container.querySelectorAll(".nav-count");
    // 전략/백테스트/주문 = 3개.
    expect(badges.length).toBe(3);
    const texts = Array.from(badges).map((b) => b.textContent);
    expect(texts).toEqual(["12", "48", "7"]);
    const ordersBadge = Array.from(badges).find((b) => b.textContent === "7");
    expect(ordersBadge?.getAttribute("title")).toMatch(/미체결/);
    expect(ordersBadge?.getAttribute("title")).toMatch(/대기\+전송/);
  });
});
