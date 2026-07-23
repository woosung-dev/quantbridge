// 주문 원장(OrdersBlotter) — C 이식(W3-D) 상태 4종 + 프로토타입 시맨틱 구조 회귀 가드.
// useOrders 를 목으로 갈아끼워 로딩/에러/빈/데이터 경로를 각각 렌더하고, 프로토타입 유래
// 핵심 클래스(role=group 필터 · .order-side.buy/.sell · .chip.done · 10열 헤더 · 무데이터 title)를
// assert 한다. 라벨은 전부 용어 SSOT 에서 오므로 원시 enum 이 새어 나오지 않는지도 함께 본다.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { OrdersBlotter } from "@/app/(dashboard)/orders/_components/orders-blotter";
import {
  CancelOrderResponseSchema,
  type Order,
} from "@/features/trading/schemas";

const mockUseOrders = vi.fn();
const mockUseCancelOrder = vi.fn();
const mockCancelOrder = vi.fn();
vi.mock("@/features/trading/hooks", () => ({
  useOrders: (...args: unknown[]) => mockUseOrders(...args),
  useCancelOrder: () => mockUseCancelOrder(),
  ACTIVE_ORDER_STATES: new Set(["pending", "submitted"]),
}));

function makeOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: "00000000-0000-4000-8000-000000000001",
    symbol: "BTC/USDT",
    side: "buy",
    state: "filled",
    quantity: "0.021",
    filled_price: "62880.00",
    exchange_order_id: "78409188",
    error_message: null,
    created_at: "2026-04-14T20:00:04Z",
    reduce_only: false,
    trigger_price: null,
    trigger_by: null,
    take_profit: null,
    stop_loss: null,
    trigger_direction: null,
    oco_group_id: null,
    trailing_stop: null,
    ...overrides,
  };
}

function mockReturn(over: Record<string, unknown>) {
  mockUseCancelOrder.mockReturnValue({
    mutate: mockCancelOrder,
    isPending: false,
  });
  mockUseOrders.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...over,
  });
}

function withOrders(items: Order[]) {
  mockReturn({ data: { items, total: items.length } });
}

afterEach(() => {
  cleanup();
  mockUseOrders.mockReset();
  mockUseCancelOrder.mockReset();
  mockCancelOrder.mockReset();
});

describe("OrdersBlotter — 상태 4종", () => {
  it("로딩 — 스켈레톤 표를 그린다", () => {
    mockReturn({ isLoading: true });
    render(<OrdersBlotter />);
    expect(screen.getByTestId("order-skeleton")).toBeInTheDocument();
  });

  it("에러 — role=alert state-box + 실제 엔드포인트·HTTP 코드", () => {
    mockReturn({ isError: true, error: new Error("boom") });
    render(<OrdersBlotter />);
    const box = screen.getByTestId("order-error");
    expect(box).toBeInTheDocument();
    expect(box).toHaveAttribute("role", "alert");
    expect(screen.getByText("GET /api/v1/orders · 500")).toBeInTheDocument();
  });

  it("빈 상태 — 원장이 비면 안내 박스 + 코크핏 링크", () => {
    withOrders([]);
    render(<OrdersBlotter />);
    const box = screen.getByTestId("order-empty");
    expect(box).toBeInTheDocument();
    expect(screen.getByText("표시할 주문이 없습니다.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "트레이딩 코크핏 열기" })).toBeInTheDocument();
  });

  it("무데이터 셀 — 대기 주문의 체결가는 사유 title 을 단 빈 셀이다", () => {
    withOrders([makeOrder({ state: "pending", filled_price: null, exchange_order_id: null })]);
    const { container } = render(<OrdersBlotter />);
    expect(
      container.querySelector('[title="아직 체결되지 않아 체결가가 없습니다."]'),
    ).not.toBeNull();
    expect(
      container.querySelector('[title="아직 거래소로 보내지 않아 주문번호가 없습니다."]'),
    ).not.toBeNull();
  });
});

describe("OrdersBlotter — 프로토타입 시맨틱 구조", () => {
  it("상태 필터는 tablist 오용이 아니라 role=group + aria-pressed 다", () => {
    withOrders([makeOrder()]);
    render(<OrdersBlotter />);
    expect(screen.queryByRole("tablist")).toBeNull();
    const group = screen.getByRole("group", { name: "주문 상태 필터" });
    expect(group).toBeInTheDocument();
    const all = screen.getByTestId("order-filter-all");
    expect(all).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("order-filter-filled")).toHaveAttribute("aria-pressed", "false");
    expect(
      screen.getByText(
        "위 미체결 건수는 대기와 전송을 더한 값입니다. 사이드바 배지도 같은 미체결 주문 수를 표시합니다.",
      ),
    ).toBeInTheDocument();
  });

  it("주문 방향 배지는 .order-side.buy / .order-side.sell 를 쓴다(포지션 .side 와 분리)", () => {
    withOrders([
      makeOrder({ id: "b", side: "buy" }),
      makeOrder({ id: "s", side: "sell", state: "rejected", filled_price: null, exchange_order_id: null, error_message: "최소 주문 수량 미달" }),
    ]);
    const { container } = render(<OrdersBlotter />);
    const buy = container.querySelector(".order-side.buy");
    const sell = container.querySelector(".order-side.sell");
    expect(buy?.textContent).toBe("매수");
    expect(sell?.textContent).toBe("매도");
    // 포지션 방향 클래스는 이 화면에 없다.
    expect(container.querySelector(".side.long")).toBeNull();
    expect(container.querySelector(".side.short")).toBeNull();
  });

  it("체결 상태는 .chip.done, 거부 상태는 .chip.warn 톤을 쓴다", () => {
    withOrders([
      makeOrder({ id: "f", state: "filled" }),
      makeOrder({ id: "r", state: "rejected", filled_price: null, exchange_order_id: null, error_message: "최소 주문 수량 미달" }),
    ]);
    const { container } = render(<OrdersBlotter />);
    expect(container.querySelector(".chip.done")?.textContent).toContain("체결");
    expect(container.querySelector(".chip.warn")?.textContent).toContain("거부");
  });

  it("헤더는 10열이고 액션 열을 포함하며 청산가는 없다", () => {
    withOrders([makeOrder()]);
    render(<OrdersBlotter />);
    const headers = screen.getAllByRole("columnheader");
    expect(headers).toHaveLength(10);
    const texts = headers.map((h) => h.textContent);
    expect(texts).toContain("익절·손절");
    expect(texts).not.toContain("청산가");
    expect(texts).toContain("액션");
  });

  it("감소전용 배지 + title, 익절·손절 셀은 체결가 대비 거리를 함께 인쇄한다", () => {
    withOrders([
      makeOrder({
        reduce_only: true,
        take_profit: "64200.00",
        stop_loss: "61900.00",
        filled_price: "62880.00",
      }),
    ]);
    const { container } = render(<OrdersBlotter />);
    const badge = screen.getByText("감소전용");
    expect(badge).toHaveAttribute(
      "title",
      "열려 있는 포지션을 줄이는 주문입니다. 새 포지션을 만들지 않습니다.",
    );
    // 64200/62880-1 = +2.10% · 61900/62880-1 = -1.56%
    expect(
      container.querySelector(".col-tpsl .cell-sub")?.textContent,
    ).toBe("체결가 62880.00 대비 +2.10% / -1.56%");
  });

  it("출처 배지(브로커·모의)는 스키마 미백킹이라 렌더하지 않는다(§4.9)", () => {
    withOrders([makeOrder({ exchange_order_id: "78409188" })]);
    render(<OrdersBlotter />);
    // 뒤 8자만 표시, 브로커·모의 배지 없음.
    expect(screen.getByText("78409188")).toBeInTheDocument();
    expect(screen.queryByText("브로커")).toBeNull();
    expect(screen.queryByText("모의")).toBeNull();
  });

  it("대기·전송 주문에는 취소 버튼, terminal 주문에는 취소 불가 dim 셀을 그린다", () => {
    withOrders([
      makeOrder({ id: "p", state: "pending", filled_price: null, exchange_order_id: null }),
      makeOrder({ id: "s", state: "submitted", filled_price: null }),
      makeOrder({ id: "f", state: "filled" }),
      makeOrder({ id: "c", state: "cancelled", filled_price: null }),
      makeOrder({ id: "r", state: "rejected", filled_price: null, exchange_order_id: null }),
    ]);
    const { container } = render(<OrdersBlotter />);
    expect(screen.getAllByRole("button", { name: "주문 취소" })).toHaveLength(2);
    expect(
      container.querySelector('[title="이미 체결이 끝난 주문이라 취소할 수 없습니다."]'),
    ).toHaveClass("dim");
    expect(
      container.querySelector('[title="이미 취소된 주문입니다."]'),
    ).toHaveClass("dim");
    expect(
      container.querySelector('[title="이미 거부로 끝난 주문이라 취소할 수 없습니다."]'),
    ).toHaveClass("dim");
  });

  it("취소 버튼 클릭은 주문 ID로 mutation을 호출한다", () => {
    withOrders([makeOrder({ id: "p", state: "pending", filled_price: null, exchange_order_id: null })]);
    render(<OrdersBlotter />);
    fireEvent.click(screen.getByRole("button", { name: "주문 취소" }));
    expect(mockCancelOrder).toHaveBeenCalledWith("p");
  });

  it("202 취소 접수 응답을 파싱한다", () => {
    expect(
      CancelOrderResponseSchema.parse({
        order_id: "00000000-0000-4000-8000-000000000001",
        state: "submitted",
        detail: "exchange cancel requested",
      }),
    ).toMatchObject({ state: "submitted", detail: "exchange cancel requested" });
  });

  it("필터 토글 — 체결만 선택하면 거부 행이 사라진다", () => {
    withOrders([
      makeOrder({ id: "f", state: "filled" }),
      makeOrder({ id: "r", state: "rejected", filled_price: null, exchange_order_id: null, error_message: "err" }),
    ]);
    render(<OrdersBlotter />);
    expect(screen.getByTestId("order-row-f")).toBeInTheDocument();
    expect(screen.getByTestId("order-row-r")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("order-filter-filled"));
    expect(screen.getByTestId("order-row-f")).toBeInTheDocument();
    expect(screen.queryByTestId("order-row-r")).toBeNull();
    expect(screen.getByTestId("order-filter-filled")).toHaveAttribute("aria-pressed", "true");
  });
});
