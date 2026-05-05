// Sprint 33-A (BL-150 partial) — LiveSessionDetail 통합 테스트.
//
// 목적:
//  - recharts → lightweight-charts 마이그 후 chart 가 정상 mount 되는지 검증.
//  - ErrorBoundary 미발동 (render 가 throw 하지 않음 — Sprint 30 BL-157 currentColor regression 방어).
//  - empty / loaded / equity_curve 분기별 createChart 호출 횟수 검증.
//
// 패턴: ExchangeAccountsPanel 테스트 동일 (Clerk + RQ 구성).

import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import type {
  LiveSession,
  LiveSignalEvent,
  LiveSignalState,
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

vi.mock("../../api", () => ({
  getLiveSessionState: (...args: unknown[]) => stateMock(...args),
  listLiveSessionEvents: (...args: unknown[]) => eventsMock(...args),
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

const EVENT_BASE: Omit<
  LiveSignalEvent,
  "id" | "bar_time" | "sequence_no" | "action"
> = {
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
  schema_version: 1,
  last_strategy_state_report: {},
  last_open_trades_snapshot: {},
  total_closed_trades: 1,
  total_realized_pnl: "12.34",
  equity_curve: [],
  updated_at: "2026-05-01T12:01:00Z",
};

const STATE_WITH_EQUITY: LiveSignalState = {
  ...STATE_NO_EQUITY,
  equity_curve: [
    { timestamp_ms: Date.parse("2026-05-01T12:01:00Z"), cumulative_pnl: "12.34" },
  ],
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
    (
      globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }
    ).ResizeObserver = MockResizeObserver;
  });

  afterEach(() => {
    delete (globalThis as unknown as { ResizeObserver?: unknown })
      .ResizeObserver;
  });

  it("empty events — 안내 텍스트만, chart 미생성", async () => {
    stateMock.mockResolvedValue(STATE_NO_EQUITY);
    eventsMock.mockResolvedValue({ items: [] });

    renderWith(<LiveSessionDetail session={SESSION} />);

    // 안내 문구 등장 확인 (events 영역은 두 군데 — Activity Timeline + Recent Events).
    const empties = await screen.findAllByText(
      /아직 평가된 signal 이 없습니다/,
    );
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
    expect(screen.getByText("98.76")).toBeInTheDocument();
  });
});
