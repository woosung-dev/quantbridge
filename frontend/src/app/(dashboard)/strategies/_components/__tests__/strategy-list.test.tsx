// 전략 목록(C 이식 screen-06) 시맨틱 구조 회귀 테스트 — 프로토타입 유래 클래스/상태 4종 assert.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { StrategyList } from "@/app/(dashboard)/strategies/_components/strategy-list";
import { EMPTY_CELL } from "@/lib/labels";

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
    latest_backtest: {
      backtest_id: "00000000-0000-4000-8000-000000000999",
      completed_at: "2026-04-14T10:00:00Z",
      metrics: {
        total_return: 0.1234,
        net_profit_abs: 12,
        sharpe_ratio: 1.5,
        max_drawdown: -0.04,
        num_trades: 3,
        total_open_trades: 0,
      },
    },
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

  it("표는 최신 성과 3칸과 백테스트 완료 수 3·0을 그린다", () => {
    mockUseStrategies.mockReturnValue({
      data: {
        items: [
          makeItem({ backtest_count: 3 }),
          makeItem({
            id: "00000000-0000-4000-8000-000000000002",
            name: "Donchian Breakout",
            backtest_count: 0,
          }),
        ],
        total: 2,
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

    const table = screen.getByRole("table", { name: /전략 목록 2개/ });
    expect(table.className).toContain("trades");
    const headers = within(table).getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual([
      "전략명",
      "상태",
      "심볼 · 주기",
      "최근 수익률",
      "MDD",
      "샤프",
      "백테스트",
      "마지막 수정",
      "액션",
    ]);
    expect(within(table).getByTitle("완료된 백테스트 수입니다. 실행 중이거나 실패한 실행은 세지 않습니다.")).toHaveTextContent("백테스트");
    // parse_status ok → "변환 가능" chip done (원시 enum 미노출)
    const row = screen.getByTestId("strategy-row-00000000-0000-4000-8000-000000000001");
    expect(within(row).getByText("변환 가능").className).toBe("chip done");
    expect(within(row).getByText("MA Crossover Strategy").className).toBe("strat-name");
    expect(within(row).getByText("00000000")).toBeTruthy();
    expect(within(row).getByText("12.34%")).toBeTruthy();
    expect(within(row).getByText("-4.00%")).toBeTruthy();
    expect(within(row).getByText("1.50")).toBeTruthy();
    expect(within(row).getByText("3").closest("td")).toHaveClass("num");
    const emptyRow = screen.getByTestId("strategy-row-00000000-0000-4000-8000-000000000002");
    expect(within(emptyRow).getByTitle("아직 백테스트를 실행하지 않았습니다.")).toHaveTextContent("0");
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

  it("완료 실행이 없으면 성과 3칸을 EMPTY_CELL 과 사유로 표기한다", () => {
    mockUseStrategies.mockReturnValue({
      data: {
        items: [makeItem({ latest_backtest: null })],
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
    const row = screen.getByTestId("strategy-row-00000000-0000-4000-8000-000000000001");
    expect(within(row).getAllByTitle("완료 실행 없음")).toHaveLength(3);
    expect(within(row).getAllByText(EMPTY_CELL).length).toBeGreaterThanOrEqual(3);
  });
});

describe("StrategyList — 01 필터 구획 (screen-06 재도입)", () => {
  afterEach(() => {
    cleanup();
    mockUseStrategies.mockReset();
  });

  function makeMulti() {
    return {
      data: {
        items: [
          makeItem({
            id: "00000000-0000-4000-8000-000000000001",
            name: "MA Crossover Strategy",
            symbol: "BTC/USDT",
            updated_at: "2026-04-14T09:32:00Z",
          }),
          makeItem({
            id: "00000000-0000-4000-8000-000000000002",
            name: "RSI Divergence v3",
            symbol: "ETH/USDT",
            parse_status: "unsupported" as const,
            updated_at: "2026-04-13T21:05:00Z",
          }),
          makeItem({
            id: "00000000-0000-4000-8000-000000000003",
            name: "Bollinger MeanRev",
            symbol: "BTC/USDT",
            updated_at: "2026-04-12T10:47:00Z",
          }),
        ],
        total: 3,
        page: 1,
        limit: 20,
        total_pages: 1,
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    };
  }

  it("툴바는 .toolbar/.input/.select 구조로 검색·심볼·정렬 3컨트롤을 그린다", () => {
    mockUseStrategies.mockReturnValue(makeMulti());
    renderList();
    const search = screen.getByTestId("strategy-search");
    expect(search.className).toBe("input");
    expect(search.closest(".toolbar")).toBeTruthy();
    const symbol = screen.getByTestId("strategy-symbol-filter");
    expect(symbol.className).toBe("select");
    // 심볼 옵션은 로드된 데이터에서 실측(BTC/ETH) — 하드코딩 아님.
    const symbolOpts = within(symbol).getAllByRole("option").map((o) => o.textContent);
    expect(symbolOpts).toEqual(["심볼 전체", "BTC/USDT", "ETH/USDT"]);
    const sort = screen.getByTestId("strategy-sort");
    const sortOpts = within(sort).getAllByRole("option").map((o) => o.textContent);
    // unbacked 성과 정렬(수익률/샤프) 미도입 — backed 2종만.
    expect(sortOpts).toEqual(["마지막 수정 순", "이름 순"]);
  });

  it("검색은 전략명·ID 를 클라이언트 사이드로 좁힌다", () => {
    mockUseStrategies.mockReturnValue(makeMulti());
    renderList();
    fireEvent.change(screen.getByTestId("strategy-search"), { target: { value: "bollinger" } });
    const rows = screen.getAllByTestId(/^strategy-row-/);
    expect(rows).toHaveLength(1);
    expect(within(rows[0]!).getByText("Bollinger MeanRev")).toBeTruthy();
  });

  it("심볼 필터는 선택 심볼만 남긴다", () => {
    mockUseStrategies.mockReturnValue(makeMulti());
    renderList();
    fireEvent.change(screen.getByTestId("strategy-symbol-filter"), { target: { value: "ETH/USDT" } });
    const rows = screen.getAllByTestId(/^strategy-row-/);
    expect(rows).toHaveLength(1);
    expect(within(rows[0]!).getByText("RSI Divergence v3")).toBeTruthy();
  });

  it("이름 순 정렬은 로케일 순서로 재배열한다", () => {
    mockUseStrategies.mockReturnValue(makeMulti());
    renderList();
    fireEvent.change(screen.getByTestId("strategy-sort"), { target: { value: "name" } });
    const names = screen
      .getAllByTestId(/^strategy-row-/)
      .map((r) => within(r).getByRole("link", { name: /Strategy|Divergence|MeanRev/ }).textContent);
    expect(names).toEqual(["Bollinger MeanRev", "MA Crossover Strategy", "RSI Divergence v3"]);
  });

  it("검색이 0건이면 빈 상태 + 필터 초기화 CTA 를 그린다", () => {
    mockUseStrategies.mockReturnValue(makeMulti());
    renderList();
    fireEvent.change(screen.getByTestId("strategy-search"), { target: { value: "없는전략" } });
    expect(screen.getByTestId("strategy-empty")).toBeTruthy();
    expect(screen.getByText("필터 초기화")).toBeTruthy();
  });

  it("CSV 내보내기 버튼은 backed 헤더로 blob 을 만든다", () => {
    mockUseStrategies.mockReturnValue(makeMulti());
    const createUrl = vi.fn((_blob: Blob) => "blob:mock");
    const revokeUrl = vi.fn();
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    vi.stubGlobal("URL", { ...URL, createObjectURL: createUrl, revokeObjectURL: revokeUrl });
    renderList();
    fireEvent.click(screen.getByTestId("strategy-export-csv"));
    expect(createUrl).toHaveBeenCalledTimes(1);
    const blob = createUrl.mock.calls[0]![0];
    expect(blob.type).toContain("text/csv");
    expect(clickSpy).toHaveBeenCalledTimes(1);
    clickSpy.mockRestore();
    vi.unstubAllGlobals();
  });
});
