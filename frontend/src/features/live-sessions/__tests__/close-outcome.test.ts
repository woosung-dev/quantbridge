// 청산 응답/에러 → 화면 상태 매핑. 순수 함수라 React 없이 잰다.
//
// ★이 매핑이 이 회차의 계약이다. CLI(`live_session_admin.py:374-423`)가 rc 0/3/4 로
//   가르는 것과 **같은 갈래**를 화면이 갖게 한다 — 특히 「잔량 0」과 「못 물어봤다」가
//   서로 다른 상태여야 한다. 빈 목록 하나로 둘을 표현하면 그것이 [BL-684] 가 지목한
//   거짓 성공의 화면 축이다.
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api-client";

import { outcomeFromError, outcomeFromResponse } from "../close-outcome";
import { ClosePositionResponseSchema } from "../schemas";

const ORDER = {
  order_id: "abc123",
  side: "buy",
  qty: "0.029",
  trigger_price: "100",
  order_link_id: "link-1",
};

/** 409 는 FastAPI 가 `{"detail": <서비스가 준 dict>}` 로 한 겹 감싼다. */
function conflictBody(orders: unknown[], count = orders.length) {
  return {
    detail: {
      code: "resting_conditional_entries",
      count,
      detail: `포지션은 없지만 미체결 진입 주문 ${count}건이 남아 있습니다.`,
      orders,
    },
  };
}

describe("outcomeFromResponse", () => {
  it("잔량 0 이고 조회도 성공했으면 clean 이다", () => {
    const res = ClosePositionResponseSchema.parse({
      order_id: "order-1",
      state: "submitted",
      detail: "reduce-only market close accepted",
      resting_entries: [],
      resting_entries_unknown: false,
    });
    expect(outcomeFromResponse(res)).toEqual({
      kind: "clean",
      orderId: "order-1",
      state: "submitted",
    });
  });

  it("잔량이 있으면 accepted_with_resting 이고 주문을 그대로 들고 간다", () => {
    const res = ClosePositionResponseSchema.parse({
      order_id: "order-1",
      state: "submitted",
      detail: "reduce-only market close accepted · 미체결 진입 주문 1건이 남아 있다",
      resting_entries: [ORDER],
      resting_entries_unknown: false,
    });
    const outcome = outcomeFromResponse(res);
    expect(outcome.kind).toBe("accepted_with_resting");
    expect(outcome.kind === "accepted_with_resting" && outcome.orders).toEqual([ORDER]);
  });

  it("조회 실패는 accepted_unknown 이다 — 잔량 0 과 같은 상태가 아니다", () => {
    const res = ClosePositionResponseSchema.parse({
      order_id: "order-1",
      state: "submitted",
      detail: "reduce-only market close accepted · 미체결 진입 주문 확인 실패",
      resting_entries: [],
      resting_entries_unknown: true,
    });
    expect(outcomeFromResponse(res).kind).toBe("accepted_unknown");
  });

  it("빈 목록 + unknown 은 accepted_unknown 이다 — 빈 목록이 '없다'의 증거가 아니다", () => {
    const res = ClosePositionResponseSchema.parse({
      order_id: "order-1",
      state: "submitted",
      detail: null,
      resting_entries: [],
      resting_entries_unknown: true,
    });
    expect(outcomeFromResponse(res).kind).toBe("accepted_unknown");
  });

  it("★목록이 있어도 unknown 이면 unknown 이 이긴다 (우리가 고르는 우선순위)", () => {
    // ★이 조합은 **오늘 서버가 만들지 않는다** — 실패 시 `entries = []` 로 리셋한다.
    //   그래서 위의 빈-목록 케이스만으로는 우선순위가 고정되지 않는다(변이가 초록으로
    //   빠져나갔다). 서버가 언젠가 부분 성공을 보내면 목록은 **불완전**하므로 「잔량
    //   N건」이라고 단정해서는 안 된다 — 그 선택을 여기서 못 박는다.
    const res = ClosePositionResponseSchema.parse({
      order_id: "order-1",
      state: "submitted",
      detail: null,
      resting_entries: [ORDER],
      resting_entries_unknown: true,
    });
    expect(outcomeFromResponse(res).kind).toBe("accepted_unknown");
  });

  it("두 필드가 없는 구 응답은 clean 으로 읽는다 (스키마 기본값)", () => {
    const res = ClosePositionResponseSchema.parse({
      order_id: "order-1",
      state: "submitted",
      detail: null,
    });
    expect(outcomeFromResponse(res).kind).toBe("clean");
  });
});

describe("outcomeFromError", () => {
  it("409 resting_conditional_entries 는 blocked_resting 이고 주문 목록을 편다", () => {
    const err = new ApiError(409, "unknown_error", "API 409 /x", conflictBody([ORDER]));
    const outcome = outcomeFromError(err);
    expect(outcome.kind).toBe("blocked_resting");
    if (outcome.kind !== "blocked_resting") throw new Error("unreachable");
    expect(outcome.orders).toEqual([ORDER]);
    expect(outcome.message).toBe("포지션은 없지만 미체결 진입 주문 1건이 남아 있습니다.");
  });

  it("음성 대조 — 같은 409 라도 code 가 다르면 blocked_resting 이 아니다", () => {
    // `no_open_position` 등은 `detail` 이 **평문 문자열**이다. 여기서 걸러지지 않으면
    // 화면이 "잔량이 남았다"고 없는 사실을 말하게 된다.
    const err = new ApiError(409, "unknown_error", "API 409 /x", {
      detail: "no_open_position",
    });
    const outcome = outcomeFromError(err);
    expect(outcome.kind).toBe("failed");
  });

  it("음성 대조 — code 만 맞고 orders 가 없으면 blocked_resting 이 아니다", () => {
    const err = new ApiError(409, "unknown_error", "API 409 /x", {
      detail: { code: "resting_conditional_entries" },
    });
    expect(outcomeFromError(err).kind).toBe("failed");
  });

  it("409 가 아니면 blocked_resting 이 아니다", () => {
    const err = new ApiError(422, "unknown_error", "API 422 /x", conflictBody([ORDER]));
    expect(outcomeFromError(err).kind).toBe("failed");
  });

  it("도메인 에러는 describeApiError 의 한국어 문장을 싣는다", () => {
    const err = new ApiError(422, "unknown_error", "API 422 /x", {
      detail: { code: "settings_unset", detail: "거래 설정이 저장되지 않았습니다" },
    });
    const outcome = outcomeFromError(err);
    expect(outcome).toEqual({ kind: "failed", message: "거래 설정이 저장되지 않았습니다" });
  });

  it("ApiError 가 아닌 것도 문장으로 떨어진다", () => {
    expect(outcomeFromError(new Error("거래소 연결 실패"))).toEqual({
      kind: "failed",
      message: "거래소 연결 실패",
    });
  });
});
