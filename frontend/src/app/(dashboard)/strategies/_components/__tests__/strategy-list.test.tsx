// 전략 목록(C 이식 screen-06) 시맨틱 구조 회귀 테스트 — 프로토타입 유래 클래스/상태 4종 assert.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { StrategyList } from "@/app/(dashboard)/strategies/_components/strategy-list";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/strategies",
  useSearchParams: () => new URLSearchParams(),
}));

const mockUseStrategies = vi.fn();
vi.mock("@/features/strategy/hooks", () => ({
  useStrategies: (...args: unknown[]) => mockUseStrategies(...args),
}));

function makeQc() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function makeItem(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: "00000000-0000-4000-8000-000000000001",
    name: "MA Crossover Strategy",
    pine_version: "v5" as const,
    parse_status: "ok" as const,
    parse_errors: null,
    timeframe: "1h",
    symbol: "BTC/USDT",
    tags: [],
    trading_sessions: [],
    settings: null,
    pine_declared_qty: null,
    is_archived: false,
    created_at: "2026-04-14T09:00:00Z",
    updated_at: "2026-04-14T09:32:00Z",
    ...overrides,
  };
}

function renderList() {
  return render(
    <QueryClientProvider client={makeQc()}>
      <StrategyList />
    </QueryClientProvider>,
  );
}

describe("StrategyList — C 이식 시맨틱 구조", () => {
  afterEach(() => {
    cleanup();
    mockUseStrategies.mockReset();
  });

  it("표는 table.trades + backed 열 5개(전략명/상태/심볼·주기/마지막 수정/액션)를 그린다", () => {
    mockUseStrategies.mockReturnValue({
      data: { items: [makeItem()], total: 1, page: 1, limit: 20, total_pages: 1 },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    renderList();

    const table = screen.getByRole("table", { name: /전략 목록 1개/ });
    expect(table.className).toContain("trades");
    const headers = within(table).getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual(["전략명", "상태", "심볼 · 주기", "마지막 수정", "액션"]);
    // parse_status ok → "변환 가능" chip done (원시 enum 미노출)
    const row = screen.getByTestId("strategy-row-00000000-0000-4000-8000-000000000001");
    expect(within(row).getByText("변환 가능").className).toBe("chip done");
    expect(within(row).getByText("MA Crossover Strategy").className).toBe("strat-name");
    expect(within(row).getByText("00000000")).toBeTruthy();
  });

  it("파싱 상태 필터는 role=group + 탭 4종(전체/변환 가능/일부 미지원/오류)이다", () => {
    mockUseStrategies.mockReturnValue({
      data: { items: [makeItem()], total: 1, page: 1, limit: 20, total_pages: 1 },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    renderList();
    const group = screen.getByRole("group", { name: "파싱 상태 필터" });
    const labels = within(group).getAllByRole("button").map((b) => b.textContent);
    expect(labels).toEqual(["전체", "변환 가능", "일부 미지원", "오류"]);
  });

  it("로딩 상태는 .sk 스켈레톤 표를 그린다", () => {
    mockUseStrategies.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    renderList();
    expect(screen.getByTestId("strategy-skeleton")).toBeTruthy();
  });

  it("에러 상태는 .state-box.failed + 실제 엔드포인트 코드를 노출한다", () => {
    mockUseStrategies.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("boom"),
      refetch: vi.fn(),
    });
    renderList();
    const box = screen.getByTestId("strategy-error");
    expect(box.className).toContain("state-box failed");
    expect(box.getAttribute("role")).toBe("alert");
    expect(screen.getByText("GET /api/v1/strategies")).toBeTruthy();
  });

  it("빈 상태는 state-box + 새 전략 등록 CTA 를 그린다", () => {
    mockUseStrategies.mockReturnValue({
      data: { items: [], total: 0, page: 1, limit: 20, total_pages: 0 },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    renderList();
    expect(screen.getByTestId("strategy-empty")).toBeTruthy();
    expect(screen.getByText("새 전략 등록")).toBeTruthy();
  });

  it("심볼·주기가 없으면 무데이터 셀(EMPTY_CELL + title)로 표기한다", () => {
    mockUseStrategies.mockReturnValue({
      data: {
        items: [makeItem({ symbol: null, timeframe: null })],
        total: 1,
        page: 1,
        limit: 20,
        total_pages: 1,
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    renderList();
    const cell = screen.getByTitle("이 전략에는 심볼과 주기가 저장돼 있지 않습니다.");
    expect(cell.textContent).toBe("—");
  });
});
