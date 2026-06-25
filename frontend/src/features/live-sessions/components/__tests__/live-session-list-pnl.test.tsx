// 세션 리스트 PnL 배지 — useLiveSessionState 재사용 surfacing 검증.
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { LiveSession, LiveSignalState } from "../../schemas";
import { LiveSessionList } from "../live-session-list";

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ userId: "test-user", getToken: async () => "test-token" }),
}));

const stateMock = vi.fn();
const listMock = vi.fn();
vi.mock("../../api", () => ({
  getLiveSessionState: (...a: unknown[]) => stateMock(...a),
  listLiveSessions: (...a: unknown[]) => listMock(...a),
  listLiveSessionEvents: vi.fn(),
  registerLiveSession: vi.fn(),
  deactivateLiveSession: vi.fn(),
}));

const SESSION: LiveSession = {
  id: "00000000-0000-0000-0000-0000000000aa",
  user_id: "00000000-0000-0000-0000-0000000000bb",
  strategy_id: "00000000-0000-0000-0000-0000000000cc",
  exchange_account_id: "00000000-0000-0000-0000-0000000000dd",
  symbol: "BTCUSDT",
  interval: "5m",
  is_active: true,
  last_evaluated_bar_time: null,
  created_at: "2026-05-01T11:00:00Z",
  deactivated_at: null,
};

const STATE: LiveSignalState = {
  session_id: SESSION.id,
  schema_version: 1,
  last_strategy_state_report: {},
  last_open_trades_snapshot: {},
  total_closed_trades: 3,
  total_realized_pnl: "42.5",
  equity_curve: [],
  updated_at: "2026-05-01T12:00:00Z",
};

function renderWith(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("LiveSessionList PnL 배지 (Wave0 cockpit surfacing)", () => {
  beforeEach(() => {
    stateMock.mockReset();
    listMock.mockReset();
    listMock.mockResolvedValue({ items: [SESSION], total: 1 });
    stateMock.mockResolvedValue(STATE);
  });

  it("활성 세션 행에 부호·tone PnL 배지 표시", async () => {
    renderWith(<LiveSessionList />);
    // 양수 PnL 은 + prefix.
    expect(await screen.findByText("+42.5")).toBeInTheDocument();
  });
});
