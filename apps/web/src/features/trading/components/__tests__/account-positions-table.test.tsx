// BL-498 — 활성 세션이 없어도 계정 잔여 포지션이 보이고 닫히는지 검증한다.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAccountPositions, useClosePosition } from "@/features/live-sessions/hooks";
import type { AccountPositions } from "@/features/live-sessions/schemas";
import { ApiError } from "@/lib/api-client";

const mockUseIsMutating = vi.hoisted(() => vi.fn());

vi.mock("@tanstack/react-query", () => ({
  useIsMutating: (...args: unknown[]) => mockUseIsMutating(...args),
}));

vi.mock("@/features/live-sessions/hooks", () => ({
  closePositionMutationKey: ({ sessionId, symbol }: { sessionId: string; symbol: string }) => [
    "close-position",
    sessionId,
    symbol,
  ],
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

const RESTING_ORDER = {
  order_id: "1a2b3c4d",
  side: "buy",
  qty: "0.029",
  trigger_price: "64000",
  order_link_id: "link-1",
};

/** 서버가 실제로 내는 202 body (`ClosePositionResponse`). */
function closeResponse(overrides: Record<string, unknown> = {}) {
  return {
    order_id: "o-1",
    state: "submitted",
    detail: "reduce-only market close accepted",
    resting_entries: [],
    resting_entries_unknown: false,
    ...overrides,
  };
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
    // ★종전 픽스처는 `{}` 였다. 그것은 「응답 body 를 아무도 안 쓴다」는 사실을 시험으로
    //   굳힌 것이고, 실제로 화면이 잔량을 못 보는 원인의 한 축이었다. 이제는 서버가
    //   실제로 내는 모양을 준다.
    closePosition.mockResolvedValue(closeResponse());
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

  it("같은 uid·심볼의 양방향 두 leg를 모두 보존하고 차단한다", () => {
    mockAccountPositions.mockReturnValue([
      query({
        data: payload({
          rows: [
            {
              symbol: "BTC/USDT",
              position: position({ side: "long" }),
              closable_session_id: null,
              close_blocked_reason: "hedge_unsupported",
            },
            {
              symbol: "BTC/USDT",
              position: position({ side: "short" }),
              closable_session_id: null,
              close_blocked_reason: "hedge_unsupported",
            },
          ],
        } as Partial<AccountPositions>),
      }),
    ]);

    render(<AccountPositionsTable accounts={[{ ...ACCOUNT, exchangeUid: EXCHANGE_UID }]} />);

    expect(screen.getAllByText("BTC/USDT")).toHaveLength(2);
    const blockedRows = screen.getAllByTestId("account-position-blocked-BTC/USDT");
    expect(blockedRows).toHaveLength(2);
    for (const blockedRow of blockedRows) {
      expect(blockedRow).toHaveTextContent("양방향 포지션은 화면에서 청산할 수 없습니다.");
    }
    expect(screen.getByText("롱")).toBeInTheDocument();
    expect(screen.getByText("숏")).toBeInTheDocument();
  });

  it("조회 범위를 각주로 고지한다", () => {
    render(<AccountPositionsTable accounts={[ACCOUNT]} />);

    expect(screen.getByText(/USDT 정산 선물\(무기한·만기물\)만 조회합니다/)).toBeInTheDocument();
  });

  it("같은 uid와 심볼의 포지션을 한 행으로 접는다", () => {
    mockAccountPositions.mockReturnValue([
      query({
        data: payload({
          rows: [
            {
              symbol: "BTC/USDT",
              position: position(),
              closable_session_id: null,
              close_blocked_reason: "read_only_key",
            },
          ],
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
          rows: [
            {
              symbol: "BTC/USDT",
              position: position(),
              closable_session_id: null,
              close_blocked_reason: "read_only_key",
            },
          ],
        } as Partial<AccountPositions>),
      }),
      query({
        data: payload({
          rows: [
            {
              symbol: "BTC/USDT",
              position: position(),
              closable_session_id: WRITABLE_SESSION_ID,
              close_blocked_reason: null,
            },
          ],
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
          rows: [
            {
              symbol: "BTC/USDT",
              position: position(),
              closable_session_id: null,
              close_blocked_reason: "read_only_key",
            },
          ],
        } as Partial<AccountPositions>),
      }),
      query({
        data: payload({
          rows: [
            {
              symbol: "BTC/USDT",
              position: position(),
              closable_session_id: null,
              close_blocked_reason: "read_only_key",
            },
          ],
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
    mockAccountPositions.mockReturnValue([query(), query({ data: undefined, isError: true })]);

    render(
      <AccountPositionsTable
        accounts={[ACCOUNT, { id: "b0000000-0000-4000-8000-000000000002", label: "Bybit 데모 2" }]}
      />,
    );

    expect(screen.getByText("BTC/USDT")).toBeInTheDocument();
    expect(screen.getByTestId("account-positions-account-error")).toHaveTextContent("Bybit 데모 2");
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
        data: payload({
          supported: false,
          reason: "live_mode_stub",
          rows: [],
        } as Partial<AccountPositions>),
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

// ★청산 결과 표면. CLI 는 rc 0/3/4 로 세 상태를 가르는데 화면은 오래 「접수」 하나만
//   말했다. 여기서 재는 것은 **셋이 서로 다르게 보이는가** 다 — 특히 「잔량 없음」과
//   「거래소에 못 물어봤다」가 같은 화면이면 고친 것이 없다.
describe("AccountPositionsTable 청산 결과", () => {
  async function closeAndWait(response: unknown, { reject = false } = {}) {
    if (reject) closePosition.mockRejectedValue(response);
    else closePosition.mockResolvedValue(response);
    render(<AccountPositionsTable accounts={[ACCOUNT]} />);
    fireEvent.click(screen.getByTestId("account-position-close-BTC/USDT"));
    fireEvent.click(screen.getByRole("button", { name: "청산 실행" }));
    await waitFor(() => expect(closePosition).toHaveBeenCalled());
  }

  it("잔량이 없으면 조용히 닫힌다", async () => {
    await closeAndWait(closeResponse());

    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "청산 실행" })).not.toBeInTheDocument(),
    );
    expect(screen.queryByTestId("close-outcome-resting")).not.toBeInTheDocument();
    expect(screen.queryByTestId("close-outcome-unknown")).not.toBeInTheDocument();
  });

  it("접수 + 잔량이면 주문 목록을 보여주고 재제출을 막는다", async () => {
    await closeAndWait(closeResponse({ resting_entries: [RESTING_ORDER] }));

    const panel = await screen.findByTestId("close-outcome-resting");
    expect(panel).toHaveTextContent("미체결 진입 주문 1건이 남아 있습니다.");
    expect(screen.getByTestId("close-resting-entry")).toHaveTextContent("1a2b3c4d");
    expect(screen.getByTestId("close-resting-entry")).toHaveTextContent("64000");
    // 주문은 이미 나갔다.
    expect(screen.queryByRole("button", { name: "청산 실행" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "확인" })).toBeInTheDocument();
    // 음성 대조 — 미확인 상태와 겹치지 않는다.
    expect(screen.queryByTestId("close-outcome-unknown")).not.toBeInTheDocument();
  });

  it("접수 + 잔량 미확인은 잔량 있음과 **다르게** 보인다", async () => {
    await closeAndWait(closeResponse({ resting_entries_unknown: true }));

    const panel = await screen.findByTestId("close-outcome-unknown");
    expect(panel).toHaveTextContent("확인하지 못했습니다");
    // ★빈 목록을 「잔량 없음」으로 그리지 않는다. 이것이 이 회차의 핵심 판정이다.
    expect(screen.queryByTestId("close-outcome-resting")).not.toBeInTheDocument();
    expect(screen.queryByTestId("close-resting-entry")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "청산 실행" })).not.toBeInTheDocument();
  });

  it("409 잔량은 주문 목록까지 펴고 재시도를 남긴다", async () => {
    await closeAndWait(
      new ApiError(409, "resting_conditional_entries", "API 409 /x", {
        detail: {
          code: "resting_conditional_entries",
          count: 1,
          detail: "포지션은 없지만 미체결 진입 주문 1건이 남아 있습니다.",
          orders: [RESTING_ORDER],
        },
      }),
      { reject: true },
    );

    const panel = await screen.findByTestId("close-outcome-blocked");
    expect(panel).toHaveTextContent("포지션은 없지만 미체결 진입 주문 1건이 남아 있습니다.");
    expect(screen.getByTestId("close-resting-entry")).toHaveTextContent("1a2b3c4d");
    // 주문을 내지 않았으므로 재시도가 유효하다.
    expect(screen.getByRole("button", { name: "청산 실행" })).toBeInTheDocument();
  });
});
