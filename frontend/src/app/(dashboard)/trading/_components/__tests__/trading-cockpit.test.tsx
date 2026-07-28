// 트레이딩 코크핏의 WS 미실현 손익 KPI 상태를 검증한다.
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const useLiveSessionsMock = vi.fn();
const useUnrealizedPnlEstimateMock = vi.fn();
const useStrategiesMock = vi.fn();
const useExchangeAccountsMock = vi.fn();
const useKillSwitchEventsMock = vi.fn();

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));
vi.mock("@/features/live-sessions", () => ({
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
vi.mock("@/features/strategy/hooks", () => ({
  useStrategies: () => useStrategiesMock(),
}));
vi.mock("@/features/trading", () => ({
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
  useLiveSessionsMock.mockReturnValue({
    data: { items: [{ id: "session-1", is_active: true }] },
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
});
