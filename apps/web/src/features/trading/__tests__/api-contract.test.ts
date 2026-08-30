// Trading REST 래퍼의 정상 경로·응답 스키마 계약을 고정한다.
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import {
  cancelOrder,
  deleteExchangeAccount,
  getAccountBalance,
  getLiquidationInfo,
  listExchangeAccounts,
  listKillSwitchEvents,
  listOrders,
  registerExchangeAccount,
  resolveKillSwitchEvent,
} from "../api";

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

const ACCOUNT = {
  id: "00000000-0000-4000-a000-000000000012",
  exchange: "bybit",
  mode: "demo",
  label: "Demo futures",
  api_key_masked: "abcd****wxyz",
  exchange_uid: null,
  read_only: null,
  created_at: "2026-08-22T00:00:00Z",
};

afterEach(() => {
  apiFetchMock.mockReset();
});

describe("trading API contract", () => {
  it("상태 필터가 없고 limit=0이면 query 없이 빈 페이지를 요청한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 0 });

    await expect(listOrders(0, null)).resolves.toEqual({ items: [], total: 0 });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/orders", {
      method: "GET",
      token: null,
      params: { limit: 0, offset: 0 },
    });
  });

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
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("주문 취소는 cancel POST의 acknowledgement를 파싱한다", async () => {
    const acknowledgement = {
      order_id: ORDER.id,
      state: "submitted",
      detail: "exchange cancel requested",
    };
    apiFetchMock.mockResolvedValueOnce(acknowledgement);

    await expect(cancelOrder(ORDER.id, "jwt")).resolves.toEqual(acknowledgement);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/orders/${ORDER.id}/cancel`, {
      method: "POST",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("주문 취소 API 오류는 status·code가 든 같은 Error 객체를 그대로 전파한다", async () => {
    const { ApiError } =
      await vi.importActual<typeof import("@/lib/api-client")>("@/lib/api-client");
    const apiError = new ApiError(
      409,
      "order_not_cancellable",
      "API 409 /api/v1/orders/order/cancel",
    );
    apiFetchMock.mockRejectedValueOnce(apiError);

    await expect(cancelOrder(ORDER.id, "jwt")).rejects.toBe(apiError);
    expect(apiError).toMatchObject({ status: 409, code: "order_not_cancellable" });
  });

  it("킬 스위치 목록은 기본 limit와 GET 인증을 전달한다", async () => {
    const event = {
      id: "00000000-0000-4000-a000-000000000013",
      trigger_type: "daily_loss",
      trigger_value: "101",
      threshold: "100",
      triggered_at: "2026-08-22T00:00:00Z",
      resolved_at: null,
    };
    apiFetchMock.mockResolvedValueOnce({ items: [event] });

    await expect(listKillSwitchEvents("jwt")).resolves.toEqual({ items: [event] });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/kill-switch/events", {
      method: "GET",
      token: "jwt",
      params: { limit: 20 },
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("킬 스위치 목록은 0 limit도 기본값으로 바꾸지 않는다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [] });

    await expect(listKillSwitchEvents("jwt", 0)).resolves.toEqual({ items: [] });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/kill-switch/events", {
      method: "GET",
      token: "jwt",
      params: { limit: 0 },
    });
  });

  it("킬 스위치 해제는 기본 관리 메모를 POST body로 보낸다", async () => {
    const eventId = "00000000-0000-4000-a000-000000000014";
    apiFetchMock.mockResolvedValueOnce(undefined);

    await expect(resolveKillSwitchEvent(eventId, "jwt")).resolves.toBeUndefined();

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/kill-switch/events/${eventId}/resolve`, {
      method: "POST",
      token: "jwt",
      body: { note: "manual unlock from dashboard" },
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("거래소 계정 목록은 GET 응답의 items만 반환한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [ACCOUNT] });

    await expect(listExchangeAccounts("jwt")).resolves.toEqual([ACCOUNT]);

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/exchange-accounts", {
      method: "GET",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("계정 잔고는 account 경로의 GET 응답을 파싱한다", async () => {
    const balance = {
      account_id: ACCOUNT.id,
      asset: "USDT",
      supported: true,
      reason: null,
      total: "1000",
      free: "900",
      fetched_at: "2026-08-22T00:00:00Z",
    };
    apiFetchMock.mockResolvedValueOnce(balance);

    await expect(getAccountBalance(ACCOUNT.id, "jwt")).resolves.toEqual(balance);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/exchange-accounts/${ACCOUNT.id}/balance`, {
      method: "GET",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("거래소 계정 등록은 API 키 요청 body를 POST하고 응답을 파싱한다", async () => {
    const request = {
      label: "Demo futures",
      api_key: "test-api-key",
      api_secret: "test-api-secret",
    };
    apiFetchMock.mockResolvedValueOnce(ACCOUNT);

    await expect(registerExchangeAccount(request, "jwt")).resolves.toEqual(ACCOUNT);

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/exchange-accounts", {
      method: "POST",
      token: "jwt",
      body: request,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("거래소 계정 응답이 계약을 어기면 Zod parse 오류로 중단한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ ...ACCOUNT, api_key_masked: null });

    await expect(listExchangeAccounts("jwt")).rejects.toThrow();
  });

  it("거래소 계정 삭제는 식별자 DELETE와 인증만 전달한다", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);

    await expect(deleteExchangeAccount(ACCOUNT.id, "jwt")).resolves.toBeUndefined();

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/exchange-accounts/${ACCOUNT.id}`, {
      method: "DELETE",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
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
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });
});
