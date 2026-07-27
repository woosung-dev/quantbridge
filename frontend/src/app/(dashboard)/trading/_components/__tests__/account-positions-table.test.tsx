// BL-498 — 활성 세션이 없어도 계정 잔여 포지션이 보이고 닫히는지 검증한다.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAccountPositions, useClosePosition } from "@/features/live-sessions/hooks";
import type { AccountPositions } from "@/features/live-sessions/schemas";

const mockUseIsMutating = vi.hoisted(() => vi.fn());

vi.mock("@tanstack/react-query", () => ({
  useIsMutating: (...args: unknown[]) => mockUseIsMutating(...args),
}));

vi.mock("@/features/live-sessions/hooks", () => ({
  closePositionMutationKey: ({ sessionId, symbol }: { sessionId: string; symbol: string }) =>
    ["close-position", sessionId, symbol],
  useAccountPositions: vi.fn(),
  useClosePosition: vi.fn(),
}));

import { AccountPositionsTable } from "../account-positions-table";

const ACCOUNT = { id: "b0000000-0000-4000-8000-000000000001", label: "Bybit 데모" };
const ACCOUNT_TWO = { id: "b0000000-0000-4000-8000-000000000002", label: "Bybit 데모 2" };
const SESSION_ID = "c0000000-0000-4000-8000-000000000001";
const WRITABLE_SESSION_ID = "c0000000-0000-4000-8000-000000000002";
const EXCHANGE_UID = "558689281";

const closePosition = vi.fn();
const refetch = vi.fn();
const mockAccountPositions = vi.mocked(useAccountPositions);
const mockClosePosition = vi.mocked(useClosePosition);

function position(overrides: Record<string, unknown> = {}) {
  return {
    side: "short",
    size: "0.029",
    entry_price: "65340.2",
    mark_price: "65100",
    unrealized_pnl: "7.22",
    liquidation_price: null,
    leverage: "10",
    take_profit_prices: [],
    stop_loss_prices: [],
    has_trailing_stop: false,
    ...overrides,
  };
}

function payload(overrides: Partial<AccountPositions> = {}): AccountPositions {
  return {
    account_id: ACCOUNT.id,
    supported: true,
    reason: null,
    fetched_at: "2026-07-27T12:00:00Z",
    settle_coin: "USDT",
    truncated: false,
    rows: [
      {
        symbol: "BTC/USDT",
        position: position(),
        closable_session_id: SESSION_ID,
        close_blocked_reason: null,
      },
    ],
    ...overrides,
  } as AccountPositions;
}

function query(overrides: Record<string, unknown> = {}) {
  return {
    data: payload(),
    isLoading: false,
    isError: false,
    refetch,
    ...overrides,
  } as never;
}

beforeEach(() => {
  closePosition.mockReset();
  refetch.mockReset();
  mockUseIsMutating.mockReset();
  mockUseIsMutating.mockReturnValue(0);
  mockAccountPositions.mockReturnValue([query()]);
  mockClosePosition.mockReturnValue({
    mutateAsync: closePosition,
    isPending: false,
    variables: undefined,
  } as never);
});

describe("AccountPositionsTable", () => {
  it("활성 세션이 하나도 없어도 계정 잔여 포지션을 렌더한다", () => {
    render(<AccountPositionsTable accounts={[ACCOUNT]} />);

    expect(screen.getByText("BTC/USDT")).toBeInTheDocument();
    expect(screen.getByText("0.029")).toBeInTheDocument();
  });

  it("귀속 세션이 있으면 청산 버튼이 그 세션으로 요청한다", async () => {
    closePosition.mockResolvedValue({});
    render(<AccountPositionsTable accounts={[ACCOUNT]} />);

    fireEvent.click(screen.getByTestId("account-position-close-BTC/USDT"));
    expect(mockClosePosition).toHaveBeenLastCalledWith({
      sessionId: SESSION_ID,
      symbol: "BTC/USDT",
    });
    fireEvent.click(screen.getByRole("button", { name: "청산 실행" }));

    await waitFor(() => expect(closePosition).toHaveBeenCalledWith());
  });

  it("귀속 세션이 없으면 버튼 대신 사유를 보여준다", () => {
    mockAccountPositions.mockReturnValue([
      query({
        data: payload({
          rows: [
            {
              symbol: "ETH/USDT",
              position: position(),
              closable_session_id: null,
              close_blocked_reason: "no_owning_session",
            },
          ],
        } as Partial<AccountPositions>),
      }),
    ]);

    render(<AccountPositionsTable accounts={[ACCOUNT]} />);

    expect(screen.queryByTestId("account-position-close-ETH/USDT")).not.toBeInTheDocument();
    expect(screen.getByTestId("account-position-blocked-ETH/USDT")).toHaveTextContent(
      "이 계정·심볼로 만든 세션이 없어 원장에 귀속할 수 없습니다.",
    );
  });

  it("양방향 포지션은 청산 버튼을 주지 않고 이유를 말한다", () => {
    mockAccountPositions.mockReturnValue([
      query({
        data: payload({
          rows: [
            {
              symbol: "BTC/USDT",
              position: position(),
              closable_session_id: null,
              close_blocked_reason: "hedge_unsupported",
            },
          ],
        } as Partial<AccountPositions>),
      }),
    ]);

    render(<AccountPositionsTable accounts={[ACCOUNT]} />);

    expect(screen.queryByTestId("account-position-close-BTC/USDT")).not.toBeInTheDocument();
    expect(screen.getByTestId("account-position-blocked-BTC/USDT")).toHaveTextContent(
      "양방향 포지션은 화면에서 청산할 수 없습니다.",
    );
  });

  it("조회 범위를 각주로 고지한다", () => {
    render(<AccountPositionsTable accounts={[ACCOUNT]} />);

    expect(
      screen.getByText(/USDT 정산 선물\(무기한·만기물\)만 조회합니다/),
    ).toBeInTheDocument();
  });

  it("같은 uid와 심볼의 포지션을 한 행으로 접는다", () => {
    mockAccountPositions.mockReturnValue([
      query({
        data: payload({
          rows: [{ symbol: "BTC/USDT", position: position(), closable_session_id: null, close_blocked_reason: "read_only_key" }],
        } as Partial<AccountPositions>),
      }),
      query(),
    ]);

    render(
      <AccountPositionsTable
        accounts={[
          { ...ACCOUNT, exchangeUid: EXCHANGE_UID, readOnly: true },
          { ...ACCOUNT_TWO, exchangeUid: EXCHANGE_UID, readOnly: false },
        ]}
      />,
    );

    expect(screen.getAllByText("BTC/USDT")).toHaveLength(1);
  });

  it("접힌 행은 쓰기 가능하고 귀속 세션이 있는 형제로 청산한다", () => {
    mockAccountPositions.mockReturnValue([
      query({
        data: payload({
          rows: [{ symbol: "BTC/USDT", position: position(), closable_session_id: null, close_blocked_reason: "read_only_key" }],
        } as Partial<AccountPositions>),
      }),
      query({
        data: payload({
          rows: [{ symbol: "BTC/USDT", position: position(), closable_session_id: WRITABLE_SESSION_ID, close_blocked_reason: null }],
        } as Partial<AccountPositions>),
      }),
    ]);

    render(
      <AccountPositionsTable
        accounts={[
          { ...ACCOUNT, exchangeUid: EXCHANGE_UID, readOnly: true },
          { ...ACCOUNT_TWO, exchangeUid: EXCHANGE_UID, readOnly: false },
        ]}
      />,
    );

    fireEvent.click(screen.getByTestId("account-position-close-BTC/USDT"));

    expect(mockClosePosition).toHaveBeenLastCalledWith({
      sessionId: WRITABLE_SESSION_ID,
      symbol: "BTC/USDT",
    });
  });

  it("쓰기 가능하고 귀속된 형제가 없으면 이유와 함께 차단한다", () => {
    mockAccountPositions.mockReturnValue([
      query({
        data: payload({
          rows: [{ symbol: "BTC/USDT", position: position(), closable_session_id: null, close_blocked_reason: "read_only_key" }],
        } as Partial<AccountPositions>),
      }),
      query({
        data: payload({
          rows: [{ symbol: "BTC/USDT", position: position(), closable_session_id: null, close_blocked_reason: "read_only_key" }],
        } as Partial<AccountPositions>),
      }),
    ]);

    render(
      <AccountPositionsTable
        accounts={[
          { ...ACCOUNT, exchangeUid: EXCHANGE_UID, readOnly: true },
          { ...ACCOUNT_TWO, exchangeUid: EXCHANGE_UID, readOnly: true },
        ]}
      />,
    );

    expect(screen.queryByTestId("account-position-close-BTC/USDT")).not.toBeInTheDocument();
    expect(screen.getByTestId("account-position-blocked-BTC/USDT")).toHaveTextContent(
      "이 API 키는 읽기 전용이라 화면에서 청산할 수 없습니다.",
    );
  });

  it("exchange_uid가 없으면 같은 심볼도 접지 않는다", () => {
    mockAccountPositions.mockReturnValue([query(), query()]);

    render(<AccountPositionsTable accounts={[ACCOUNT, ACCOUNT_TWO]} />);

    expect(screen.getAllByText("BTC/USDT")).toHaveLength(2);
  });

  it("거래소가 더 있다고 하면 첫 200건만 보여준다고 말한다", () => {
    mockAccountPositions.mockReturnValue([
      query({ data: payload({ truncated: true } as Partial<AccountPositions>) }),
    ]);

    render(<AccountPositionsTable accounts={[ACCOUNT]} />);

    expect(screen.getByText(/첫 200건만 보여줍니다/)).toBeInTheDocument();
  });

  it("계정 하나가 실패해도 나머지를 보여주고 실패를 실패라고 말한다", () => {
    // ★행에서 지우면 "이 계정에 포지션이 없다" 로 읽힌다 — 잔여 노출 관리 표에서
    //   그건 정확히 반대의 거짓말이다.
    mockAccountPositions.mockReturnValue([
      query(),
      query({ data: undefined, isError: true }),
    ]);

    render(
      <AccountPositionsTable
        accounts={[ACCOUNT, { id: "b0000000-0000-4000-8000-000000000002", label: "Bybit 데모 2" }]}
      />,
    );

    expect(screen.getByText("BTC/USDT")).toBeInTheDocument();
    expect(screen.getByTestId("account-positions-account-error")).toHaveTextContent(
      "Bybit 데모 2",
    );
    expect(screen.queryByTestId("account-positions-empty")).not.toBeInTheDocument();
  });

  it("성공 이력이 있는 계정이 실패하면 그 값이 낡았다고 말한다", () => {
    mockAccountPositions.mockReturnValue([query({ isError: true })]);

    render(<AccountPositionsTable accounts={[ACCOUNT]} />);

    expect(screen.getByTestId("account-positions-account-error")).toHaveTextContent(
      "최신이 아닙니다",
    );
  });

  it("미지원 계정은 이유를 숨기지 않는다", () => {
    mockAccountPositions.mockReturnValue([
      query({
        data: payload({ supported: false, reason: "live_mode_stub", rows: [] } as Partial<AccountPositions>),
      }),
    ]);

    render(<AccountPositionsTable accounts={[ACCOUNT]} />);

    expect(screen.getByTestId("account-positions-unsupported")).toHaveTextContent(
      "라이브 모드 계정의 포지션 조회는 아직 제공되지 않습니다.",
    );
  });

  it("등록된 계정이 없으면 빈 상태를 표시한다", () => {
    mockAccountPositions.mockReturnValue([]);
    render(<AccountPositionsTable accounts={[]} />);

    expect(screen.getByTestId("account-positions-no-accounts")).toBeInTheDocument();
  });

  it("조회 실패는 빈 목록으로 위장하지 않는다", () => {
    mockAccountPositions.mockReturnValue([query({ data: undefined, isError: true })]);

    render(<AccountPositionsTable accounts={[ACCOUNT]} />);

    expect(screen.getByTestId("account-positions-error")).toBeInTheDocument();
  });
});
