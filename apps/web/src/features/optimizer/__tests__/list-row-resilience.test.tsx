// Sprint 62 T-1 (BL-350+354) — Optimizer listing graceful error 회귀 test
//
// Multi-Agent QA 2026-05-17 발견 (★★★ Curious + Casual 공통 P0):
// /optimizer 진입 시 Zod validation error JSON 풀텍스트 ~20 row 도배. 본 fix =
// (1) api.ts row-level safeParse → invalid skip + skipped_count (smoke 만 검증, fixture 정합 별도)
// (2) optimizer-run-list 컴포넌트 catch error 시 raw message 차단 + user-friendly fallback ← 본 test

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { OptimizerRunList } from "@/features/optimizer/components/optimizer-run-list";

// React Query hook mock — useOptimizationRuns 가 error / data 시뮬레이션.
vi.mock("@/features/optimizer/hooks", () => ({
  useOptimizationRuns: vi.fn(),
}));

import { useOptimizationRuns } from "@/features/optimizer/hooks";

function renderWithQueryClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("OptimizerRunList graceful error (Sprint 62 T-1, BL-350+354)", () => {
  it("error 발생 시 raw error.message 노출 차단 + user-friendly 메시지", () => {
    // Sprint 50-52 retro row + 53-55 schema tightening 으로 Zod parse 실패 시뮬레이션
    vi.mocked(useOptimizationRuns).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error(
        '[{"expected":"number","code":"invalid_type","path":["items",0,"param_space","bayesian_n_initial_random"]}, ...] (~20 row)',
      ),
    } as unknown as ReturnType<typeof useOptimizationRuns>);

    renderWithQueryClient(<OptimizerRunList />);

    // 1차 발견 패턴 — raw JSON 노출 X
    expect(screen.queryByText(/expected.*invalid_type/)).not.toBeInTheDocument();
    expect(screen.queryByText(/bayesian_n_initial_random/)).not.toBeInTheDocument();
    // W3-C C 이식: 에러는 state-box failed(role=alert) + user-friendly 문구(W1 사유 SSOT)로 렌더.
    const box = screen.getByTestId("optimizer-error");
    expect(box.className).toContain("state-box");
    expect(box.className).toContain("failed");
    expect(screen.getByText(/불러오지 못했습니다/)).toBeInTheDocument();
    // 에러 패널에 실존 엔드포인트 + HTTP 코드 노출.
    expect(box.textContent).toMatch(/GET \/api\/v1\/optimizer\/runs/);
  });

  it("skipped_count > 0 시 graceful warn 표시", () => {
    vi.mocked(useOptimizationRuns).mockReturnValue({
      data: {
        items: [],
        total: 5,
        limit: 20,
        offset: 0,
        skipped_count: 3,
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useOptimizationRuns>);

    renderWithQueryClient(<OptimizerRunList />);
    // skipped_count = 3 → graceful 메시지 (testid 로 직접 query)
    const warn = screen.getByTestId("optimizer-skipped-warn");
    expect(warn).toBeInTheDocument();
    expect(warn.textContent).toMatch(/3개 항목이 표시되지 않습니다/);
  });

  it("isLoading 시 스켈레톤(.sk) 노출 + error 메시지 부재 (W3-C C 이식)", () => {
    vi.mocked(useOptimizationRuns).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof useOptimizationRuns>);

    const { container } = renderWithQueryClient(<OptimizerRunList />);
    expect(screen.getByTestId("optimizer-skeleton")).toBeInTheDocument();
    expect(container.querySelector(".sk.sk-cell")).not.toBeNull();
    expect(screen.queryByText(/불러오지 못했습니다/)).not.toBeInTheDocument();
  });
});
