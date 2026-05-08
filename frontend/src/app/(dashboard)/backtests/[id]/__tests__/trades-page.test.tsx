// Sprint 43 W11 — /backtests/[id]/trades page UUID 검증 + notFound 트리거 검증.
//
// Server component 직접 호출 — notFound() 가 Next.js 의 NEXT_NOT_FOUND error 를
// throw 하므로, 잘못된 UUID 시 throw 검증.

import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  notFound: () => {
    throw new Error("NEXT_NOT_FOUND");
  },
}));

vi.mock("../../_components/trade-detail-shell", () => ({
  TradeDetailShell: ({ id }: { id: string }) => `MockedTradeDetailShell:${id}`,
}));

import BacktestTradesPage from "../trades/page";

describe("BacktestTradesPage — UUID 검증", () => {
  it("정상 UUID → 정상 렌더 (notFound 호출되지 않음)", async () => {
    const validUuid = "550e8400-e29b-41d4-a716-446655440000";
    const result = await BacktestTradesPage({
      params: Promise.resolve({ id: validUuid }),
    });
    // 렌더 결과 React element 객체 (정상 경로 — error throw 없음)
    expect(result).toBeDefined();
  });

  it("잘못된 UUID 포맷 → notFound() throw", async () => {
    await expect(() =>
      BacktestTradesPage({
        params: Promise.resolve({ id: "not-a-uuid" }),
      }),
    ).rejects.toThrow("NEXT_NOT_FOUND");
  });

  it("빈 문자열 → notFound() throw", async () => {
    await expect(() =>
      BacktestTradesPage({ params: Promise.resolve({ id: "" }) }),
    ).rejects.toThrow("NEXT_NOT_FOUND");
  });

  it("SQL injection 시도 → notFound() throw (UUID 포맷 미통과)", async () => {
    await expect(() =>
      BacktestTradesPage({
        params: Promise.resolve({ id: "1' OR '1'='1" }),
      }),
    ).rejects.toThrow("NEXT_NOT_FOUND");
  });
});
