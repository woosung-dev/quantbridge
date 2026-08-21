// 진단 띠(C 이식 screen-08 §02) 시맨틱 구조 테스트 — §3-6 진짜 탭(tablist+tabpanel) + 판정 KPI.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";

import { DiagnosticsStrip } from "@/features/strategy/components/edit/diagnostics-strip";
import type { ParsePreviewResponse, StrategyResponse } from "@/features/strategy/schemas";

vi.mock("@/features/strategy/edit-store", () => ({
  useEditStore: (sel: (s: { pineSource: string }) => unknown) =>
    sel({ pineSource: "//@version=5" }),
  selectPineSource: (s: { pineSource: string }) => s.pineSource,
}));

const mockUsePreviewParse = vi.fn();
vi.mock("@/features/strategy/hooks", () => ({
  usePreviewParse: (...args: unknown[]) => mockUsePreviewParse(...args),
}));

function makeStrategy(): StrategyResponse {
  return {
    id: "00000000-0000-4000-8000-000000000001",
    name: "MA Crossover Strategy",
    description: null,
    pine_source: "//@version=5",
    pine_version: "v5",
    parse_status: "ok",
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
  };
}

function makeResult(overrides: Partial<ParsePreviewResponse> = {}): ParsePreviewResponse {
  return {
    status: "ok",
    pine_version: "v5",
    warnings: [],
    errors: [],
    entry_count: 2,
    exit_count: 2,
    functions_used: ["ta.sma", "ta.crossover", "strategy.entry"],
    unsupported_builtins: [],
    unsupported_calls: [],
    is_runnable: true,
    ...overrides,
  };
}

describe("DiagnosticsStrip — C 이식 진짜 탭 구조 (§3-6)", () => {
  afterEach(() => {
    cleanup();
    mockUsePreviewParse.mockReset();
  });

  it("role=tablist + tab 3종(파싱/파라미터/지표) + tabpanel 3종을 그린다", () => {
    mockUsePreviewParse.mockReturnValue({
      data: makeResult(),
      isFetching: false,
      isError: false,
      refetch: vi.fn(),
    });
    render(<DiagnosticsStrip strategy={makeStrategy()} />);

    const tablist = screen.getByRole("tablist", { name: "진단 항목" });
    const tabs = within(tablist)
      .getAllByRole("tab")
      .map((t) => t.textContent);
    expect(tabs).toEqual(["파싱", "파라미터", "지표"]);
    // 3 tabpanel 이 실재한다 (오용 아님). 비활성 2개는 hidden 이라 hidden:true 로 조회.
    expect(screen.getAllByRole("tabpanel", { hidden: true }).length).toBe(3);
    // 각 tab 의 aria-controls 가 실제 tabpanel id 를 가리킨다.
    for (const id of ["parse", "param", "indicator"]) {
      expect(document.getElementById(`diag-panel-${id}`)?.getAttribute("role")).toBe("tabpanel");
    }
  });

  it("판정 KPI 는 지원/감지 함수 수를 backed 값으로 그린다 (3/3, 100%)", () => {
    mockUsePreviewParse.mockReturnValue({
      data: makeResult(),
      isFetching: false,
      isError: false,
      refetch: vi.fn(),
    });
    render(<DiagnosticsStrip strategy={makeStrategy()} />);
    expect(screen.getByText("지원 판정")).toBeTruthy();
    expect(screen.getByText("3 / 3")).toBeTruthy();
  });

  it("탭 클릭 시 aria-selected + 패널 hidden 이 전환된다", () => {
    mockUsePreviewParse.mockReturnValue({
      data: makeResult(),
      isFetching: false,
      isError: false,
      refetch: vi.fn(),
    });
    render(<DiagnosticsStrip strategy={makeStrategy()} />);
    const paramTab = screen.getByRole("tab", { name: "파라미터" });
    expect(paramTab.getAttribute("aria-selected")).toBe("false");
    fireEvent.click(paramTab);
    expect(paramTab.getAttribute("aria-selected")).toBe("true");
    expect(document.getElementById("diag-panel-param")?.hasAttribute("hidden")).toBe(false);
    expect(document.getElementById("diag-panel-parse")?.hasAttribute("hidden")).toBe(true);
  });

  it("파라미터 탭은 스키마에 필드가 없어 미렌더 근거 state-box 를 그린다(§4.9)", () => {
    mockUsePreviewParse.mockReturnValue({
      data: makeResult(),
      isFetching: false,
      isError: false,
      refetch: vi.fn(),
    });
    render(<DiagnosticsStrip strategy={makeStrategy()} />);
    expect(screen.getByTestId("diag-param-empty")).toBeTruthy();
  });

  it("파싱 요청 실패 시 파싱 탭에 state-box.failed + 엔드포인트를 노출한다", () => {
    mockUsePreviewParse.mockReturnValue({
      data: null,
      isFetching: false,
      isError: true,
      error: new Error("boom"),
      refetch: vi.fn(),
    });
    render(<DiagnosticsStrip strategy={makeStrategy()} />);
    const box = screen.getByTestId("diag-parse-error");
    expect(box.className).toContain("state-box failed");
  });
});
