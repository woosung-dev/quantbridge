// 열린 포지션 표의 정직한 상태와 수익률 표시를 검증한다.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  useClosePosition,
  useLiveSessionsPositions,
} from "@/features/live-sessions/hooks";
import type { LiveSession } from "@/features/live-sessions/schemas";
import { ApiError } from "@/lib/api-client";

const mockUseIsMutating = vi.hoisted(() => vi.fn());

vi.mock("@tanstack/react-query", () => ({
  useIsMutating: (...args: unknown[]) => mockUseIsMutating(...args),
}));

vi.mock("@/features/live-sessions/hooks", () => ({
  closePositionMutationKey: ({ sessionId, symbol }: { sessionId: string; symbol: string }) =>
    ["close-position", sessionId, symbol],
  useClosePosition: vi.fn(),
  useLiveSessionsPositions: vi.fn(),
}));

import { OpenPositionsTable } from "../open-positions-table";

const session = {
  id: "a0000000-0000-4000-8000-000000000001",
  strategy_id: "a0000000-0000-4000-8000-000000000011",
  is_active: true,
} as unknown as LiveSession;
const refetch = vi.fn();
const closePosition = vi.fn();
const mockPositions = vi.mocked(useLiveSessionsPositions);
const mockClosePosition = vi.mocked(useClosePosition);
const demoSessionIds = new Set([session.id]);

function aggregate(overrides: Record<string, unknown> = {}) {
  return {
    rows: [],
    unsupported: [],
    divergences: [],
    latestFetchedAt: null,
    isLoading: false,
    isPending: false,
    isError: false,
    refetch,
    ...overrides,
  } as never;
}

/** 청산 버튼이 뜨는 최소 행. 청산 결과 시험들이 공유한다. */
function closableRow() {
  return {
    sessionId: session.id,
    sessionLabel: "전략 A",
    symbol: "BTCUSDT",
    verdict: "match",
    position: {
      side: "long",
      size: "1",
      entry_price: "100",
      mark_price: "100",
      unrealized_pnl: "0",
      take_profit_prices: [],
      stop_loss_prices: [],
      has_trailing_stop: false,
      liquidation_price: null,
      leverage: null,
    },
  };
}

beforeEach(() => {
  refetch.mockReset();
  closePosition.mockReset();
  mockUseIsMutating.mockReset();
  mockUseIsMutating.mockReturnValue(0);
  mockPositions.mockReturnValue(aggregate());
  mockClosePosition.mockReturnValue({
    mutateAsync: closePosition,
    isPending: false,
    variables: undefined,
  } as never);
});

describe("OpenPositionsTable", () => {
  it("활성 세션이 없으면 빈 상태를 정직하게 표시한다", () => {
    render(<OpenPositionsTable sessions={[]} demoSessionIds={demoSessionIds} />);
    expect(screen.getByText("활성 라이브 세션이 없습니다.")).toBeInTheDocument();
  });

  it("지원 응답이지만 열린 포지션이 없으면 별도 빈 상태를 표시한다", () => {
    render(<OpenPositionsTable sessions={[session]} demoSessionIds={demoSessionIds} />);
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
    render(<OpenPositionsTable sessions={[session]} demoSessionIds={demoSessionIds} />);
    expect(screen.getByTestId("open-positions-unsupported")).toHaveTextContent(
      "현물 세션의 포지션 대조는 아직 지원하지 않습니다.",
    );
    expect(screen.getByTestId("open-positions-unsupported").querySelector("td")).toHaveAttribute(
      "colspan",
      "14",
    );
  });

  it("오류는 실제 positions 경로와 재시도를 제공한다", () => {
    mockPositions.mockReturnValue(aggregate({ isError: true }));
    render(<OpenPositionsTable sessions={[session]} demoSessionIds={demoSessionIds} />);
    expect(screen.getByText(/GET \/api\/v1\/live-sessions\/\{session_id\}\/positions · 503/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    expect(refetch).toHaveBeenCalledOnce();
  });

  it("flat은 수익률을 비우고 short 수익률은 진입가 하락을 양수로 표시하며 병합 TP/SL을 렌더한다", () => {
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
              take_profit_prices: ["80", "70"],
              stop_loss_prices: [],
              has_trailing_stop: false,
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
              take_profit_prices: [],
              stop_loss_prices: [],
              has_trailing_stop: false,
              liquidation_price: null,
              leverage: null,
            },
          },
        ],
      }),
    );
    render(<OpenPositionsTable sessions={[session]} demoSessionIds={demoSessionIds} />);

    expect(screen.getByText("10.00%")).toBeInTheDocument();
    expect(screen.getByText("플랫")).toBeInTheDocument();
    expect(screen.getByText("거래소와 일치")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "익절" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "손절" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "청산" })).toBeInTheDocument();
    expect(screen.getByText("80, 70")).toBeInTheDocument();
    expect(screen.getAllByText("\u2014").length).toBeGreaterThan(0);
    expect(screen.getByText(/포지션-부착 값과 별도 조건부 주문/)).toBeInTheDocument();
    expect(screen.queryByText("트레일링 스톱은 거리 기반이라 가격 열에는 표시되지 않습니다.")).not.toBeInTheDocument();
  });

  it("트레일링 스톱이 있는 포지션이면 가격 열 제외 안내를 표시한다", () => {
    mockPositions.mockReturnValue(
      aggregate({
        rows: [
          {
            sessionId: session.id,
            sessionLabel: "전략 A",
            symbol: "BTCUSDT",
            verdict: "match",
            position: {
              side: "long",
              size: "1",
              entry_price: "100",
              mark_price: "100",
              unrealized_pnl: "0",
              take_profit_prices: [],
              stop_loss_prices: [],
              has_trailing_stop: true,
              liquidation_price: null,
              leverage: null,
            },
          },
        ],
      }),
    );

    render(<OpenPositionsTable sessions={[session]} demoSessionIds={demoSessionIds} />);

    expect(screen.getByText("트레일링 스톱은 거리 기반이라 가격 열에는 표시되지 않습니다.")).toBeInTheDocument();
  });

  it("청산 확인창은 계정 단위 시장가 주문과 봇 재진입 가능성을 알린다", () => {
    mockPositions.mockReturnValue(
      aggregate({
        rows: [
          {
            sessionId: session.id,
            sessionLabel: "전략 A",
            symbol: "BTCUSDT",
            verdict: "match",
            position: {
              side: "long",
              size: "1",
              entry_price: "100",
              mark_price: "100",
              unrealized_pnl: "0",
              take_profit_prices: [],
              stop_loss_prices: [],
              has_trailing_stop: false,
              liquidation_price: null,
              leverage: null,
            },
          },
        ],
      }),
    );
    render(<OpenPositionsTable sessions={[session]} demoSessionIds={demoSessionIds} />);

    fireEvent.click(screen.getByRole("button", { name: "청산" }));

    expect(mockClosePosition).toHaveBeenLastCalledWith({
      sessionId: session.id,
      symbol: "BTCUSDT",
    });
    expect(screen.getByRole("heading", { name: "포지션 청산" })).toBeInTheDocument();
    expect(screen.getByText(/감소전용 시장가 주문/)).toBeInTheDocument();
    expect(screen.getByText(/수동 청산은 봇을 중단하지 않습니다/)).toBeInTheDocument();
  });

  it("진행 중인 청산은 해당 세션과 심볼 행만 비활성화한다", () => {
    const otherSession = { ...session, id: "a0000000-0000-4000-8000-000000000009" };
    mockUseIsMutating.mockReturnValueOnce(1).mockReturnValueOnce(0);
    mockPositions.mockReturnValue(
      aggregate({
        rows: [
          {
            sessionId: session.id,
            sessionLabel: "전략 A",
            symbol: "BTCUSDT",
            verdict: "match",
            position: {
              side: "long",
              size: "1",
              entry_price: "100",
              mark_price: "100",
              unrealized_pnl: "0",
              take_profit_prices: [],
              stop_loss_prices: [],
              has_trailing_stop: false,
              liquidation_price: null,
              leverage: null,
            },
          },
          {
            sessionId: otherSession.id,
            sessionLabel: "전략 B",
            symbol: "ETHUSDT",
            verdict: "match",
            position: {
              side: "long",
              size: "1",
              entry_price: "100",
              mark_price: "100",
              unrealized_pnl: "0",
              take_profit_prices: [],
              stop_loss_prices: [],
              has_trailing_stop: false,
              liquidation_price: null,
              leverage: null,
            },
          },
        ],
      }),
    );
    render(
      <OpenPositionsTable
        sessions={[session, otherSession]}
        demoSessionIds={new Set([session.id, otherSession.id])}
      />,
    );

    expect(screen.getByRole("button", { name: "청산 중..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "청산" })).toBeEnabled();
  });

  it("청산 요청 실패는 확인창 안에 표시한다", async () => {
    closePosition.mockRejectedValueOnce(new Error("거래소 연결 실패"));
    mockPositions.mockReturnValue(aggregate({ rows: [closableRow()] }));
    render(<OpenPositionsTable sessions={[session]} demoSessionIds={demoSessionIds} />);

    fireEvent.click(screen.getByRole("button", { name: "청산" }));
    fireEvent.click(screen.getByRole("button", { name: "청산 실행" }));

    await waitFor(() => expect(closePosition).toHaveBeenCalledWith());
    expect(await screen.findByRole("alert")).toHaveTextContent("거래소 연결 실패");
  });

  // ★이 표는 오랫동안 `error.message` 만 썼다. 그래서 서버가 한국어 사유를 실어 보내도
  //   화면에는 `API 409 /api/v1/…` 가 떴다. 계정 표는 고쳐졌는데 여기만 안 고쳐진
  //   비대칭이었고, 아래 두 시험이 그것을 고정한다.
  it("도메인 거부는 서버가 보낸 사유를 보여준다", async () => {
    closePosition.mockRejectedValueOnce(
      new ApiError(409, "no_open_position", "API 409 /x", {
        detail: { code: "no_open_position", detail: "이미 평탄한 상태입니다" },
      }),
    );
    mockPositions.mockReturnValue(aggregate({ rows: [closableRow()] }));
    render(<OpenPositionsTable sessions={[session]} demoSessionIds={demoSessionIds} />);

    fireEvent.click(screen.getByRole("button", { name: "청산" }));
    fireEvent.click(screen.getByRole("button", { name: "청산 실행" }));

    const panel = await screen.findByTestId("close-outcome-failed");
    expect(panel).toHaveTextContent("이미 평탄한 상태입니다");
    expect(panel).not.toHaveTextContent("API 409");
  });

  it("409 잔량은 주문 목록을 편다", async () => {
    closePosition.mockRejectedValueOnce(
      new ApiError(409, "resting_conditional_entries", "API 409 /x", {
        detail: {
          code: "resting_conditional_entries",
          count: 1,
          detail: "포지션은 없지만 미체결 진입 주문 1건이 남아 있습니다.",
          orders: [
            {
              order_id: "1a2b3c4d",
              side: "buy",
              qty: "0.029",
              trigger_price: "64000",
              order_link_id: null,
            },
          ],
        },
      }),
    );
    mockPositions.mockReturnValue(aggregate({ rows: [closableRow()] }));
    render(<OpenPositionsTable sessions={[session]} demoSessionIds={demoSessionIds} />);

    fireEvent.click(screen.getByRole("button", { name: "청산" }));
    fireEvent.click(screen.getByRole("button", { name: "청산 실행" }));

    expect(await screen.findByTestId("close-outcome-blocked")).toHaveTextContent(
      "미체결 진입 주문 1건",
    );
    const entry = screen.getByTestId("close-resting-entry");
    expect(entry).toHaveTextContent("1a2b3c4d");
    // `order_link_id` 가 없으면 CLI 와 같은 자리표시자를 쓴다.
    expect(entry).toHaveTextContent("link -");
  });

  it("접수 + 잔량 미확인은 잔량 있음과 다르게 보인다", async () => {
    closePosition.mockResolvedValueOnce({
      order_id: "o-1",
      state: "submitted",
      detail: "reduce-only market close accepted · 미체결 진입 주문 확인 실패",
      resting_entries: [],
      resting_entries_unknown: true,
    });
    mockPositions.mockReturnValue(aggregate({ rows: [closableRow()] }));
    render(<OpenPositionsTable sessions={[session]} demoSessionIds={demoSessionIds} />);

    fireEvent.click(screen.getByRole("button", { name: "청산" }));
    fireEvent.click(screen.getByRole("button", { name: "청산 실행" }));

    expect(await screen.findByTestId("close-outcome-unknown")).toHaveTextContent(
      "확인하지 못했습니다",
    );
    expect(screen.queryByTestId("close-outcome-resting")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "청산 실행" })).not.toBeInTheDocument();
  });
});

// === BL-480 — 발산을 은폐하던 빈 상태 ===
describe("OpenPositionsTable — 발산 표면화 (BL-480)", () => {
  const divergence = {
    sessionId: session.id,
    sessionLabel: "전략 A",
    symbol: "BTCUSDT",
    verdict: "local_only" as const,
    localOpenTrades: [{ id: "PivRevLE", direction: "long", qty: "1" }],
    fetchedAt: "2026-07-26T04:47:19Z",
  };

  it("local_only 면 '열린 포지션이 없습니다' 대신 발산을 표시한다", () => {
    mockPositions.mockReturnValue(aggregate({ divergences: [divergence] }));
    render(<OpenPositionsTable sessions={[session]} demoSessionIds={demoSessionIds} />);

    // ★핵심 — 거래소 기준으로는 참이지만 pine 이 롱을 들고 있다는 걸 감추는 문구.
    expect(screen.queryByText("열린 포지션이 없습니다.")).not.toBeInTheDocument();
    expect(screen.getByTestId("open-positions-divergence")).toHaveTextContent(
      "전략에만 열린 거래가 있습니다.",
    );
  });

  it("발산 행이 전략이 들고 있다고 믿는 포지션을 함께 보여준다", () => {
    mockPositions.mockReturnValue(aggregate({ divergences: [divergence] }));
    render(<OpenPositionsTable sessions={[session]} demoSessionIds={demoSessionIds} />);

    const row = screen.getByTestId("open-positions-divergence");
    expect(row).toHaveTextContent("PivRevLE");
    expect(row).toHaveTextContent("롱");
    expect(row).toHaveTextContent("1");
  });

  it("발산이 없으면 기존 빈 상태를 그대로 유지한다", () => {
    mockPositions.mockReturnValue(aggregate({ divergences: [] }));
    render(<OpenPositionsTable sessions={[session]} demoSessionIds={demoSessionIds} />);
    expect(screen.getByText("열린 포지션이 없습니다.")).toBeInTheDocument();
    expect(screen.queryByTestId("open-positions-divergence")).not.toBeInTheDocument();
  });
});
