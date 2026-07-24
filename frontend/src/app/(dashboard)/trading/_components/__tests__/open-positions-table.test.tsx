// 열린 포지션 표의 정직한 상태와 수익률 표시를 검증한다.
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useLiveSessionsPositions } from "@/features/live-sessions/hooks";
import type { LiveSession } from "@/features/live-sessions/schemas";

vi.mock("@/features/live-sessions/hooks", () => ({
  useLiveSessionsPositions: vi.fn(),
}));

import { OpenPositionsTable } from "../open-positions-table";

const session = {
  id: "a0000000-0000-4000-8000-000000000001",
  strategy_id: "a0000000-0000-4000-8000-000000000011",
  is_active: true,
} as unknown as LiveSession;
const refetch = vi.fn();
const mockPositions = vi.mocked(useLiveSessionsPositions);

function aggregate(overrides: Record<string, unknown> = {}) {
  return {
    rows: [],
    unsupported: [],
    latestFetchedAt: null,
    isLoading: false,
    isPending: false,
    isError: false,
    refetch,
    ...overrides,
  } as never;
}

beforeEach(() => {
  refetch.mockReset();
  mockPositions.mockReturnValue(aggregate());
});

describe("OpenPositionsTable", () => {
  it("활성 세션이 없으면 빈 상태를 정직하게 표시한다", () => {
    render(<OpenPositionsTable sessions={[]} />);
    expect(screen.getByText("활성 라이브 세션이 없습니다.")).toBeInTheDocument();
  });

  it("지원 응답이지만 열린 포지션이 없으면 별도 빈 상태를 표시한다", () => {
    render(<OpenPositionsTable sessions={[session]} />);
    expect(screen.getByText("열린 포지션이 없습니다.")).toBeInTheDocument();
  });

  it("지원하지 않는 세션은 사유 행으로 표시한다", () => {
    mockPositions.mockReturnValue(
      aggregate({
        unsupported: [
          {
            sessionId: session.id,
            sessionLabel: "전략 A",
            symbol: "BTCUSDT",
            reason: "spot_position_api_unsupported",
          },
        ],
      }),
    );
    render(<OpenPositionsTable sessions={[session]} />);
    expect(screen.getByTestId("open-positions-unsupported")).toHaveTextContent(
      "현물 세션의 포지션 대조는 아직 지원하지 않습니다.",
    );
  });

  it("오류는 실제 positions 경로와 재시도를 제공한다", () => {
    mockPositions.mockReturnValue(aggregate({ isError: true }));
    render(<OpenPositionsTable sessions={[session]} />);
    expect(screen.getByText(/GET \/api\/v1\/live-sessions\/\{session_id\}\/positions · 503/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    expect(refetch).toHaveBeenCalledOnce();
  });

  it("flat은 수익률을 비우고 short 수익률은 진입가 하락을 양수로 표시하며 TP/SL 열을 만들지 않는다", () => {
    mockPositions.mockReturnValue(
      aggregate({
        latestFetchedAt: "2026-07-24T12:00:00Z",
        rows: [
          {
            sessionId: session.id,
            sessionLabel: "전략 A",
            symbol: "BTCUSDT",
            verdict: "match",
            position: {
              side: "short",
              size: "1",
              entry_price: "100",
              mark_price: "90",
              unrealized_pnl: "10",
              liquidation_price: "150",
              leverage: "5",
            },
          },
          {
            sessionId: "session-flat",
            sessionLabel: "전략 B",
            symbol: "ETHUSDT",
            verdict: "unknown",
            position: {
              side: "flat",
              size: "0",
              entry_price: "100",
              mark_price: "100",
              unrealized_pnl: null,
              liquidation_price: null,
              leverage: null,
            },
          },
        ],
      }),
    );
    render(<OpenPositionsTable sessions={[session]} />);

    expect(screen.getByText("10.00%")).toBeInTheDocument();
    expect(screen.getByText("플랫")).toBeInTheDocument();
    expect(screen.getByText("거래소와 일치")).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: /익절|손절|청산 액션/ })).not.toBeInTheDocument();
  });
});
