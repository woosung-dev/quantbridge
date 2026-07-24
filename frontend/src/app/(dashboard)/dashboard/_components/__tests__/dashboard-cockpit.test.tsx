// 워크스페이스 대시보드 코크핏 테스트 (S7) — 실행 표 4상태 + 정직성 규율.
// 훅은 데이터 페치를 격리하려 mock 한다 (dashboard-shell.test.tsx 관례). TradingChart 는
// lightweight-charts 의존을 피해 스텁으로 갈아끼운다.

import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const useLiveSessionsMock = vi.fn();
const useLiveSessionsAggregateMock = vi.fn();
const useUnrealizedPnlEstimateMock = vi.fn();
const useExchangeAccountsMock = vi.fn();
const useStrategiesMock = vi.fn();
const useBacktestsMock = vi.fn();
const useOptimizationRunsMock = vi.fn();

vi.mock("@/features/live-sessions", () => ({
  useLiveSessions: () => useLiveSessionsMock(),
  useLiveSessionsAggregate: () => useLiveSessionsAggregateMock(),
  useUnrealizedPnlEstimate: () => useUnrealizedPnlEstimateMock(),
}));
vi.mock("@/features/strategy/hooks", () => ({
  useStrategies: () => useStrategiesMock(),
}));
vi.mock("@/features/backtest/hooks", () => ({
  useBacktests: () => useBacktestsMock(),
}));
vi.mock("@/features/optimizer/hooks", () => ({
  useOptimizationRuns: () => useOptimizationRunsMock(),
}));
vi.mock("@/features/trading", () => ({
  useExchangeAccounts: () => useExchangeAccountsMock(),
}));
vi.mock("@/components/charts/trading-chart", () => ({
  TradingChart: (props: { ariaLabel: string }) => (
    <div data-testid="mock-trading-chart" aria-label={props.ariaLabel} />
  ),
}));

import { DashboardCockpit } from "../dashboard-cockpit";

// --- fixtures -------------------------------------------------------------

const SESSIONS = {
  data: {
    items: [
      { id: "s1", is_active: true },
      { id: "s2", is_active: false },
    ],
  },
};

const AGG_POPULATED = {
  totalRealizedPnl: 142.18,
  totalClosedTrades: 7,
  mergedEquityCurve: [
    { time: 1700000000, value: 0 },
    { time: 1700003600, value: 80 },
    { time: 1700007200, value: 142.18 },
  ],
  populatedSessions: 1,
  isLoading: false,
  isError: false,
  isPending: false,
};

const AGG_EMPTY = {
  totalRealizedPnl: 0,
  totalClosedTrades: 0,
  mergedEquityCurve: [],
  populatedSessions: 0,
  isLoading: false,
  isError: false,
  isPending: false,
};

const STRATEGIES = {
  data: {
    total: 12,
    items: [
      {
        id: "strat-1",
        name: "MA Crossover Strategy",
        symbol: "BTC/USDT",
        timeframe: "1h",
        tags: ["trend"],
        updated_at: "2026-04-14T21:07:00Z",
        latest_backtest: {
          backtest_id: "run-2f9c41aa",
          completed_at: "2026-04-14T21:20:00Z",
          metrics: { total_return: 0.1234, sharpe_ratio: 1.5 },
        },
      },
      {
        id: "strat-2",
        name: "Donchian Breakout",
        symbol: null,
        timeframe: null,
        tags: [],
        updated_at: "2026-04-13T11:05:00Z",
        latest_backtest: null,
      },
    ],
  },
  isLoading: false,
  isError: false,
  error: null,
  refetch: vi.fn(),
};

const OPTIMIZATIONS = {
  data: {
    items: [
      {
        id: "opt-c268af00",
        backtest_id: "run-2f9c41aa",
        strategy_id: "strat-1",
        backtest_symbol: "BTC/USDT",
        backtest_timeframe: "1h",
        kind: "grid_search",
        status: "completed",
        param_space: {},
        created_at: "2026-04-14T21:06:00Z",
      },
    ],
  },
  isLoading: false,
  isError: false,
  error: null,
  refetch: vi.fn(),
};

const BACKTESTS = {
  data: {
    total: 48,
    items: [
      {
        id: "run-2f9c41aa",
        strategy_id: "strat-1",
        symbol: "BTC/USDT",
        timeframe: "1h",
        period_start: "2024-01-01T00:00:00Z",
        period_end: "2026-04-14T00:00:00Z",
        status: "completed",
        created_at: "2026-04-14T21:07:00Z",
        completed_at: "2026-04-14T21:20:00Z",
      },
      {
        id: "run-c268af00",
        strategy_id: "strat-1",
        symbol: "ETH/USDT",
        timeframe: "4h",
        period_start: "2024-06-01T00:00:00Z",
        period_end: "2026-04-14T00:00:00Z",
        status: "running",
        created_at: "2026-04-14T21:04:00Z",
        completed_at: null,
      },
      {
        id: "run-5b770000",
        strategy_id: "strat-2",
        symbol: "BTC/USDT",
        timeframe: "4h",
        period_start: "2025-01-01T00:00:00Z",
        period_end: "2026-04-14T00:00:00Z",
        status: "failed",
        created_at: "2026-04-13T11:05:00Z",
        completed_at: "2026-04-13T11:06:00Z",
      },
    ],
  },
  isLoading: false,
  isError: false,
  error: null,
  refetch: vi.fn(),
};

function setDefaults() {
  useLiveSessionsMock.mockReturnValue(SESSIONS);
  useLiveSessionsAggregateMock.mockReturnValue(AGG_POPULATED);
  useUnrealizedPnlEstimateMock.mockReturnValue({
    total: -3.2,
    isEstimating: false,
    latestTs: 1_720_000_000_000,
  });
  useExchangeAccountsMock.mockReturnValue({ data: [{ id: "acc-1" }] });
  useStrategiesMock.mockReturnValue(STRATEGIES);
  useBacktestsMock.mockReturnValue(BACKTESTS);
  useOptimizationRunsMock.mockReturnValue(OPTIMIZATIONS);
}

beforeEach(() => {
  vi.clearAllMocks();
  setDefaults();
});

describe("DashboardCockpit — 헤더·KPI 정직성", () => {
  it("워크스페이스 리포트 헤더와 4개 KPI 를 스키마 값으로 그린다", () => {
    render(<DashboardCockpit />);
    expect(screen.getByRole("heading", { level: 1, name: "워크스페이스" })).toBeInTheDocument();
    // KPI 값: 전략 total 12, 백테스트 total 48 (목록 쿼리 .total 파생).
    expect(screen.getByTestId("kpi-strategies")).toHaveTextContent("12");
    expect(screen.getByTestId("kpi-backtests")).toHaveTextContent("48");
    expect(screen.getByTestId("kpi-sessions")).toHaveTextContent("1");
    // 손익 KPI 는 "실현" 이라고 못박는다. 프로토타입의 "데모 미실현 손익" 라벨은
    // 스키마에 미실현 필드가 없어 쓰지 않는다 (KPI 라벨로 노출 금지).
    expect(screen.getByText("데모 실현 손익 · 합산")).toBeInTheDocument();
    expect(screen.queryByText("데모 미실현 손익")).not.toBeInTheDocument();
    // 실현 손익 값은 부호 + 배율 없는 값.
    expect(screen.getByTestId("kpi-pnl")).toHaveTextContent("+142.18");
    expect(screen.getByTestId("kpi-pnl").parentElement).toHaveTextContent("미실현(추정) -3.20");
  });

  it("거래소 연결 수를 리포트 칩에 정직하게 표기한다", () => {
    render(<DashboardCockpit />);
    expect(screen.getByText("거래소 1개 연결")).toBeInTheDocument();
    expect(screen.getByText("활성 세션 1")).toBeInTheDocument();
  });
});

describe("DashboardCockpit — 손익 KPI 정직성 (StatValue 규율)", () => {
  it("세션별 state 집계가 실패하면 kpi-pnl 을 성공-0 이 아니라 '확인 불가'로 그린다", () => {
    // 합산 손익은 세션별 state 조회 합이라, 하나라도 실패하면 +0.00 처럼 그리면 거짓 정상.
    useLiveSessionsAggregateMock.mockReturnValue({ ...AGG_POPULATED, isError: true });
    render(<DashboardCockpit />);
    const pnl = screen.getByTestId("kpi-pnl");
    expect(pnl).toHaveTextContent("확인 불가");
    expect(pnl).not.toHaveTextContent("+142.18");
  });

  it("세션 목록 조회가 실패하면(활성 세션 미상) kpi-pnl 도 '확인 불가'로 전파한다", () => {
    // 어떤 세션을 합산할지 모르는 상태 → 손익을 0 으로 단정하지 않는다.
    useLiveSessionsMock.mockReturnValue({ ...SESSIONS, isError: true });
    useLiveSessionsAggregateMock.mockReturnValue(AGG_EMPTY);
    render(<DashboardCockpit />);
    expect(screen.getByTestId("kpi-pnl")).toHaveTextContent("확인 불가");
  });

  it("집계가 아직 미수신이면 kpi-pnl 을 '불러오는 중'으로 그린다", () => {
    useLiveSessionsAggregateMock.mockReturnValue({
      ...AGG_EMPTY,
      isPending: true,
    });
    render(<DashboardCockpit />);
    expect(screen.getByTestId("kpi-pnl")).toHaveTextContent("불러오는 중");
  });
});

describe("DashboardCockpit — 최근 실행 원장", () => {
  it("백테스트와 최적화를 시간순으로 합치고 유형 라벨과 성과를 정직하게 그린다", () => {
    render(<DashboardCockpit />);
    expect(screen.getByTestId("run-row-run-2f9c41aa")).toBeInTheDocument();
    expect(screen.getByTestId("run-row-opt-c268af00")).toBeInTheDocument();
    expect(within(screen.getByTestId("run-row-run-2f9c41aa")).getByText("백테스트")).toBeInTheDocument();
    expect(within(screen.getByTestId("run-row-opt-c268af00")).getByText("최적화")).toBeInTheDocument();
    // 상태 칩은 S4 라벨(완료/실행 중/실패)로만 나온다.
    expect(screen.getAllByText("완료").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("실행 중")).toBeInTheDocument();
    expect(screen.getByText("실패")).toBeInTheDocument();
    // 원시 enum 문자열은 텍스트로 노출되지 않는다.
    expect(screen.queryByText("completed")).not.toBeInTheDocument();
    expect(screen.queryByText("running")).not.toBeInTheDocument();
    // 전략명은 id → name 매핑으로 나온다.
    expect(screen.getAllByText("MA Crossover Strategy").length).toBeGreaterThan(0);
    const optimizerRow = screen.getByTestId("run-row-opt-c268af00");
    expect(within(optimizerRow).getAllByTitle("결과는 최적화 상세에서 확인")).toHaveLength(2);
  });

  it("loading — 스켈레톤을 그린다", () => {
    useBacktestsMock.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    useOptimizationRunsMock.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<DashboardCockpit />);
    expect(screen.getByTestId("runs-skeleton")).toBeInTheDocument();
  });

  it("한 원장 실패는 자체 확인 불가 칩만 표시하고 다른 원장을 유지한다", () => {
    useBacktestsMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("boom"),
      refetch: vi.fn(),
    });
    render(<DashboardCockpit />);
    expect(screen.getByText("백테스트 확인 불가")).toBeInTheDocument();
    expect(screen.getByTestId("run-row-opt-c268af00")).toBeInTheDocument();
    expect(screen.queryByTestId("runs-error")).not.toBeInTheDocument();
  });

  it("두 원장이 모두 비면 빈 상태 박스를 그린다", () => {
    useBacktestsMock.mockReturnValue({
      data: { total: 0, items: [] },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    useOptimizationRunsMock.mockReturnValue({
      data: { items: [] },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<DashboardCockpit />);
    expect(screen.getByTestId("runs-empty")).toBeInTheDocument();
    expect(screen.getByText("아직 실행한 작업이 없습니다.")).toBeInTheDocument();
  });
});

describe("DashboardCockpit — 전략 §04 수명주기 칩 미렌더", () => {
  it("전략별 최근 성과를 그리되 배포됨/검증됨/초안 칩은 그리지 않는다", () => {
    render(<DashboardCockpit />);
    expect(screen.getByTestId("strategy-row-strat-1")).toBeInTheDocument();
    // 스키마에 없는 수명주기 라벨은 어디에도 없다 (캐논 §4.9).
    expect(screen.queryByText("배포됨")).not.toBeInTheDocument();
    expect(screen.queryByText("검증됨")).not.toBeInTheDocument();
    expect(screen.queryByText("초안")).not.toBeInTheDocument();
    expect(within(screen.getByTestId("strategy-row-strat-1")).getByText("12.34%")).toBeInTheDocument();
    expect(within(screen.getByTestId("strategy-row-strat-1")).getByText("1.50")).toBeInTheDocument();
    // 심볼이 null 인 전략은 무데이터 표기(EMPTY_CELL)로 떨어진다.
    expect(screen.getByTestId("strategy-row-strat-2")).toBeInTheDocument();
    expect(
      within(screen.getByTestId("strategy-row-strat-1")).getByRole("link", {
        name: "MA Crossover Strategy",
      }),
    ).toHaveAttribute("href", "/strategies/strat-1/edit");
  });
});

describe("DashboardCockpit — 자산 곡선 4상태 연동", () => {
  it("곡선이 있으면 차트 스텁을 렌더한다", () => {
    render(<DashboardCockpit />);
    expect(screen.getByTestId("mock-trading-chart")).toBeInTheDocument();
  });

  it("곡선이 없고 로딩도 아니면 빈 상태 박스를 그린다", () => {
    useLiveSessionsAggregateMock.mockReturnValue(AGG_EMPTY);
    render(<DashboardCockpit />);
    expect(screen.getByTestId("equity-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("mock-trading-chart")).not.toBeInTheDocument();
  });

  it("집계가 로딩 중이고 곡선이 없으면 스켈레톤을 그린다", () => {
    useLiveSessionsAggregateMock.mockReturnValue({ ...AGG_EMPTY, isLoading: true });
    render(<DashboardCockpit />);
    expect(screen.getByTestId("equity-loading")).toBeInTheDocument();
  });
});
