// 트레이딩 코크핏의 WS 미실현 손익 KPI 상태를 검증한다.
import { cleanup, render, screen } from "@testing-library/react";
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
  LiveSessionDetail: () => null,
  LiveSessionForm: () => null,
  LiveSessionList: () => null,
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
});
