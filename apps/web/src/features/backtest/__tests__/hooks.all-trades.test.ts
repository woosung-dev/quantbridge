// makeAllTradesFetcher first-page-then-parallel 단위 테스트 — offset 순서·truncated·cap 검증.

import { beforeEach, describe, expect, it, vi } from "vitest";

import { makeAllTradesFetcher } from "../hooks";
import type { TradeItem, TradeListResponse } from "../schemas";
import type * as ApiModule from "../api";

// listBacktestTrades 만 mock — 나머지 api export 는 원본 유지 (hooks.ts import 충족).
vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof ApiModule>();
  return {
    ...actual,
    listBacktestTrades: vi.fn(),
  };
});

import { listBacktestTrades } from "../api";

const listBacktestTradesMock = vi.mocked(listBacktestTrades);

const PAGE_SIZE = 200;
const MAX_CAP = 2000;

// Helper — trade_index 로 offset 순서를 식별하는 경량 fixture (fetcher 는
// items/total 만 소비하므로 나머지 필드는 생략 cast).
function tradeItems(offset: number, count: number): TradeItem[] {
  return Array.from(
    { length: count },
    (_, i) => ({ trade_index: offset + i }) as unknown as TradeItem,
  );
}

function page(offset: number, count: number, total: number): TradeListResponse {
  return { items: tradeItems(offset, count), total, limit: PAGE_SIZE, offset };
}

const getToken = async () => "test-token";

describe("makeAllTradesFetcher (first-page-then-parallel)", () => {
  beforeEach(() => {
    listBacktestTradesMock.mockReset();
  });

  it("단일 페이지 (total ≤ 200) → 1회 호출, truncated=false", async () => {
    listBacktestTradesMock.mockResolvedValueOnce(page(0, 150, 150));

    const result = await makeAllTradesFetcher("bt-1", getToken)();

    expect(listBacktestTradesMock).toHaveBeenCalledTimes(1);
    expect(listBacktestTradesMock).toHaveBeenCalledWith(
      "bt-1",
      { limit: PAGE_SIZE, offset: 0 },
      "test-token",
    );
    expect(result.items).toHaveLength(150);
    expect(result.total).toBe(150);
    expect(result.truncated).toBe(false);
  });

  it("다중 페이지 (total=450) → 잔여 offset 병렬 fetch + 응답 순서 무관 offset 순 concat", async () => {
    const total = 450;
    listBacktestTradesMock.mockImplementation(async (_id, query) => {
      // offset=200 응답을 지연시켜 out-of-order 해소 시나리오 재현.
      if (query.offset === 200) {
        await new Promise((r) => setTimeout(r, 10));
        return page(200, 200, total);
      }
      if (query.offset === 400) return page(400, 50, total);
      return page(0, 200, total);
    });

    const result = await makeAllTradesFetcher("bt-1", getToken)();

    const calledOffsets = listBacktestTradesMock.mock.calls.map(
      (c) => c[1].offset,
    );
    expect(calledOffsets).toEqual([0, 200, 400]);
    // 응답 도착 순서와 무관하게 offset 순 concat.
    expect(result.items.map((t) => t.trade_index)).toEqual(
      Array.from({ length: total }, (_, i) => i),
    );
    expect(result.total).toBe(total);
    expect(result.truncated).toBe(false);
  });

  it("total > cap(2000) → offset < 2000 까지만 호출, truncated=true", async () => {
    const total = 2500;
    listBacktestTradesMock.mockImplementation(async (_id, query) =>
      page(query.offset, PAGE_SIZE, total),
    );

    const result = await makeAllTradesFetcher("bt-1", getToken)();

    const calledOffsets = listBacktestTradesMock.mock.calls.map(
      (c) => c[1].offset,
    );
    expect(calledOffsets).toEqual([
      0, 200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800,
    ]);
    expect(calledOffsets.every((o) => o < MAX_CAP)).toBe(true);
    expect(result.items).toHaveLength(MAX_CAP);
    expect(result.total).toBe(total);
    expect(result.truncated).toBe(true);
  });

  it("total=0 (빈 결과) → 1회 호출, truncated=false", async () => {
    listBacktestTradesMock.mockResolvedValueOnce(page(0, 0, 0));

    const result = await makeAllTradesFetcher("bt-1", getToken)();

    expect(listBacktestTradesMock).toHaveBeenCalledTimes(1);
    expect(result.items).toEqual([]);
    expect(result.truncated).toBe(false);
  });
});
