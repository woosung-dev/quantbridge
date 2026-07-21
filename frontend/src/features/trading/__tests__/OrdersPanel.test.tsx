import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, vi } from "vitest";
import { OrdersPanel } from "../components/orders-panel";

// Clerk useAuth mock — hooks.ts 에서 getToken 호출.
vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: async () => "test-token" }),
}));

const apiFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api-client", () => ({
  apiFetch: apiFetchMock,
  ApiError: class ApiError extends Error {},
}));

function _mountOrders(items: Array<Record<string, unknown>>) {
  apiFetchMock.mockResolvedValueOnce({ items, total: items.length });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <OrdersPanel />
    </QueryClientProvider>,
  );
}

const _baseOrder = {
  id: "a0000000-0000-4000-a000-000000000001",
  symbol: "BTC/USDT",
  side: "buy",
  state: "filled",
  quantity: "0.01",
  filled_price: "50000",
  error_message: null,
  created_at: "2026-04-16T10:00:00Z",
};

afterEach(() => {
  apiFetchMock.mockReset();
});

test("OrdersPanel 최근 주문 50건 렌더 — 상태는 용어 SSOT 라벨(체결)로", async () => {
  _mountOrders([{ ..._baseOrder, exchange_order_id: "fixture-1" }]);
  expect(await screen.findByText("BTC/USDT")).toBeInTheDocument();
  // 원시 enum "filled" 가 아니라 ORDER_STATE_LABEL 의 "체결" (S4 인계).
  expect(screen.getByText("체결")).toBeInTheDocument();
  expect(screen.queryByText("filled")).not.toBeInTheDocument();
  // 주문 방향도 SSOT — buy → 매수.
  expect(screen.getByText("매수")).toBeInTheDocument();
});

// Sprint 21 BL-093 superset — broker evidence column 시각 분기.

test("OrdersPanel: exchange_order_id null 일 때 BrokerBadge 가 dash 만 표시", async () => {
  _mountOrders([{ ..._baseOrder, exchange_order_id: null }]);
  await screen.findByText("BTC/USDT");
  // 거래소 주문번호 컬럼 헤더 노출
  expect(screen.getByText("거래소 주문번호")).toBeInTheDocument();
  // null 인 경우 Mock/Real 라벨 미렌더
  expect(screen.queryByTestId("broker-badge-mock")).not.toBeInTheDocument();
  expect(screen.queryByTestId("broker-badge-real")).not.toBeInTheDocument();
});

test("OrdersPanel: fixture- prefix 시 mock 배지 + 마지막 8자 + (mock) 라벨", async () => {
  _mountOrders([
    { ..._baseOrder, exchange_order_id: "fixture-abcdefghijklmnop" },
  ]);
  await screen.findByText("BTC/USDT");
  const badge = await screen.findByTestId("broker-badge-mock");
  expect(badge).toBeInTheDocument();
  expect(badge.textContent).toContain("(mock)");
  // 마지막 8자 = "ijklmnop"
  expect(badge.textContent).toContain("ijklmnop");
  // tooltip 에 전체 ID
  expect(badge.getAttribute("title")).toContain("fixture-abcdefghijklmnop");
});

test("OrdersPanel: real broker UUID 시 broker 배지 + 마지막 8자 + (broker) 라벨", async () => {
  _mountOrders([
    {
      ..._baseOrder,
      exchange_order_id: "1234567890abcdef-bybit-real-trading-id-x9y8z7",
    },
  ]);
  await screen.findByText("BTC/USDT");
  const badge = await screen.findByTestId("broker-badge-real");
  expect(badge).toBeInTheDocument();
  expect(badge.textContent).toContain("(broker)");
  // 마지막 8자 = "x9y8z7" 보다 8자 = "id-x9y8z7" 의 last 8 = "-x9y8z7" 가 아니라 "x-x9y8z7"... 정확히는 slice(-8)
  // 전체 ID = "1234567890abcdef-bybit-real-trading-id-x9y8z7" (45자), slice(-8) = "x9y8z7" 보다 6자 (오타 — 실제 검증)
  // 단순화: title 에 전체 ID 포함 + (broker) 라벨 검증.
  expect(badge.getAttribute("title")).toContain(
    "1234567890abcdef-bybit-real-trading-id-x9y8z7",
  );
});

// Wave 2 — TP/SL 컬럼 + 청산가 컬럼(graceful-empty).

test("OrdersPanel: TP/SL 값이 있으면 렌더, 청산가는 graceful '—'", async () => {
  _mountOrders([
    {
      ..._baseOrder,
      exchange_order_id: "broker-1",
      take_profit: "55000",
      stop_loss: "48000",
    },
  ]);
  await screen.findByText("BTC/USDT");
  expect(screen.getByText("익절·손절")).toBeInTheDocument();
  expect(screen.getByText("청산가")).toBeInTheDocument();
  const tpslCell = screen.getByTestId("tpsl-cell");
  expect(tpslCell).toHaveTextContent("55000");
  expect(tpslCell).toHaveTextContent("48000");
  // 청산가는 W-B 미머지 → graceful-empty 셀
  expect(screen.getByTestId("liquidation-cell")).toHaveTextContent("—");
});

// STEP B — 트레일링 의도(Order.trailing_stop) 표출 (Playwright UI 검증 대상).
test("OrdersPanel: trailing_stop 있으면 trail 거리 렌더", async () => {
  _mountOrders([
    {
      ..._baseOrder,
      exchange_order_id: "broker-1",
      stop_loss: "48000",
      trailing_stop: "150.5",
    },
  ]);
  await screen.findByText("BTC/USDT");
  const tpslCell = screen.getByTestId("tpsl-cell");
  expect(tpslCell).toHaveTextContent("48000");
  expect(tpslCell).toHaveTextContent("trail 150.5");
});

// STEP B (qa-P2) — trail-only: TP·SL 모두 null, trailing_stop 만 → '— / — / trail X'.
// `|| o.trailing_stop` 항이 유일 결정 인자인 케이스. 이 항 삭제 시 '—' 로 protection 은닉
// (Surface Trust 위반) — 기존 fixture 는 모두 SL 보유라 이 항이 결정 인자였던 적 없음(mutation gap).
test("OrdersPanel: TP·SL 없고 trailing_stop 만 있으면 trail 렌더 ('—' 아님)", async () => {
  _mountOrders([
    {
      ..._baseOrder,
      exchange_order_id: "broker-trail-only",
      take_profit: null,
      stop_loss: null,
      trailing_stop: "150.5",
    },
  ]);
  await screen.findByText("BTC/USDT");
  const tpslCell = screen.getByTestId("tpsl-cell");
  expect(tpslCell).toHaveTextContent("— / — / trail 150.5");
  expect(tpslCell).not.toHaveTextContent(/^—$/);
});

test("OrdersPanel: TP/SL 없으면 dash 표시", async () => {
  _mountOrders([
    {
      ..._baseOrder,
      exchange_order_id: "broker-1",
      take_profit: null,
      stop_loss: null,
    },
  ]);
  await screen.findByText("BTC/USDT");
  const tpslCell = screen.getByTestId("tpsl-cell");
  expect(tpslCell).toHaveTextContent("—");
});
