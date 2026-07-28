// Sprint 33-A (BL-150 partial) — LiveSessionDetail 통합 테스트.
//
// 목적:
//  - recharts → lightweight-charts 마이그 후 chart 가 정상 mount 되는지 검증.
//  - ErrorBoundary 미발동 (render 가 throw 하지 않음 — Sprint 30 BL-157 currentColor regression 방어).
//  - empty / loaded / equity_curve 분기별 createChart 호출 횟수 검증.
//
// 패턴: ExchangeAccountsPanel 테스트 동일 (Clerk + RQ 구성).

import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  LiveSession,
  LiveSignalEvent,
  LiveSignalState,
  OutcomeParityResponse,
} from "../../schemas";
import { LiveSessionDetail } from "../live-session-detail";

// --- lightweight-charts mock ---------------------------------------------

interface SeriesSpy {
  setData: ReturnType<typeof vi.fn>;
  applyOptions: ReturnType<typeof vi.fn>;
  setMarkers: ReturnType<typeof vi.fn>;
}

interface ChartSpy {
  addLineSeries: ReturnType<typeof vi.fn>;
  addAreaSeries: ReturnType<typeof vi.fn>;
  removeSeries: ReturnType<typeof vi.fn>;
  applyOptions: ReturnType<typeof vi.fn>;
  remove: ReturnType<typeof vi.fn>;
  timeScale: ReturnType<typeof vi.fn>;
}

const createChartMock = vi.fn();
const chartInstances: ChartSpy[] = [];

vi.mock("lightweight-charts", () => {
  return {
    createChart: (...args: unknown[]) => {
      createChartMock(...args);
      const chart: ChartSpy = {
        addLineSeries: vi.fn(
          (): SeriesSpy => ({
            setData: vi.fn(),
            applyOptions: vi.fn(),
            setMarkers: vi.fn(),
          }),
        ),
        addAreaSeries: vi.fn(
          (): SeriesSpy => ({
            setData: vi.fn(),
            applyOptions: vi.fn(),
            setMarkers: vi.fn(),
          }),
        ),
        removeSeries: vi.fn(),
        applyOptions: vi.fn(),
        remove: vi.fn(),
        timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
      };
      chartInstances.push(chart);
      return chart;
    },
  };
});

// jsdom ResizeObserver mock.
type RoCallback = (entries: Array<{ contentRect: { width: number } }>) => void;
let roInstances: Array<{ cb: RoCallback; targets: Element[] }> = [];

class MockResizeObserver {
  cb: RoCallback;
  targets: Element[] = [];
  constructor(cb: RoCallback) {
    this.cb = cb;
    roInstances.push({ cb, targets: this.targets });
  }
  observe(target: Element) {
    this.targets.push(target);
  }
  unobserve() {}
  disconnect() {
    this.targets = [];
  }
}

// --- Clerk + API mocks ---------------------------------------------------

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({
    userId: "test-user",
    getToken: async () => "test-token",
  }),
}));

// hooks 의 api 호출을 직접 mock — useLiveSessionState / useLiveSessionEvents 가
// 호출하는 api.ts 모듈 함수들을 가짜 응답으로 교체.
const stateMock = vi.fn();
const eventsMock = vi.fn();
const outcomeParityMock = vi.fn();

vi.mock("../../api", () => ({
  getLiveSessionState: (...args: unknown[]) => stateMock(...args),
  listLiveSessionEvents: (...args: unknown[]) => eventsMock(...args),
  getLiveSessionOutcomeParity: (...args: unknown[]) => outcomeParityMock(...args),
  // 사용 안 하지만 hooks.ts 가 import 하므로 stub 필요.
  listLiveSessions: vi.fn(),
  registerLiveSession: vi.fn(),
  deactivateLiveSession: vi.fn(),
}));

// --- fixtures ------------------------------------------------------------

const SESSION: LiveSession = {
  id: "00000000-0000-0000-0000-0000000000aa",
  user_id: "00000000-0000-0000-0000-0000000000bb",
  strategy_id: "00000000-0000-0000-0000-0000000000cc",
  exchange_account_id: "00000000-0000-0000-0000-0000000000dd",
  symbol: "BTCUSDT",
  interval: "5m",
  is_active: true,
  last_evaluated_bar_time: "2026-05-01T12:00:00Z",
  created_at: "2026-05-01T11:00:00Z",
  deactivated_at: null,
};

const EVENT_BASE: Omit<LiveSignalEvent, "id" | "bar_time" | "sequence_no" | "action"> = {
  session_id: SESSION.id,
  direction: "long",
  trade_id: "T1",
  qty: "1",
  comment: "",
  status: "dispatched",
  order_id: null,
  error_message: null,
  retry_count: 0,
  created_at: "2026-05-01T12:00:00Z",
  dispatched_at: "2026-05-01T12:00:00Z",
};

const EVENTS: LiveSignalEvent[] = [
  {
    ...EVENT_BASE,
    id: "00000000-0000-0000-0000-0000000000e1",
    bar_time: "2026-05-01T12:00:00Z",
    sequence_no: 0,
    action: "entry",
  },
  {
    ...EVENT_BASE,
    id: "00000000-0000-0000-0000-0000000000e2",
    bar_time: "2026-05-01T12:01:00Z",
    sequence_no: 0,
    action: "close",
  },
];

const STATE_NO_EQUITY: LiveSignalState = {
  session_id: SESSION.id,
  evaluated: true,
  schema_version: 1,
  last_strategy_state_report: {},
  total_closed_trades: 1,
  total_realized_pnl: "12.34",
  equity_curve: [],
  updated_at: "2026-05-01T12:01:00Z",
};

const STATE_WITH_EQUITY: LiveSignalState = {
  ...STATE_NO_EQUITY,
  equity_curve: [{ timestamp_ms: Date.parse("2026-05-01T12:01:00Z"), cumulative_pnl: "12.34" }],
};

const INACTIVE_SESSION: LiveSession = {
  ...SESSION,
  is_active: false,
  deactivated_at: "2026-05-01T12:02:00Z",
};

const OUTCOME_PARITY_SCOPE: OutcomeParityResponse["session"] = {
  matched_count: 1,
  expected_gross: "10",
  actual_net: "8",
  decomposable_count: 1,
  decomposable_expected_gross: "10",
  execution_gap: "-1",
  cost: "-1",
  decomposable_actual_net: "8",
  actual_gross: "9",
  round_trip_notional: "1000",
  effective_cost_pct_per_leg: "0.1",
  effective_cost_pct_round_trip: "0.2",
  edge_pct_round_trip: "1.6",
  cost_to_edge_ratio: "0.125",
  undecomposed_count: 0,
  undecomposed_net: "0",
  expected_only_count: 0,
  expected_only_gross: "0",
  expected_only_pending_count: 0,
  expected_only_failed_count: 0,
  expected_only_dispatched_count: 0,
  actual_only_count: 0,
  actual_only_net: "0",
  ledger_only_count: 0,
  ledger_only_net: "0",
  inferred_attribution_count: 0,
  match_coverage_pct: "100",
  decomposition_coverage_pct: "100",
  sample_n: 1,
  sample_mean_net: "8",
  sample_sd_net: null,
  sample_required_n: null,
  sample_sufficient: false,
  ratio_sample_n: 1,
  ratio_sample_required_n: null,
  ratio_sample_sufficient: false,
};

const OUTCOME_PARITY_RESPONSE: OutcomeParityResponse = {
  session_id: SESSION.id,
  session: OUTCOME_PARITY_SCOPE,
  strategy: OUTCOME_PARITY_SCOPE,
  unattributed_count: 0,
  inferred_attribution_count: 0,
  ledger_supported: true,
  strategy_session_count: 1,
  assumption: {
    source: "house_default",
    taker_fee_pct: "0.1",
    slippage_pct: "0.05",
    maker_fee_pct: "0.02",
    implied_round_trip_pct: "0.3",
  },
};

// --- helpers -------------------------------------------------------------

function renderWith(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

// --- tests ---------------------------------------------------------------

describe("LiveSessionDetail (Sprint 33-A BL-150 partial)", () => {
  beforeEach(() => {
    createChartMock.mockClear();
    chartInstances.length = 0;
    roInstances = [];
    stateMock.mockReset();
    eventsMock.mockReset();
    outcomeParityMock.mockReset();
    outcomeParityMock.mockResolvedValue(OUTCOME_PARITY_RESPONSE);
    (globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }).ResizeObserver =
      MockResizeObserver;
  });

  afterEach(() => {
    delete (globalThis as unknown as { ResizeObserver?: unknown }).ResizeObserver;
  });

  it("empty events — 안내 텍스트만, chart 미생성", async () => {
    stateMock.mockResolvedValue(STATE_NO_EQUITY);
    eventsMock.mockResolvedValue({ items: [] });

    renderWith(<LiveSessionDetail session={SESSION} />);

    // 안내 문구 등장 확인 (events 영역은 두 군데 — Activity Timeline + Recent Events).
    const empties = await screen.findAllByText(/아직 평가된 signal 이 없습니다/);
    expect(empties.length).toBeGreaterThanOrEqual(1);
    // chart 미생성.
    expect(createChartMock).not.toHaveBeenCalled();
  });

  it("events present, no equity_curve — 1 chart 인스턴스 (counts pane only)", async () => {
    stateMock.mockResolvedValue(STATE_NO_EQUITY);
    eventsMock.mockResolvedValue({ items: EVENTS });

    renderWith(<LiveSessionDetail session={SESSION} />);

    // Activity Timeline chart 가 mount 되기를 기다림.
    await screen.findByTestId("activity-timeline-chart");
    expect(await screen.findByTestId("outcome-parity-panel")).toBeInTheDocument();

    expect(createChartMock).toHaveBeenCalledTimes(1);
    expect(chartInstances).toHaveLength(1);
    // counts pane = entries (main) + closes (benchmark) = 2 line series.
    expect(chartInstances[0]!.addLineSeries).toHaveBeenCalledTimes(2);
  });

  it("events + equity_curve — 2 chart 인스턴스 (counts + equity panes)", async () => {
    stateMock.mockResolvedValue(STATE_WITH_EQUITY);
    eventsMock.mockResolvedValue({ items: EVENTS });

    renderWith(<LiveSessionDetail session={SESSION} />);

    await screen.findByTestId("activity-timeline-chart");
    // equity pane 도 등장.
    await screen.findByTestId("activity-timeline-equity-pane");

    expect(createChartMock).toHaveBeenCalledTimes(2);
    expect(chartInstances).toHaveLength(2);
  });

  it("종료 세션도 데이터를 렌더하고 종료 상태를 표시한다", async () => {
    stateMock.mockResolvedValue(STATE_NO_EQUITY);
    eventsMock.mockResolvedValue({ items: EVENTS });

    renderWith(<LiveSessionDetail session={INACTIVE_SESSION} />);

    expect(await screen.findByText("+12.34")).toBeInTheDocument();
    expect(screen.getByTestId("live-session-ended-badge")).toHaveTextContent("종료된 세션");
    expect(eventsMock).toHaveBeenCalledWith(INACTIVE_SESSION.id, "test-token");
  });

  it("ErrorBoundary 미발동 — render 가 throw 하지 않음 (BL-157 regression 방어)", async () => {
    // Sprint 30 BL-157: lightweight-charts colorStringToRgba 가 "currentColor"
    // 키워드 fallback 으로 throw → AttributionLogoWidget 가 cascade → ErrorBoundary
    // fallback 이 페이지 전체를 깨뜨림. trading-chart wrapper 가 hex 색상 명시
    // 변환했으므로 본 테스트는 render 자체가 예외 없이 완료되는지 확인.
    stateMock.mockResolvedValue(STATE_WITH_EQUITY);
    eventsMock.mockResolvedValue({ items: EVENTS });

    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    try {
      expect(() => {
        renderWith(<LiveSessionDetail session={SESSION} />);
      }).not.toThrow();
      // chart mount 완료 대기 — render 완료 후 effect 안 createChart 호출까지.
      await screen.findByTestId("activity-timeline-chart");
      // React error boundary cascade 가 console.error 로 에러 토스되지 않아야 함.
      // (RQ refetch 경고 등 무관한 warnings 는 허용 — 단 "Uncaught" / "Error: " 패턴 확인).
      const hasReactRenderError = errorSpy.mock.calls.some((call) => {
        const msg = String(call[0] ?? "");
        return (
          msg.includes("React will try to recreate") ||
          msg.includes("Uncaught") ||
          msg.includes("colorStringToRgba")
        );
      });
      expect(hasReactRenderError).toBe(false);
    } finally {
      errorSpy.mockRestore();
    }
  });

  it("session 메타 — 심볼 / closed trades / realized PnL 표시", async () => {
    // total_closed_trades=42 (qty="1" 과 충돌 회피 위해 unique 값).
    stateMock.mockResolvedValue({
      ...STATE_NO_EQUITY,
      total_closed_trades: 42,
      total_realized_pnl: "98.76",
    });
    eventsMock.mockResolvedValue({ items: EVENTS });

    renderWith(<LiveSessionDetail session={SESSION} />);

    expect(await screen.findByText("BTCUSDT")).toBeInTheDocument();
    // closed_trades / realized_pnl 셀은 dl 안에서 unique value.
    const closedCell = await screen.findByText("42");
    expect(closedCell).toBeInTheDocument();
    // Wave0 cockpit: 양수 PnL 은 + prefix + success tone 으로 표시.
    expect(screen.getByText("+98.76")).toBeInTheDocument();
  });

  it("기준 자본은 세션 시작 잔고와 USDT 단위를 표시한다", () => {
    stateMock.mockResolvedValue(STATE_NO_EQUITY);
    eventsMock.mockResolvedValue({ items: [] });

    renderWith(
      <LiveSessionDetail session={{ ...SESSION, equity_baseline_usdt: "1234.5" }} />,
    );

    expect(screen.getByText("기준 자본")).toBeInTheDocument();
    expect(screen.getByTestId("live-session-equity-baseline")).toHaveTextContent("1234.5 USDT");
  });

  it("기준 자본이 null이면 0 대신 자리표를 표시한다", () => {
    stateMock.mockResolvedValue(STATE_NO_EQUITY);
    eventsMock.mockResolvedValue({ items: [] });

    renderWith(<LiveSessionDetail session={{ ...SESSION, equity_baseline_usdt: null }} />);

    // 자리표만 남기고 단위를 붙이지 않는다 — 모르는 값에 USDT 를 붙이면 0 을 아는 척하는 것과 같다.
    const baseline = screen.getByTestId("live-session-equity-baseline");
    expect(baseline.textContent?.trim()).toBe("—");
    expect(baseline).not.toHaveTextContent("USDT");
    expect(baseline).not.toHaveTextContent("0");
  });

  it("BL-458 — 출처 소계가 오면 확정/추정 칩 두 개를 그린다", async () => {
    stateMock.mockResolvedValue({
      ...STATE_NO_EQUITY,
      total_realized_pnl: "-6",
      confirmed_realized_pnl: "-2",
      estimated_realized_pnl: "-4",
      confirmed_closed_trades: 1,
      estimated_closed_trades: 1,
    });
    eventsMock.mockResolvedValue({ items: EVENTS });

    renderWith(<LiveSessionDetail session={SESSION} />);

    // 어휘는 주문 블로터와 같은 SSOT — 두 화면이 다른 말을 하면 안 된다.
    expect(await screen.findByText("거래소 확정")).toBeInTheDocument();
    expect(screen.getByText("추정")).toBeInTheDocument();
    expect(screen.getByText("-2")).toBeInTheDocument();
    expect(screen.getByText("-4")).toBeInTheDocument();
  });

  it("BL-458 — 소계가 없는 구 응답에서는 칩을 그리지 않는다 (부재 ≠ 0)", async () => {
    stateMock.mockResolvedValue(STATE_NO_EQUITY);
    eventsMock.mockResolvedValue({ items: EVENTS });

    renderWith(<LiveSessionDetail session={SESSION} />);

    await screen.findByText("BTCUSDT");
    expect(screen.queryByText("거래소 확정")).not.toBeInTheDocument();
  });

  it("진입 스킵이 없으면 자리표를 표시한다", async () => {
    stateMock.mockResolvedValue(STATE_NO_EQUITY);
    eventsMock.mockResolvedValue({ items: [] });

    renderWith(<LiveSessionDetail session={SESSION} />);

    await waitFor(() => {
      expect(screen.getByTestId("live-session-entry-skips").textContent?.trim()).toBe(
        String.fromCharCode(0x2014),
      );
    });
  });

  it("강제 청산이 없으면 자리표를 표시한다", async () => {
    stateMock.mockResolvedValue(STATE_NO_EQUITY);
    eventsMock.mockResolvedValue({ items: [] });

    renderWith(<LiveSessionDetail session={SESSION} />);

    await waitFor(() => {
      expect(screen.getByTestId("live-session-liquidations").textContent?.trim()).toBe(
        String.fromCharCode(0x2014),
      );
    });
  });

  it("대기 중인 조건부 진입의 방향과 트리거가를 표시한다", async () => {
    stateMock.mockResolvedValue({
      ...STATE_NO_EQUITY,
      last_strategy_state_report: {
        pending_orders: [
          { direction: "long", stop_price: "101.25", target_position: "1" },
          { direction: "short", stop_price: "99.50", target_position: "-1" },
        ],
      },
    });
    eventsMock.mockResolvedValue({ items: [] });

    renderWith(<LiveSessionDetail session={SESSION} />);

    const pendingOrders = await screen.findByTestId("live-session-pending-orders");
    expect(pendingOrders).toHaveTextContent("롱");
    expect(pendingOrders).toHaveTextContent("101.25");
    expect(pendingOrders).toHaveTextContent("숏");
    expect(pendingOrders).toHaveTextContent("99.50");
  });

  it("대기 조건부 진입을 거래소 등재로 주장하지 않는다", async () => {
    // ★출처는 엔진 desired set(reconcile 이전 저장)이라 거래소 등재 여부를 모른다.
    // 목표 수량이 눈금 미만이거나 트리거가 이미 돌파됐으면 계획기가 발주를 걷어내는데
    // 이 목록은 그대로 남는다. "대기 중" 이라고 쓰면 안 나간 주문을 나간 것처럼 보이게
    // 하는 "되는 척" 이 된다 (최종 codex 리뷰 P2).
    stateMock.mockResolvedValue({
      ...STATE_NO_EQUITY,
      last_strategy_state_report: {
        pending_orders: [{ direction: "long", stop_price: "101.25", target_position: "1" }],
      },
    });
    eventsMock.mockResolvedValue({ items: [] });

    renderWith(<LiveSessionDetail session={SESSION} />);

    const pendingOrders = await screen.findByTestId("live-session-pending-orders");
    expect(pendingOrders).toHaveTextContent("전략이 의도한 조건부 진입");
    expect(pendingOrders).not.toHaveTextContent("대기 중인 조건부 진입");
    expect(pendingOrders).toHaveTextContent("거래소 등재 여부는 주문 원장에서 확인");
  });

  it("대기 조건부 진입이 비면 구역을 표시하지 않는다", async () => {
    stateMock.mockResolvedValue({
      ...STATE_NO_EQUITY,
      last_strategy_state_report: { pending_orders: [] },
    });
    eventsMock.mockResolvedValue({ items: [] });

    renderWith(<LiveSessionDetail session={SESSION} />);

    await screen.findByText("BTCUSDT");
    expect(screen.queryByTestId("live-session-pending-orders")).not.toBeInTheDocument();
  });

  it("검증 실패한 대기 조건부 진입은 구역을 표시하지 않는다", async () => {
    stateMock.mockResolvedValue({
      ...STATE_NO_EQUITY,
      last_strategy_state_report: {
        pending_orders: [null, 42, { direction: "long", stop_price: 101 }],
      },
    });
    eventsMock.mockResolvedValue({ items: [] });

    renderWith(<LiveSessionDetail session={SESSION} />);

    await screen.findByText("BTCUSDT");
    expect(screen.queryByTestId("live-session-pending-orders")).not.toBeInTheDocument();
  });

  it("쓰레기 원소는 강제 청산으로 세지 않는다", async () => {
    // 열린 record 스키마라 `null`·숫자가 올 수 있다. 길이만 세면 `[null]` 이
    // "강제 청산 1건" 으로 위장된다 (최종 리뷰 지적).
    stateMock.mockResolvedValue({
      ...STATE_NO_EQUITY,
      last_strategy_state_report: {
        last_bar_liquidations: [null, 42, { id: "L" }],
      },
    });
    eventsMock.mockResolvedValue({ items: [] });

    renderWith(<LiveSessionDetail session={SESSION} />);

    await waitFor(() => {
      expect(
        screen.getByTestId("live-session-liquidations").textContent?.trim(),
      ).toBe(String.fromCharCode(0x2014));
    });
  });

  it("강제 청산 건수와 격리 증거금 고지를 표시한다", async () => {
    // 픽스처는 생산자(`Trade.to_dict()`)가 실제로 주는 형태를 쓴다.
    stateMock.mockResolvedValue({
      ...STATE_NO_EQUITY,
      last_strategy_state_report: {
        last_bar_liquidations: [
          { id: "L", direction: "long", qty: 1, liquidated: true },
          { id: "S", direction: "short", qty: 2, liquidated: true },
        ],
      },
    });
    eventsMock.mockResolvedValue({ items: [] });

    renderWith(<LiveSessionDetail session={SESSION} />);

    await waitFor(() => {
      expect(screen.getByTestId("live-session-liquidations")).toHaveTextContent("2건");
    });
    expect(
      screen.getByText(
        "증거금 부족 시 시뮬레이터가 청산으로 판정해 청산 주문을 냅니다. 격리 증거금 기준이며 거래소의 실제 청산과 다를 수 있습니다.",
      ),
    ).toBeInTheDocument();
  });

  it("진입 스킵 사유별 한국어 라벨과 건수를 표시한다", async () => {
    stateMock.mockResolvedValue({
      ...STATE_NO_EQUITY,
      last_strategy_state_report: {
        last_bar_entry_skips: [
          { reason: "margin_insufficient" },
          { reason: "margin_insufficient" },
          { reason: "non_finite_qty" },
          { reason: "pyramiding_cap" },
          { reason: "session_closed" },
          { reason: "unexpected_reason" },
        ],
      },
    });
    eventsMock.mockResolvedValue({ items: [] });

    renderWith(<LiveSessionDetail session={SESSION} />);

    await waitFor(() => {
      expect(screen.getByTestId("live-session-entry-skips")).toHaveTextContent("증거금 부족 2건");
    });
    const entrySkips = screen.getByTestId("live-session-entry-skips");
    expect(entrySkips).toHaveTextContent("증거금 부족 2건");
    expect(entrySkips).toHaveTextContent("수량 계산 불가 1건");
    expect(entrySkips).toHaveTextContent("추가 진입 한도 1건");
    expect(entrySkips).toHaveTextContent("거래 시간대 밖 1건");
    expect(entrySkips).toHaveTextContent("unexpected_reason 1건");
  });

  it("증거금 부족 스킵에만 gross 자본 고지를 표시한다", async () => {
    stateMock.mockResolvedValue({
      ...STATE_NO_EQUITY,
      last_strategy_state_report: {
        last_bar_entry_skips: [{ reason: "margin_insufficient" }],
      },
    });
    eventsMock.mockResolvedValue({ items: [] });

    renderWith(<LiveSessionDetail session={SESSION} />);

    expect(
      await screen.findByText("증거금 판정은 수수료·슬리피지를 차감하기 전 자본으로 합니다."),
    ).toBeInTheDocument();
  });
});
