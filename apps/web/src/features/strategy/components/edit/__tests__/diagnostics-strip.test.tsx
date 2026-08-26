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
    declaration: null,
    inputs: [],
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

  // [ADR-040] Stage 1 — 종전 이 자리의 테스트는 「스키마에 파라미터 필드가 0건이라
  // 미렌더한다」를 고정하고 있었다. `ParsePreviewResponse.inputs` 가 열리면서 그 근거가
  // 사라졌으므로 아래 3건으로 교체한다(파싱 전 / 선언 0건 / 실데이터).
  it("파싱 결과가 아직 없으면 파라미터 탭은 빈 안내를 그린다", () => {
    mockUsePreviewParse.mockReturnValue({
      data: null,
      isFetching: false,
      isError: false,
      refetch: vi.fn(),
    });
    render(<DiagnosticsStrip strategy={makeStrategy()} />);
    expect(screen.getByTestId("diag-param-empty")).toBeTruthy();
  });

  it("input 선언이 0건이면 「조절할 파라미터가 없다」를 명시한다", () => {
    mockUsePreviewParse.mockReturnValue({
      data: makeResult({ inputs: [] }),
      isFetching: false,
      isError: false,
      refetch: vi.fn(),
    });
    render(<DiagnosticsStrip strategy={makeStrategy()} />);
    expect(screen.getByTestId("diag-param-none")).toBeTruthy();
  });

  it("파라미터 표에 var_name·타입·기본값을 그리고 스윕 가능 여부를 가른다", () => {
    mockUsePreviewParse.mockReturnValue({
      data: makeResult({
        inputs: [
          { input_type: "int", var_name: "length", defval: "14", title: "RSI Length" },
          { input_type: "generic", var_name: "legacy", defval: "7", title: null },
        ],
      }),
      isFetching: false,
      isError: false,
      refetch: vi.fn(),
    });
    render(<DiagnosticsStrip strategy={makeStrategy()} />);
    // 기본 탭은 「파싱」이고 나머지 패널은 hidden 이라 접근성 트리에 없다 — 실제 경로대로 연다.
    fireEvent.click(screen.getByRole("tab", { name: "파라미터" }));

    const table = screen.getByRole("table", { name: "파라미터 2개" });
    const body = table.textContent ?? "";
    // ★var_name 은 override 키다 — 가공되지 않고 원형 그대로 나와야 한다.
    expect(body).toContain("length");
    expect(body).toContain("RSI Length");
    expect(body).toContain("14");

    // ★스윕 불가를 **숨기지 않는다**. 표에서 빠지면 사용자는 파라미터가 없다고 읽는다.
    //   `generic`(v4 무네임스페이스 input)은 BE `_validate_grid_search_pre` 가 거부한다.
    expect(body).toContain("legacy");
    const rows = table.querySelectorAll("tbody tr");
    expect(rows.length).toBe(2);
    expect(rows[0]?.textContent).toContain("가능");
    expect(rows[1]?.textContent).toContain("불가");
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
