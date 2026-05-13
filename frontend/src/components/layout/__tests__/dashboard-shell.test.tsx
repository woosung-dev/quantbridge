// DashboardShell — Sprint 41-B2 (App Shell prototype 정합) 단위 테스트.
// pageTitle slot 자동 derivation + /trading 진입 시 data-theme="dash" 자동 토글 검증.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { DashboardShell } from "@/components/layout/dashboard-shell";

// usePathname 만 가변 → mock 모듈 export 를 변수로 통제.
let mockPathname = "/strategies";
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
}));

vi.mock("@clerk/nextjs", () => ({
  UserButton: () => <div data-testid="user-button" />,
}));

// useUiStore — sidebarOpen=true 기본 (proto 06/09 상태). selector 호환 mock.
// Sprint 60 S4: mobileNavOpen / setMobileNavOpen 추가 (MobileNav drawer state). 기본 false 라
// drawer 미렌더 → desktop sidebar 와의 nav label 중복 방지.
const mockUiState = {
  sidebarOpen: true,
  mobileNavOpen: false,
  toggleSidebar: () => {},
  setSidebarOpen: () => {},
  setMobileNavOpen: () => {},
};
vi.mock("@/store/ui-store", () => ({
  useUiStore: <T,>(selector?: (s: typeof mockUiState) => T) =>
    selector ? selector(mockUiState) : mockUiState,
}));

afterEach(() => {
  cleanup();
  mockPathname = "/strategies";
});

describe("DashboardShell — Sprint 41-B2 prototype layout", () => {
  it("/strategies 에서 페이지 타이틀 '전략' 이 헤더 slot 에 노출된다", () => {
    mockPathname = "/strategies";
    render(
      <DashboardShell>
        <p>content</p>
      </DashboardShell>,
    );
    expect(
      screen.getAllByRole("heading", { name: "전략" }).length,
    ).toBeGreaterThan(0);
  });

  it("/backtests/abc 에서 prefix 매칭으로 '백테스트' 가 헤더에 노출된다", () => {
    mockPathname = "/backtests/abc-123";
    render(
      <DashboardShell>
        <p>content</p>
      </DashboardShell>,
    );
    expect(
      screen.getAllByRole("heading", { name: "백테스트" }).length,
    ).toBeGreaterThan(0);
  });

  it("/trading 에서도 data-theme=\"dash\" 가 적용되지 않는다 (Sprint 42-polish-3 화이트 통일)", () => {
    mockPathname = "/trading";
    const { container } = render(
      <DashboardShell>
        <p>content</p>
      </DashboardShell>,
    );
    expect(container.querySelector("[data-theme=\"dash\"]")).toBeNull();
  });

  it("/strategies 에서도 dash 테마가 적용되지 않는다 (Light 통일)", () => {
    mockPathname = "/strategies";
    const { container } = render(
      <DashboardShell>
        <p>content</p>
      </DashboardShell>,
    );
    expect(container.querySelector("[data-theme=\"dash\"]")).toBeNull();
  });

  it("sidebar nav 에 활성 항목 4개 (전략/백테스트/트레이딩) 와 disabled 3개 (대시보드/템플릿/거래소) 가 렌더된다", () => {
    render(
      <DashboardShell>
        <p>content</p>
      </DashboardShell>,
    );
    // 활성 (link)
    expect(screen.getByRole("link", { name: /전략/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /백테스트/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /트레이딩/ })).toBeInTheDocument();
    // disabled (aria-disabled span)
    const disabledLabels = ["대시보드", "템플릿", "거래소"];
    for (const label of disabledLabels) {
      const item = screen.getByText(label);
      const span = item.closest("[aria-disabled=\"true\"]");
      expect(span).not.toBeNull();
    }
  });
});
