// Order 상태 전환 알림 — 순수 판정(detectOrderTransitions)과 소유자 훅(useOrderTransitionToasts).
// 소유자 훅은 실제 useOrders 재조회를 태워 검증한다(api-client 만 목).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, renderHook, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

const apiFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiFetchMock };
});

import { OrdersPanel } from "../components/orders-panel";
import { detectOrderTransitions, useOrders, useOrderTransitionToasts } from "../hooks";

const ORDER_A = "a0000000-0000-4000-a000-000000000001";
const ORDER_B = "a0000000-0000-4000-a000-000000000004";

function makeOrder(id: string, state: string, symbol = "BTC/USDT") {
  return {
    id,
    strategy_id: "a0000000-0000-4000-a000-000000000002",
    exchange_account_id: "a0000000-0000-4000-a000-000000000003",
    symbol,
    side: "buy",
    type: "market",
    price: null,
    state,
    quantity: "0.01",
    idempotency_key: null,
    filled_price: null,
    exchange_order_id: null,
    error_message: null,
    submitted_at: "2026-04-16T10:00:01Z",
    filled_at: null,
    created_at: "2026-04-16T10:00:00Z",
    leverage: null,
    margin_mode: null,
  };
}

function page(...items: ReturnType<typeof makeOrder>[]) {
  return { items, total: items.length };
}

function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("detectOrderTransitions", () => {
  it("이전 맵이 비어 있으면 전환이 없고, 다음 맵에 현재 state 를 담는다", () => {
    const { transitions, next } = detectOrderTransitions(new Map(), [
      { id: "a", state: "filled", symbol: "BTC/USDT" },
      { id: "b", state: "pending", symbol: "ETH/USDT" },
    ]);
    expect(transitions).toEqual([]);
    expect([...next]).toEqual([
      ["a", "filled"],
      ["b", "pending"],
    ]);
  });

  it("이전 state 가 진행 중이고 달라진 주문만 목록 순서대로 돌려준다", () => {
    const prev = new Map([
      ["a", "pending"],
      ["b", "submitted"],
      ["c", "submitted"],
      ["d", "filled"],
    ] as const);
    const { transitions } = detectOrderTransitions(prev, [
      { id: "a", state: "submitted", symbol: "A" },
      { id: "b", state: "cancelled", symbol: "B" },
      { id: "c", state: "submitted", symbol: "C" },
      { id: "d", state: "cancelled", symbol: "D" },
    ]);
    expect(transitions).toEqual([
      { state: "submitted", symbol: "A" },
      { state: "cancelled", symbol: "B" },
    ]);
  });

  it("목록에서 사라진 id 는 다음 맵에서 빠지고, 입력 맵은 고치지 않는다", () => {
    const prev = new Map([
      ["a", "pending"],
      ["gone", "submitted"],
    ] as const);
    const { next } = detectOrderTransitions(prev, [{ id: "a", state: "filled", symbol: "A" }]);
    expect([...next]).toEqual([["a", "filled"]]);
    expect(prev.get("a")).toBe("pending");
    expect(prev.has("gone")).toBe(true);
  });
});

describe("useOrderTransitionToasts", () => {
  let now = Date.UTC(2026, 3, 16, 10, 0, 0);

  beforeEach(() => {
    // 가드가 dataUpdatedAt(ms) 을 비교하므로 재조회마다 시계를 민다 — 같은 ms 에 끝난 두 응답은
    // 한 번으로 접힌다(폴링 최소 5초라 운영에서는 겹치지 않는다).
    vi.spyOn(Date, "now").mockImplementation(() => now);
    vi.spyOn(toast, "success").mockImplementation(() => "t");
    vi.spyOn(toast, "warning").mockImplementation(() => "t");
    vi.spyOn(toast, "error").mockImplementation(() => "t");
  });

  afterEach(() => {
    apiFetchMock.mockReset();
    vi.restoreAllMocks();
  });

  function renderOwner() {
    return renderHook(
      () => {
        const query = useOrders(50);
        useOrderTransitionToasts(query);
        return query;
      },
      { wrapper: makeWrapper() },
    );
  }

  async function refetchWith(
    result: { current: ReturnType<typeof useOrders> },
    data: ReturnType<typeof page>,
  ) {
    now += 5_000;
    apiFetchMock.mockResolvedValueOnce(data);
    await act(async () => {
      await result.current.refetch();
    });
    // React Query 는 구독자 통지를 다음 틱으로 미룬다 — 새 응답이 커밋될 때까지 기다린 뒤 단언한다.
    await waitFor(() => expect(result.current.dataUpdatedAt).toBe(now));
  }

  it("최초 로드는 알리지 않는다 — 이미 끝난 주문이 처음 보여도 무발화", async () => {
    apiFetchMock.mockResolvedValueOnce(page(makeOrder(ORDER_A, "filled")));
    const { result } = renderOwner();
    await waitFor(() => expect(result.current.data?.total).toBe(1));

    expect(toast.success).not.toHaveBeenCalled();
    expect(toast.warning).not.toHaveBeenCalled();
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("진행 중 → filled 재조회에 toast.success 가 정확히 1회 — 리렌더·다음 재조회는 무발화", async () => {
    apiFetchMock.mockResolvedValueOnce(page(makeOrder(ORDER_A, "submitted")));
    const { result, rerender } = renderOwner();
    await waitFor(() => expect(result.current.data?.total).toBe(1));

    await refetchWith(result, page(makeOrder(ORDER_A, "filled")));
    expect(toast.success).toHaveBeenCalledTimes(1);
    expect(toast.success).toHaveBeenCalledWith("BTC/USDT 주문 체결 완료");

    rerender();
    await refetchWith(result, page(makeOrder(ORDER_A, "filled")));
    expect(toast.success).toHaveBeenCalledTimes(1);
    expect(toast.warning).not.toHaveBeenCalled();
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("cancelled 는 warning, rejected 는 error 로 알리고 pending → submitted 는 알리지 않는다", async () => {
    apiFetchMock.mockResolvedValueOnce(
      page(makeOrder(ORDER_A, "pending", "ETH/USDT"), makeOrder(ORDER_B, "pending", "SOL/USDT")),
    );
    const { result } = renderOwner();
    await waitFor(() => expect(result.current.data?.total).toBe(2));

    await refetchWith(
      result,
      page(makeOrder(ORDER_A, "submitted", "ETH/USDT"), makeOrder(ORDER_B, "rejected", "SOL/USDT")),
    );
    expect(toast.error).toHaveBeenCalledTimes(1);
    expect(toast.error).toHaveBeenCalledWith("SOL/USDT 주문 거부됨");
    expect(toast.warning).not.toHaveBeenCalled();

    await refetchWith(
      result,
      page(makeOrder(ORDER_A, "cancelled", "ETH/USDT"), makeOrder(ORDER_B, "rejected", "SOL/USDT")),
    );
    expect(toast.warning).toHaveBeenCalledTimes(1);
    expect(toast.warning).toHaveBeenCalledWith("ETH/USDT 주문 취소됨");
    expect(toast.error).toHaveBeenCalledTimes(1);
    expect(toast.success).not.toHaveBeenCalled();
  });

  it("목록에서 사라진 주문 id 는 잊는다 — 다시 나타나도 최초 관측으로 취급해 무발화", async () => {
    apiFetchMock.mockResolvedValueOnce(page(makeOrder(ORDER_A, "pending")));
    const { result } = renderOwner();
    await waitFor(() => expect(result.current.data?.total).toBe(1));

    await refetchWith(result, page(makeOrder(ORDER_B, "filled")));
    await refetchWith(result, page(makeOrder(ORDER_A, "filled"), makeOrder(ORDER_B, "filled")));

    expect(toast.success).not.toHaveBeenCalled();
    expect(toast.warning).not.toHaveBeenCalled();
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("OrdersPanel 이 전환 알림을 소유한다 — 진행 중 → filled 폴링에 toast 1회", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    apiFetchMock.mockResolvedValueOnce(page(makeOrder(ORDER_A, "submitted")));
    render(
      <QueryClientProvider client={queryClient}>
        <OrdersPanel />
      </QueryClientProvider>,
    );
    await screen.findByText("BTC/USDT");
    expect(toast.success).not.toHaveBeenCalled();

    now += 5_000;
    apiFetchMock.mockResolvedValueOnce(page(makeOrder(ORDER_A, "filled")));
    await act(async () => {
      await queryClient.refetchQueries();
    });

    await waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1));
    expect(toast.success).toHaveBeenCalledWith("BTC/USDT 주문 체결 완료");
  });
});
