// 주문 원장(OrdersBlotter) — C 이식(W3-D) 상태 4종 + 프로토타입 시맨틱 구조 회귀 가드.
// useOrders 를 목으로 갈아끼워 로딩/에러/빈/데이터 경로를 각각 렌더하고, 프로토타입 유래
// 핵심 클래스(role=group 필터 · .order-side.buy/.sell · .chip.done · 12열 헤더 · 무데이터 title)를
// assert 한다. 라벨은 전부 용어 SSOT 에서 오므로 원시 enum 이 새어 나오지 않는지도 함께 본다.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";

import { OrdersBlotter } from "@/features/trading/components/orders/orders-blotter";
import { ORDER_REALIZED_PNL_SOURCE_HINT } from "@/features/trading/labels";
import { CancelOrderResponseSchema, type Order } from "@/features/trading/schemas";
import { EMPTY_CELL } from "@/lib/labels";
import type * as TradingHooks from "@/features/trading/hooks";
import type * as BacktestUtils from "@/features/backtest/utils";

const mockUseOrders = vi.fn();
const mockUseCancelOrder = vi.fn();
const mockCancelOrder = vi.fn();
const mockDownloadCsv = vi.fn();
vi.mock("@/features/trading/hooks", async (importOriginal) => {
  const actual = await importOriginal<typeof TradingHooks>();
  return {
    ...actual,
    useOrders: (...args: unknown[]) => mockUseOrders(...args),
    useCancelOrder: () => mockUseCancelOrder(),
  };
});
vi.mock("@/features/backtest/utils", async (importOriginal) => {
  const actual = await importOriginal<typeof BacktestUtils>();
  return {
    ...actual,
    downloadCsv: (...args: unknown[]) => mockDownloadCsv(...args),
  };
});

function makeOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: "00000000-0000-4000-8000-000000000001",
    strategy_id: "00000000-0000-4000-8000-000000000111",
    exchange_account_id: "00000000-0000-4000-8000-000000000222",
    symbol: "BTC/USDT",
    side: "buy",
    type: "market",
    price: null,
    state: "filled",
    quantity: "0.021",
    idempotency_key: "order-0001",
    filled_price: "62880.00",
    exchange_order_id: "78409188",
    error_message: null,
    submitted_at: "2026-04-14T20:00:01Z",
    filled_at: "2026-04-14T20:00:04Z",
    created_at: "2026-04-14T20:00:04Z",
    leverage: 5,
    margin_mode: "isolated",
    reduce_only: false,
    trigger_price: null,
    trigger_by: null,
    take_profit: null,
    stop_loss: null,
    trigger_direction: null,
    oco_group_id: null,
    trailing_stop: null,
    filled_quantity: null,
    realized_pnl: null,
    realized_pnl_synced_at: null,
    ...overrides,
  };
}

function mockReturn(over: Record<string, unknown>) {
  mockUseCancelOrder.mockReturnValue({
    mutate: mockCancelOrder,
    isPending: false,
    variables: undefined,
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
  mockDownloadCsv.mockReset();
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
    const cells = within(
      screen.getByTestId("order-row-00000000-0000-4000-8000-000000000001"),
    ).getAllByRole("cell");
    expect(cells[5]!).toHaveTextContent(EMPTY_CELL);
    expect(cells[6]!).toHaveTextContent(EMPTY_CELL);
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
      makeOrder({
        id: "s",
        side: "sell",
        state: "rejected",
        filled_price: null,
        exchange_order_id: null,
        error_message: "최소 주문 수량 미달",
      }),
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
      makeOrder({
        id: "r",
        state: "rejected",
        filled_price: null,
        exchange_order_id: null,
        error_message: "최소 주문 수량 미달",
      }),
    ]);
    const { container } = render(<OrdersBlotter />);
    expect(container.querySelector(".chip.done")?.textContent).toContain("체결");
    expect(container.querySelector(".chip.warn")?.textContent).toContain("거부");
  });

  it("헤더는 12열이고 체결가 뒤에 체결 수량·실현 손익과 액션 열을 포함하며 청산가는 없다", () => {
    withOrders([makeOrder()]);
    render(<OrdersBlotter />);
    const headers = screen.getAllByRole("columnheader");
    expect(headers).toHaveLength(12);
    const texts = headers.map((h) => h.textContent);
    expect(texts.slice(4, 7)).toEqual(["체결가", "체결 수량", "실현 손익"]);
    expect(texts).toContain("익절·손절");
    expect(texts).not.toContain("청산가");
    expect(texts).toContain("액션");
  });

  it("부분체결 수량과 실현 손익 출처·색상을 표시한다", () => {
    withOrders([
      makeOrder({
        id: "confirmed",
        quantity: "1",
        filled_quantity: "0.5",
        realized_pnl: "12.34",
        realized_pnl_synced_at: "2026-04-14T20:00:05Z",
      }),
      makeOrder({ id: "estimated", realized_pnl: "-2.50" }),
    ]);
    render(<OrdersBlotter />);

    const confirmedCells = within(screen.getByTestId("order-row-confirmed")).getAllByRole("cell");
    expect(confirmedCells[5]!).toHaveTextContent("0.5 부분");
    expect(within(confirmedCells[5]!).getByText("부분")).toHaveAttribute(
      "title",
      "주문 수량 1 중 0.5 체결",
    );
    expect(confirmedCells[6]!).toHaveClass("num", "pos");
    expect(within(confirmedCells[6]!).getByText("거래소 확정")).toHaveAttribute(
      "title",
      "거래소가 확정한 정산 손익",
    );

    const estimatedCells = within(screen.getByTestId("order-row-estimated")).getAllByRole("cell");
    expect(estimatedCells[6]!).toHaveClass("num", "neg");
    expect(within(estimatedCells[6]!).getByText("추정")).toHaveAttribute(
      "title",
      ORDER_REALIZED_PNL_SOURCE_HINT.estimated,
    );
  });

  it("거부된 주문에 남은 추정 손익은 표시하지 않는다", () => {
    withOrders([
      makeOrder({
        id: "rejected-pnl",
        state: "rejected",
        filled_price: null,
        exchange_order_id: null,
        realized_pnl: "-1007.70000000",
      }),
    ]);
    render(<OrdersBlotter />);

    const cells = within(screen.getByTestId("order-row-rejected-pnl")).getAllByRole("cell");
    expect(cells[6]!).toHaveTextContent(EMPTY_CELL);
    expect(cells[6]!).toHaveClass("dim");
    expect(within(cells[6]!).queryByText("추정")).toBeNull();
  });

  it("체결된 주문의 실현 손익과 출처 배지는 표시한다", () => {
    withOrders([makeOrder({ id: "filled-pnl", realized_pnl: "12.34" })]);
    render(<OrdersBlotter />);

    const cells = within(screen.getByTestId("order-row-filled-pnl")).getAllByRole("cell");
    expect(cells[6]!).toHaveTextContent("12.34");
    expect(within(cells[6]!).getByText("추정")).toBeInTheDocument();
  });

  it("취소된 주문에 남은 실현 손익은 표시하지 않는다", () => {
    withOrders([
      makeOrder({
        id: "cancelled-pnl",
        state: "cancelled",
        filled_price: null,
        realized_pnl: "-1.00",
      }),
    ]);
    render(<OrdersBlotter />);

    const cells = within(screen.getByTestId("order-row-cancelled-pnl")).getAllByRole("cell");
    expect(cells[6]!).toHaveTextContent(EMPTY_CELL);
    expect(cells[6]!).toHaveClass("dim");
    expect(within(cells[6]!).queryByText("추정")).toBeNull();
  });

  it("체결 전 주문에 미리 기록된 추정 손익도 표시하지 않는다", () => {
    // 손익은 close 주문 생성 시점(state=pending)에 이미 기록되므로 이게 가장 흔한 경우다.
    withOrders([
      makeOrder({ id: "pending-pnl", state: "pending", filled_price: null, realized_pnl: "-3.00" }),
      makeOrder({
        id: "submitted-pnl",
        state: "submitted",
        filled_price: null,
        realized_pnl: "-4.00",
      }),
    ]);
    render(<OrdersBlotter />);

    for (const id of ["pending-pnl", "submitted-pnl"]) {
      const cells = within(screen.getByTestId(`order-row-${id}`)).getAllByRole("cell");
      expect(cells[6]!).toHaveTextContent(EMPTY_CELL);
      // 값을 감췄는데 부호 톤만 남으면 여전히 손실처럼 읽힌다.
      expect(cells[6]!).not.toHaveClass("neg");
      expect(cells[6]!).not.toHaveClass("pos");
    }
  });

  it("감춘 손익 셀은 왜 비었는지 상태별 사유를 밝힌다", () => {
    withOrders([
      makeOrder({
        id: "reason-rejected",
        state: "rejected",
        filled_price: null,
        exchange_order_id: null,
        realized_pnl: "-1007.70000000",
      }),
    ]);
    render(<OrdersBlotter />);

    const cells = within(screen.getByTestId("order-row-reason-rejected")).getAllByRole("cell");
    expect(cells[6]!).toHaveAttribute("title", "거부된 주문이라 자금이 움직이지 않았습니다.");
  });

  it("CSV는 손익 출처·날짜·부분체결을 보존하고 모든 행의 열 수를 맞춘다", async () => {
    withOrders([
      makeOrder({
        id: "confirmed-csv",
        symbol: "BTC/USDT",
        quantity: "1",
        filled_quantity: "0.5",
        realized_pnl: "12.34",
        realized_pnl_synced_at: "2026-04-14T20:00:05Z",
      }),
      makeOrder({
        id: "estimated-csv",
        symbol: "ETH/USDT",
        quantity: "1",
        filled_quantity: "1",
        realized_pnl: "-2.50",
      }),
      makeOrder({
        id: "rejected-csv",
        symbol: "SOL/USDT",
        state: "rejected",
        filled_price: null,
        exchange_order_id: null,
        realized_pnl: "-1007.70000000",
      }),
    ]);
    render(<OrdersBlotter />);
    fireEvent.click(screen.getByRole("button", { name: "CSV 내보내기" }));

    const csv = mockDownloadCsv.mock.calls[0]![1] as string;
    const rows = csv.split("\n").map((line) => line.slice(1, -1).split('","'));
    const [header, ...dataRows] = rows;
    const sourceIndex = header!.indexOf("손익 출처");
    const filledQuantityIndex = header!.indexOf("체결 수량");
    const timeIndex = header!.indexOf("시각");
    const realizedPnlIndex = header!.indexOf("실현 손익");

    expect(sourceIndex).toBeGreaterThan(realizedPnlIndex);
    expect(dataRows.every((row) => row.length === header!.length)).toBe(true);
    expect(dataRows.find((row) => row[1] === "BTC/USDT")![sourceIndex]).toBe("거래소 확정");
    expect(dataRows.find((row) => row[1] === "ETH/USDT")![sourceIndex]).toBe("추정");
    const rejected = dataRows.find((row) => row[1] === "SOL/USDT")!;
    expect(rejected[sourceIndex]).toBe("");
    expect(rejected[realizedPnlIndex]).toBe("");
    expect(dataRows[0]![timeIndex]).toContain("2026-04-14");
    expect(dataRows.find((row) => row[1] === "BTC/USDT")![filledQuantityIndex]).toBe("0.5 부분");
    expect(dataRows.find((row) => row[1] === "ETH/USDT")![filledQuantityIndex]).toBe("1");
  });

  it("본전 손익 0 은 무데이터로 숨기지 않고, 표기만 다른 완전체결은 부분으로 읽지 않는다", () => {
    withOrders([
      makeOrder({
        id: "breakeven",
        quantity: "0.001",
        filled_quantity: "0.0010",
        realized_pnl: "0",
      }),
    ]);
    render(<OrdersBlotter />);

    const cells = within(screen.getByTestId("order-row-breakeven")).getAllByRole("cell");
    // 소수 표기만 다른 완전체결("0.0010" vs "0.001")을 부분체결로 오독하면 안 된다.
    expect(cells[5]!).toHaveTextContent("0.0010");
    expect(within(cells[5]!).queryByText("부분")).toBeNull();
    // 본전 트레이드의 0 은 실제 값이라 EMPTY_CELL 로 숨기지 않는다(색은 중립).
    expect(cells[6]!.textContent).not.toContain(EMPTY_CELL);
    expect(within(cells[6]!).getByText("추정")).toBeInTheDocument();
    expect(cells[6]!).not.toHaveClass("pos");
    expect(cells[6]!).not.toHaveClass("neg");
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
    expect(container.querySelector(".col-tpsl .cell-sub")?.textContent).toBe(
      "체결가 62880.00 대비 +2.10% / -1.56%",
    );
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
    expect(container.querySelector('[title="이미 취소된 주문입니다."]')).toHaveClass("dim");
    expect(
      container.querySelector('[title="이미 거부로 끝난 주문이라 취소할 수 없습니다."]'),
    ).toHaveClass("dim");
  });

  it("행 클릭과 Enter·Space 키로 상세를 열고 닫는다", () => {
    withOrders([makeOrder()]);
    render(<OrdersBlotter />);

    const row = screen.getByTestId("order-row-00000000-0000-4000-8000-000000000001");
    fireEvent.click(row);
    expect(screen.getByRole("dialog", { name: "BTC/USDT 주문 상세" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "닫기" }));
    expect(screen.queryByRole("dialog")).toBeNull();

    fireEvent.keyDown(row, { key: "Enter" });
    expect(screen.getByRole("dialog", { name: "BTC/USDT 주문 상세" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "닫기" }));

    fireEvent.keyDown(row, { key: " " });
    expect(screen.getByRole("dialog", { name: "BTC/USDT 주문 상세" })).toBeInTheDocument();
  });

  // ★2026-08-15 codex 적대 리뷰 P1 — 드로어가 금융 값을 오표시했다.
  it("거부 주문의 상세는 실패 시각을 체결로 적지 않고, 추정 손익을 확정처럼 보이지 않는다", () => {
    withOrders([
      makeOrder({
        state: "rejected",
        // BE `mark_rejected` 는 `filled_at` 자리에 **실패 시각**을 쓴다
        // (`apps/api/src/trading/repositories/order_repository.py:941-945`).
        filled_at: "2026-06-26T10:00:05Z",
        // rejected 에 남은 값은 close 주문 생성 시점의 pine_v2 **추정치**다.
        realized_pnl: "-111.70",
        error_message: "insufficient margin",
      }),
    ]);
    render(<OrdersBlotter />);

    fireEvent.click(screen.getByTestId("order-row-00000000-0000-4000-8000-000000000001"));
    const dialog = screen.getByRole("dialog", { name: "BTC/USDT 주문 상세" });

    expect(within(dialog).getByText("실패 시각")).toBeInTheDocument();
    expect(within(dialog).queryByText("체결 시각")).toBeNull();
    expect(within(dialog).queryByText("-111.70")).toBeNull();
  });

  it("★음성 대조 — 체결 주문은 여전히 체결 시각과 확정 손익을 보여준다", () => {
    withOrders([
      makeOrder({
        state: "filled",
        filled_at: "2026-06-26T10:00:05Z",
        realized_pnl: "12.34",
        realized_pnl_synced_at: "2026-06-26T10:00:06Z",
      }),
    ]);
    render(<OrdersBlotter />);

    fireEvent.click(screen.getByTestId("order-row-00000000-0000-4000-8000-000000000001"));
    const dialog = screen.getByRole("dialog", { name: "BTC/USDT 주문 상세" });

    expect(within(dialog).getByText("체결 시각")).toBeInTheDocument();
    expect(within(dialog).queryByText("실패 시각")).toBeNull();
    expect(within(dialog).getByText("12.34")).toBeInTheDocument();
  });

  it("취소 버튼 클릭은 주문 ID로 mutation을 호출한다", () => {
    withOrders([
      makeOrder({ id: "p", state: "pending", filled_price: null, exchange_order_id: null }),
    ]);
    render(<OrdersBlotter />);
    fireEvent.click(screen.getByRole("button", { name: "주문 취소" }));
    expect(mockCancelOrder).toHaveBeenCalledWith("p");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("진행 중인 취소는 해당 주문 행만 비활성화한다", () => {
    withOrders([
      makeOrder({ id: "p", state: "pending", filled_price: null, exchange_order_id: null }),
      makeOrder({ id: "s", state: "submitted", filled_price: null }),
    ]);
    mockUseCancelOrder.mockReturnValue({
      mutate: mockCancelOrder,
      isPending: true,
      variables: "p",
    });

    render(<OrdersBlotter />);

    expect(
      within(screen.getByTestId("order-row-p")).getByRole("button", { name: "주문 취소" }),
    ).toBeDisabled();
    expect(
      within(screen.getByTestId("order-row-s")).getByRole("button", { name: "주문 취소" }),
    ).toBeEnabled();
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

  // 2026-08-18 — 헤더 신뢰 장치 3종 (⑤ Bybit 데모 chip · ⑥ 단일 새로고침 CTA · ⑦ 마지막 갱신).
  it("헤더 chip 은 「Bybit 데모」다 — 계정 모드가 Bybit demo 뿐이라는 페이지 수준 사실", () => {
    withOrders([makeOrder()]);
    render(<OrdersBlotter />);
    expect(screen.getByText("Bybit 데모")).toBeInTheDocument();
    // 모드 없는 종전 하드코딩 "Bybit" 단독 chip 은 남지 않는다.
    expect(screen.queryByText(/^Bybit$/)).toBeNull();
  });

  it("새로고침 CTA 는 폴링 문맥의 「지금 새로고침」 하나뿐이다", () => {
    withOrders([makeOrder()]);
    render(<OrdersBlotter />);
    expect(screen.getByRole("button", { name: "지금 새로고침" })).toBeInTheDocument();
    // report-actions 의 중복 「새로고침」 버튼은 제거됐다.
    expect(screen.queryByRole("button", { name: "새로고침" })).toBeNull();
  });

  it("마지막 갱신 chip — dataUpdatedAt 을 mono 시각(UTC HH:MM:SS)으로 인쇄한다", () => {
    mockReturn({
      data: { items: [makeOrder()], total: 1 },
      dataUpdatedAt: Date.UTC(2026, 3, 14, 21, 7, 3),
    });
    render(<OrdersBlotter />);
    const chip = screen.getByTestId("orders-last-updated");
    expect(chip).toHaveTextContent("마지막 갱신 21:07:03");
    const time = within(chip).getByText("21:07:03");
    expect(time).toHaveClass("mono");
  });

  it("아직 한 번도 수신하지 못했으면(dataUpdatedAt=0) 마지막 갱신 chip 을 그리지 않는다", () => {
    mockReturn({ data: { items: [], total: 0 }, dataUpdatedAt: 0 });
    render(<OrdersBlotter />);
    expect(screen.queryByTestId("orders-last-updated")).toBeNull();
  });

  it("필터 토글 — 체결만 선택하면 거부 행이 사라진다", () => {
    withOrders([
      makeOrder({ id: "f", state: "filled" }),
      makeOrder({
        id: "r",
        state: "rejected",
        filled_price: null,
        exchange_order_id: null,
        error_message: "err",
      }),
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
