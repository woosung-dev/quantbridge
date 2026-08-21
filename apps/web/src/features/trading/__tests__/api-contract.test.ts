// Trading REST 래퍼의 주문 필터·청산가 요청 wire 계약을 고정한다.
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import { getLiquidationInfo, listOrders } from "../api";

const ORDER = {
  id: "00000000-0000-4000-a000-000000000011",
  symbol: "BTC/USDT:USDT",
  side: "buy",
  state: "pending",
  quantity: "0.01",
  filled_price: null,
  exchange_order_id: null,
  error_message: null,
  created_at: "2026-08-22T00:00:00Z",
};

afterEach(() => {
  apiFetchMock.mockReset();
});

describe("trading API contract", () => {
  it("주문 상태 필터는 반복 query string과 페이지 파라미터를 함께 전달한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [ORDER], total: 1 });

    await expect(listOrders(50, "jwt", { states: ["pending", "filled"] })).resolves.toEqual({
      items: [expect.objectContaining(ORDER)],
      total: 1,
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/orders?state=pending&state=filled", {
      method: "GET",
      token: "jwt",
      params: { limit: 50, offset: 0 },
    });
  });

  it("청산가 미리보기는 요청 값을 POST body로 보존하고 숫자 응답을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      symbol: "BTC/USDT:USDT",
      entry_price: "100000",
      side: "buy",
      leverage: 5,
      liquidation_price: "80200",
      maintenance_margin_rate: "0.005",
      distance_pct: "19.8",
    });

    await expect(
      getLiquidationInfo(
        { symbol: "BTC/USDT:USDT", side: "buy", entry_price: "100000", leverage: 5 },
        "jwt",
      ),
    ).resolves.toMatchObject({ liquidation_price: "80200", leverage: 5 });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/liquidation/preview", {
      method: "POST",
      token: "jwt",
      body: { symbol: "BTC/USDT:USDT", side: "buy", entry_price: "100000", leverage: 5 },
    });
  });
});
