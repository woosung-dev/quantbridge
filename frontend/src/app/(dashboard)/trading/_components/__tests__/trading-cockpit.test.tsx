// 트레이딩 코크핏의 WS 미실현 손익 KPI 상태를 검증한다.
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const useLiveSessionsMock = vi.fn();
const useUnrealizedPnlEstimateMock = vi.fn();
const useStrategiesMock = vi.fn();
const useExchangeAccountsMock = vi.fn();
const useKillSwitchEventsMock = vi.fn();

// BL-664 — 종전 mock 은 렌더마다 **새 객체**를 돌려줘서 무엇으로 무효화했는지 검증할 수 없었다.
// 모듈 레벨 안정 spy 로 바꾼다.
const invalidateQueriesMock = vi.fn();
vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({ invalidateQueries: invalidateQueriesMock }),
}));
vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ userId: "user-1", isSignedIn: true, getToken: async () => "t" }),
}));
// ★키 팩토리는 흉내내지 않고 **진짜**를 쓴다 — query-keys 는 의존성 없는 leaf 라 배럴을 끌지 않는다.
// 흉내내면 팩토리가 바뀌어도 이 시험이 초록이 된다.
vi.mock("@/features/live-sessions", async () => ({
  liveSessionKeys: (await import("@/features/live-sessions/query-keys")).liveSessionKeys,
  LiveSessionDetail: () => <div data-testid="mock-detail" />,
  LiveSessionForm: () => null,
  LiveSessionList: ({
    onSelect,
  }: {
    onSelect?: (session: { id: string; is_active?: boolean }) => void;
  }) => (
    <>
      <button
        type="button"
        data-testid="mock-live-session-select"
        onClick={() => onSelect?.({ id: "session-1", is_active: true })}
      >
        세션 선택
      </button>
      <button
        type="button"
        data-testid="mock-inactive-live-session-select"
        onClick={() => onSelect?.({ id: "inactive-session", is_active: false })}
      >
        종료 세션 선택
      </button>
    </>
  ),
  LiveSessionTable: () => null,
  useLiveSessions: () => useLiveSessionsMock(),
  useUnrealizedPnlEstimate: () => useUnrealizedPnlEstimateMock(),
}));
vi.mock("@/features/strategy/hooks", async () => ({
  strategyKeys: (await import("@/features/strategy/query-keys")).strategyKeys,
  useStrategies: () => useStrategiesMock(),
}));
vi.mock("@/features/trading", async () => ({
  tradingKeys: (await import("@/features/trading/query-keys")).tradingKeys,
  ExchangeAccountsPanel: () => null,
  KillSwitchPanel: () => null,
  OrdersPanel: () => null,
  useExchangeAccounts: () => useExchangeAccountsMock(),
  useKillSwitchEvents: () => useKillSwitchEventsMock(),
}));
vi.mock("../kill-switch-banner", () => ({ KillSwitchBanner: () => null }));
vi.mock("../account-balance-section", () => ({ AccountBalanceSection: () => null }));
vi.mock("../open-positions-table", () => ({ OpenPositionsTable: () => null }));
const accountPositionsProps = vi.fn();
vi.mock("../account-positions-table", () => ({
  AccountPositionsTable: (props: { accounts: readonly { id: string }[] }) => {
    accountPositionsProps(props);
    return null;
  },
}));
vi.mock("../session-diagnostics", () => ({ SessionDiagnostics: () => null }));

import { TradingCockpit } from "../trading-cockpit";

function setDefaults() {
  // BL-533 — 코크핏은 `useLiveSessions(true)` 를 쓴다. 그 응답에는 **비활성 세션도 들어 있다**.
  // 종전 mock 은 활성 1건만 돌려줘서 `include_inactive=false` 를 흉내내고 있었고, 그래서
  // 「종료 세션 선택」테스트가 `selectedInactiveSession` 미러 state 덕에만 통과했다.
  // 미러를 지우려면 mock 이 먼저 실제 쿼리를 닮아야 한다.
  useLiveSessionsMock.mockReturnValue({
    data: {
      items: [
        { id: "session-1", is_active: true },
        { id: "inactive-session", is_active: false },
      ],
    },
    isError: false,
    isPending: false,
  });
  useStrategiesMock.mockReturnValue({ data: { items: [] } });
  useExchangeAccountsMock.mockReturnValue({ data: [], isError: false, isPending: false });
  useKillSwitchEventsMock.mockReturnValue({
    data: { items: [] },
    isError: false,
    isPending: false,
  });
  useUnrealizedPnlEstimateMock.mockReturnValue({
    total: null,
    isEstimating: true,
    latestTs: null,
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-24T00:00:20.000Z"));
  vi.clearAllMocks();
  setDefaults();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("TradingCockpit — 미실현 손익 추정 KPI", () => {
  it("mark 미수신이면 시세 수신 대기를 그린다", () => {
    render(<TradingCockpit />);

    expect(screen.getByText("미실현 손익 · 추정")).toBeInTheDocument();
    expect(screen.getByTestId("kpi-unrealized-pnl")).toHaveTextContent("시세 수신 대기");
    expect(screen.queryByText("총 세션")).not.toBeInTheDocument();
  });

  it("추정값을 부호·소수 두 자리 USDT로 그린다", () => {
    useUnrealizedPnlEstimateMock.mockReturnValue({
      total: 12.3,
      isEstimating: false,
      latestTs: Date.now(),
    });
    render(<TradingCockpit />);

    expect(screen.getByTestId("kpi-unrealized-pnl")).toHaveTextContent("+12.30 USDT");
  });

  it("15초를 초과한 epoch-ms ticker에 시세 지연 배지를 그린다", () => {
    useUnrealizedPnlEstimateMock.mockReturnValue({
      total: -4.5,
      isEstimating: false,
      latestTs: Date.now() - 15_001,
    });
    render(<TradingCockpit />);

    expect(screen.getByTestId("kpi-unrealized-pnl")).toHaveTextContent("-4.50 USDT");
    expect(screen.getByText("시세 지연")).toBeInTheDocument();
  });

  it("새 §02·§03을 넣고 기존 섹션을 §08까지 순서대로 번호 매긴다", () => {
    render(<TradingCockpit />);

    expect(screen.getByRole("region", { name: "계좌 잔고" })).toHaveTextContent("02 계좌 잔고");
    expect(screen.getByRole("region", { name: "열린 포지션" })).toHaveTextContent("03 열린 포지션");
    expect(screen.getByRole("region", { name: "리스크 가드" })).toHaveTextContent("04 리스크 가드");
    expect(screen.getByRole("region", { name: "진단" })).toHaveTextContent("08 진단");
  });

  it("선택한 세션이 목록에서 사라지면 중단 안내를 보여준다", () => {
    const { rerender } = render(<TradingCockpit />);

    fireEvent.click(screen.getByTestId("mock-live-session-select"));
    useLiveSessionsMock.mockReturnValue({
      data: { items: [] },
      isError: false,
      isPending: false,
    });
    rerender(<TradingCockpit />);

    expect(screen.getByTestId("live-session-stopped-notice")).toBeInTheDocument();
    expect(screen.queryByTestId("mock-detail")).not.toBeInTheDocument();
  });

  it("목록에 남아 있으면 상세를 보여준다", () => {
    render(<TradingCockpit />);

    fireEvent.click(screen.getByTestId("mock-live-session-select"));

    expect(screen.getByTestId("mock-detail")).toBeInTheDocument();
    expect(screen.queryByTestId("live-session-stopped-notice")).not.toBeInTheDocument();
  });

  it("최근 종료 세션을 선택해도 같은 상세 패널을 보여준다", () => {
    render(<TradingCockpit />);

    fireEvent.click(screen.getByTestId("mock-inactive-live-session-select"));

    expect(screen.getByTestId("mock-detail")).toBeInTheDocument();
    expect(screen.queryByTestId("live-session-stopped-notice")).not.toBeInTheDocument();
  });

  // BL-533 — 위 테스트가 **무엇 덕에** 통과하는지 못 박는다.
  // 미러 state 를 지운 뒤로 종료 세션 상세는 오직 `useLiveSessions(true)` 가 비활성을
  // 실어 오기 때문에 열린다. 쿼리가 활성만 돌려주도록 되돌아가면(=`useLiveSessions()`)
  // 같은 클릭이 상세가 아니라 중단 안내로 떨어진다. 이 대조가 없으면 위 테스트는
  // 「종료 세션이 목록에 있든 없든 통과」로 읽혀 판별력이 사라진다.
  it("쿼리가 활성만 실어 오면 같은 클릭이 중단 안내로 떨어진다 (미러 없음의 증거)", () => {
    useLiveSessionsMock.mockReturnValue({
      data: { items: [{ id: "session-1", is_active: true }] },
      isError: false,
      isPending: false,
    });
    render(<TradingCockpit />);

    fireEvent.click(screen.getByTestId("mock-inactive-live-session-select"));

    expect(screen.getByTestId("live-session-stopped-notice")).toBeInTheDocument();
    expect(screen.queryByTestId("mock-detail")).not.toBeInTheDocument();
  });

  it("★계정 잔여 포지션 표에 활성 세션이 아니라 **등록된 모든 계정**을 넘긴다", () => {
    // BL-498 의 핵심 배선. 활성 세션 기준으로 좁히면 세션 0건일 때 잔여 노출이
    // 다시 화면에서 사라진다 — 그게 이 기능이 존재하는 이유다.
    useLiveSessionsMock.mockReturnValue({
      data: { items: [] },
      isError: false,
      isPending: false,
    });
    useExchangeAccountsMock.mockReturnValue({
      data: [
        { id: "acc-1", mode: "demo", label: "데모 1" },
        { id: "acc-2", mode: "demo", label: "데모 2" },
      ],
      isError: false,
      isPending: false,
    });
    accountPositionsProps.mockClear();

    render(<TradingCockpit />);

    const last = accountPositionsProps.mock.calls.at(-1)?.[0];
    expect(last.accounts.map((a: { id: string }) => a.id)).toEqual(["acc-1", "acc-2"]);
  });

  // --- BL-663 — 5초 틱의 재조정 범위 ---------------------------------------
  // `AccountPositionsTable` 은 memo 가 없으므로 코크핏이 재렌더되면 반드시 다시 호출된다.
  // ⇒ 그 호출 수가 곧 「코크핏이 재조정됐나」의 대리 측정이다.
  it("★5초 틱이 코크핏 §01~§08 을 재조정하지 않는다 (KPI leaf 안에 갇혔다)", () => {
    render(<TradingCockpit />);
    const before = accountPositionsProps.mock.calls.length;
    expect(before).toBeGreaterThan(0); // 대리 측정이 살아 있음을 먼저 확인한다

    act(() => {
      vi.advanceTimersByTime(15_000); // 5초 틱 3회분
    });

    expect(accountPositionsProps.mock.calls.length).toBe(before);
    // 그러면서 KPI 자체는 계속 그려진다.
    expect(screen.getByTestId("kpi-unrealized-pnl")).toBeInTheDocument();
  });

  // --- BL-664 — 새로고침의 무효화 범위 ------------------------------------
  // ★네 번째 도메인 `alert-rules` 는 codex 적대 리뷰가 잡았다 — 첫 판은 셋만 무효화했고
  //   §08 `SessionDiagnostics` 의 `useAlertRules`(`alert-rules/hooks.ts`)가 빠져 있었다.
  //   종전 무필터 호출은 그것도 갱신했으므로 빠뜨리면 **기능이 깨진다**. 도메인이 늘면 여기에 더해라.
  it("★새로고침이 이 화면의 네 도메인만 무효화한다 (앱 전체 캐시가 아니라)", async () => {
    const { liveSessionKeys } = await import("@/features/live-sessions/query-keys");
    const { tradingKeys } = await import("@/features/trading/query-keys");
    const { strategyKeys } = await import("@/features/strategy/query-keys");
    const { alertRuleKeys } = await import("@/features/alert-rules/query-keys");

    render(<TradingCockpit />);
    invalidateQueriesMock.mockClear();
    fireEvent.click(screen.getByRole("button", { name: /새로고침/ }));

    // ⑴ 무필터 호출이 0회여야 한다 — 이것이 [BL-664] 의 결함 자체다.
    expect(invalidateQueriesMock.mock.calls.every((c) => c[0]?.queryKey !== undefined)).toBe(true);

    // ⑵ 정확히 세 도메인 루트. 팩토리 출력과 대조하므로 키가 바뀌면 이 시험이 깨진다.
    const keys = invalidateQueriesMock.mock.calls.map((c) => c[0].queryKey);
    expect(keys).toEqual([
      tradingKeys.all("user-1"),
      liveSessionKeys.all("user-1"),
      strategyKeys.all("user-1"),
      alertRuleKeys.all("user-1"),
    ]);

    // ⑶ 음성 대조 — 백테스트·옵티마이저 루트는 어느 호출에도 안 걸린다.
    const roots = keys.map((k) => k[0]);
    expect(roots).not.toContain("backtests");
    expect(roots).not.toContain("optimizations");
  });
});
