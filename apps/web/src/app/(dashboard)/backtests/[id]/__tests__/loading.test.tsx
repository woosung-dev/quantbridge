// 상세 loading 은 클라이언트 DetailSkeleton 과 같은 골격 한 벌이어야 한다 (스킬 §4.5) —
// 라우트 전환 스켈레톤과 클라 로딩 스켈레톤이 두 언어·두 폭으로 그려지던 회귀 방지.

import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// loading.tsx → backtest-detail-view.tsx 의 import 체인이 실훅을 당기지 않도록
// 형제 테스트(rerun-integration)와 같은 mock 표면을 깐다. 렌더 대상은 스켈레톤뿐이다.
vi.mock("@/features/backtest/hooks", () => ({
  useBacktest: () => ({ data: undefined, isLoading: true, isError: false, refetch: vi.fn(), error: null }),
  useBacktestProgress: () => ({ data: undefined, refetch: vi.fn() }),
  useBacktestTrades: () => ({ data: undefined, isLoading: true, isError: false, error: null }),
  useCreateBacktest: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateBacktestShare: () => ({ mutate: vi.fn(), isPending: false }),
  useRevokeBacktestShare: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import BacktestDetailLoading from "../loading";

describe("BacktestDetailLoading — DetailSkeleton 재사용", () => {
  it("클라 DetailSkeleton(.page + C 어휘)을 그대로 그린다", () => {
    const { container } = render(<BacktestDetailLoading />);
    expect(container.querySelector("main.page")).not.toBeNull();
    expect(
      container.querySelector('[data-testid="backtest-detail-skeleton"]'),
    ).not.toBeNull();
    // 헤더 칩 자리 5개 — 실헤더 칩 수(상태·Bybit·기간·엔진·ID)와 일치
    expect(container.querySelectorAll(".report-meta .sk").length).toBe(5);
    // KPI 4칸 골격
    expect(container.querySelectorAll(".kpi-row .kpi").length).toBe(4);
  });
});
