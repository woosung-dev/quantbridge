// C 이식(W3-C) 시맨틱 구조 회귀 — 프로토타입 screen-09/10 유래 핵심 클래스가 렌더되는지 assert.
// 시각 정본 충실도는 자동 캐논 게이트가 못 본다(대비·오버플로만). 이 테스트가 구조를 잠근다.

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  GridSearchResult,
  OptimizationRunListResponse,
  OptimizationRunResponse,
} from "@/features/optimizer/schemas";

// ── 훅 목킹 ──────────────────────────────────────────────────────────────────
interface QueryLike<T> {
  data: T | undefined;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

let runsResult: QueryLike<OptimizationRunListResponse>;
let runResult: QueryLike<OptimizationRunResponse>;

vi.mock("@/features/optimizer/hooks", () => ({
  useOptimizationRuns: () => runsResult,
  useOptimizationRun: () => runResult,
}));

vi.mock("@/features/backtest/hooks", () => ({
  useCreateWalkForward: () => ({ mutate: vi.fn(), isPending: false }),
  useStressTest: () => ({ data: undefined, isLoading: false, isError: false, error: null }),
  useBacktests: () => ({ data: { items: [] }, isLoading: false }),
}));

vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

// import AFTER mocks
import { OptimizerRunList } from "../optimizer-run-list";
import { OptimizerRunDetail } from "../optimizer-run-detail";

const UUID = "0f9c41aa-1111-4222-8333-944455556666";
const BACKTEST_UUID = "2f9c41bb-1111-4222-8333-944455556666";

const GRID_RESULT: GridSearchResult = {
  schema_version: 1,
  kind: "grid_search",
  param_names: ["fastLength", "slowLength"],
  param_values: { fastLength: [10, 20, 30], slowLength: [40, 50, 60] },
  cells: [
    {
      param_values: { fastLength: 20, slowLength: 50 },
      sharpe: 1.84,
      total_return: 127.4,
      max_drawdown: -14.6,
      num_trades: 186,
      is_degenerate: false,
      objective_value: 1.84,
    },
    {
      param_values: { fastLength: 20, slowLength: 60 },
      sharpe: 1.61,
      total_return: 108.9,
      max_drawdown: -15.7,
      num_trades: 163,
      is_degenerate: false,
      objective_value: 1.61,
    },
    {
      param_values: { fastLength: 30, slowLength: 60 },
      sharpe: null,
      total_return: 0,
      max_drawdown: 0,
      num_trades: 0,
      is_degenerate: true,
      objective_value: null,
    },
  ],
  objective_metric: "sharpe_ratio",
  direction: "maximize",
  best_cell_index: 0,
};

function completedGridRun(): OptimizationRunResponse {
  return {
    id: UUID,
    user_id: UUID,
    backtest_id: BACKTEST_UUID,
    kind: "grid_search",
    status: "completed",
    param_space: {
      schema_version: 1,
      objective_metric: "sharpe_ratio",
      direction: "maximize",
      max_evaluations: 9,
      parameters: {
        fastLength: { kind: "integer", min: 10, max: 30, step: 10 },
        slowLength: { kind: "integer", min: 40, max: 60, step: 10 },
      },
      genetic_selection_method: null,
    },
    result: GRID_RESULT,
    error_message: null,
    created_at: "2026-04-14T12:41:00+00:00",
    started_at: "2026-04-14T12:41:00+00:00",
    completed_at: "2026-04-14T12:42:00+00:00",
  };
}

function listRow(status: OptimizationRunResponse["status"], idSuffix: string): OptimizationRunResponse {
  return {
    ...completedGridRun(),
    id: `${idSuffix}9c41aa-1111-4222-8333-944455556666`,
    status,
    result: status === "completed" ? GRID_RESULT : null,
  };
}

beforeEach(() => {
  runsResult = { data: undefined, isLoading: false, error: null, refetch: vi.fn() };
  runResult = { data: undefined, isLoading: false, error: null, refetch: vi.fn() };
});

describe("OptimizerRunList — C 시맨틱 구조 (screen-09 02 목록)", () => {
  it("스켈레톤 상태 — .sk 셀 렌더", () => {
    runsResult = { data: undefined, isLoading: true, error: null, refetch: vi.fn() };
    const { container } = render(<OptimizerRunList />);
    expect(screen.getByTestId("optimizer-skeleton")).toBeInTheDocument();
    expect(container.querySelector(".sk.sk-cell")).not.toBeNull();
  });

  it("에러 상태 — state-box failed + 실존 엔드포인트 + HTTP 코드", () => {
    runsResult = {
      data: undefined,
      isLoading: false,
      error: new Error("boom"),
      refetch: vi.fn(),
    };
    const { container } = render(<OptimizerRunList />);
    const box = screen.getByTestId("optimizer-error");
    expect(box.className).toContain("state-box");
    expect(box.className).toContain("failed");
    expect(box).toHaveAttribute("role", "alert");
    expect(container.querySelector(".state-code")?.textContent).toContain(
      "GET /api/v1/optimizer/runs",
    );
    expect(container.querySelector(".state-code")?.textContent).toContain("500");
  });

  it("빈 상태 — state-box(role=status)", () => {
    runsResult = {
      data: { items: [], total: 0, limit: 20, offset: 0, skipped_count: 0 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    const box = render(<OptimizerRunList />).getByTestId("optimizer-empty");
    expect(box.className).toContain("state-box");
    expect(box).toHaveAttribute("role", "status");
  });

  it("데이터 렌더 — table.trades.opt-table + run-id/run-main/run-sub + col-status 칩 + skipped 고지", () => {
    runsResult = {
      data: {
        items: [listRow("completed", "1f"), listRow("queued", "2f")],
        total: 3,
        limit: 20,
        offset: 0,
        skipped_count: 2,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    const { container } = render(<OptimizerRunList />);
    const table = container.querySelector("table.trades.opt-table");
    expect(table).not.toBeNull();
    expect(container.querySelector(".run-id")).not.toBeNull();
    expect(container.querySelector(".run-main")).not.toBeNull();
    expect(container.querySelector(".run-sub")).not.toBeNull();
    // col-status 안 칩(라벨 SSOT 톤 — 원시 enum 아님)
    expect(container.querySelector("td.col-status .chip")).not.toBeNull();
    // skipped 인라인 고지
    expect(screen.getByTestId("optimizer-skipped-warn").className).toContain("notice-inline");
    // 무데이터 셀(대기 행 최고 목표값) title 사유
    const dimTitled = container.querySelector("td.num .dim[title]");
    expect(dimTitled).not.toBeNull();
    // 원시 상태 enum 이 노출되지 않는다
    expect(container.textContent).not.toContain("queued");
    expect(container.textContent).not.toContain("grid_search");
  });
});

describe("OptimizerRunDetail — C 시맨틱 구조 (screen-10)", () => {
  it("완료 grid — .report 헤더 + 상태 칩 + 파라미터 공간 trust-row", () => {
    runResult = { data: completedGridRun(), isLoading: false, error: null, refetch: vi.fn() };
    const { container } = render(<OptimizerRunDetail runId={UUID} />);
    expect(container.querySelector("main.page")).not.toBeNull();
    expect(container.querySelector(".report .report-title")).not.toBeNull();
    expect(container.querySelector(".report-meta .chip")).not.toBeNull();
    // 파라미터 공간은 trust-row 로, key 는 pine 식별자(코드 심볼 — §4.9 예외)
    expect(container.querySelector(".opt-param-space .trust-row")).not.toBeNull();
    expect(container.textContent).toContain("fastLength");
  });

  it("완료 grid — 리더보드 table.trades(row-best + 축퇴 무데이터) + 히트맵 hm-cell 이중 렌더", () => {
    runResult = { data: completedGridRun(), isLoading: false, error: null, refetch: vi.fn() };
    const { container } = render(<OptimizerRunDetail runId={UUID} />);
    // 리더보드 최적 행
    expect(container.querySelector("tr.row-best")).not.toBeNull();
    // 축퇴 셀 무데이터 + title
    const degenTitled = container.querySelector("tr.row-nodata .dim[title]");
    expect(degenTitled).not.toBeNull();
    // KPI row
    expect(container.querySelector(".kpi-row .kpi")).not.toBeNull();
    // 히트맵 이중 렌더 (같은 값)
    expect(container.querySelector("table.hm")).not.toBeNull();
    expect(container.querySelector(".hm-cell.best")).not.toBeNull();
    expect(container.querySelector(".hm-cell.degenerate")).not.toBeNull();
  });

  it("에러 — state-box failed + 상세 엔드포인트", () => {
    runResult = {
      data: undefined,
      isLoading: false,
      error: new Error("nope"),
      refetch: vi.fn(),
    };
    const { container } = render(<OptimizerRunDetail runId={UUID} />);
    expect(container.querySelector(".state-box.failed")).not.toBeNull();
    expect(container.querySelector(".state-code")?.textContent).toContain(
      "GET /api/v1/optimizer/runs",
    );
  });
});
