/**
 * Sprint 12 Phase C — useOrders refetchInterval 분기 unit test.
 *
 * codex G3 #8 결정: useOrders 코드 자체는 이미 q.state.data?.items 기반 분기를
 * 처리하므로 hook 자체 수정 X. 단위 테스트만 추가하여 5s/30s 보장.
 *
 * computeOrdersRefetchInterval helper 를 통해 logic-only 검증.
 */
import { describe, expect, it } from "vitest";

import {
  ACTIVE_ORDER_STATES,
  ORDERS_REFETCH_INTERVAL_ACTIVE_MS,
  ORDERS_REFETCH_INTERVAL_IDLE_MS,
  computeOrdersRefetchInterval,
} from "../hooks";

describe("computeOrdersRefetchInterval", () => {
  it("returns 5s when at least one order is pending", () => {
    expect(
      computeOrdersRefetchInterval([{ state: "pending" }]),
    ).toBe(5_000);
    expect(ORDERS_REFETCH_INTERVAL_ACTIVE_MS).toBe(5_000);
  });

  it("returns 5s when at least one order is submitted", () => {
    expect(
      computeOrdersRefetchInterval([
        { state: "filled" },
        { state: "submitted" },
        { state: "cancelled" },
      ]),
    ).toBe(5_000);
  });

  it("returns 30s when all orders are terminal (filled/cancelled/rejected)", () => {
    expect(
      computeOrdersRefetchInterval([
        { state: "filled" },
        { state: "cancelled" },
        { state: "rejected" },
      ]),
    ).toBe(30_000);
    expect(ORDERS_REFETCH_INTERVAL_IDLE_MS).toBe(30_000);
  });

  it("returns 30s when orders array is empty", () => {
    expect(computeOrdersRefetchInterval([])).toBe(30_000);
  });

  it("ACTIVE_ORDER_STATES contains exactly pending and submitted", () => {
    expect(ACTIVE_ORDER_STATES.has("pending")).toBe(true);
    expect(ACTIVE_ORDER_STATES.has("submitted")).toBe(true);
    expect(ACTIVE_ORDER_STATES.has("filled")).toBe(false);
    expect(ACTIVE_ORDER_STATES.has("cancelled")).toBe(false);
    expect(ACTIVE_ORDER_STATES.has("rejected")).toBe(false);
  });
});
