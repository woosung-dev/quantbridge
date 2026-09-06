// Sprint FE-04: backtestKeys factory identity tests.
// LESSON-005: userId 첫 인자로 cache 격리.

import { describe, expect, it } from "vitest";

import {
  backtestKeys,
  type BacktestListQuery,
  type BacktestTradesQuery,
  stressTestKeys,
} from "../query-keys";

describe("backtestKeys", () => {
  const listQ: BacktestListQuery = { limit: 20, offset: 0 };
  const tradesQ: BacktestTradesQuery = { limit: 200, offset: 0 };

  it("prepends userId to the root key", () => {
    expect(backtestKeys.all("user_abc")).toEqual(["backtests", "user_abc"]);
  });

  it("different userId produces different list keys for same query", () => {
    const a = backtestKeys.list("user_a", listQ);
    const b = backtestKeys.list("user_b", listQ);
    expect(a).not.toEqual(b);
    expect(a[1]).toBe("user_a");
    expect(b[1]).toBe("user_b");
  });

  it("detail key composes userId + 'detail' + id", () => {
    const key = backtestKeys.detail("user_x", "bt-42");
    expect(key).toEqual(["backtests", "user_x", "detail", "bt-42"]);
  });

  it("progress key isolates per backtest id", () => {
    const a = backtestKeys.progress("user_a", "id-1");
    const b = backtestKeys.progress("user_a", "id-2");
    expect(a).not.toEqual(b);
    expect(a).toContain("progress");
  });

  it("trades key composes userId + 'trades' + id + query", () => {
    const key = backtestKeys.trades("user_y", "bt-1", tradesQ);
    expect(key[0]).toBe("backtests");
    expect(key[1]).toBe("user_y");
    expect(key[2]).toBe("trades");
    expect(key[3]).toBe("bt-1");
  });

  it("anon fallback is isolated from real user", () => {
    const anon = backtestKeys.lists("anon");
    const real = backtestKeys.lists("user_real");
    expect(anon).not.toEqual(real);
  });
});

describe("stressTestKeys", () => {
  // ★리터럴 모양을 고정한다 — 다른 테스트는 이 팩토리를 **쿼리 키로 실행**만 하므로
  //   세그먼트 순서·이름이 바뀌어도(예: "by_backtest" → "byBacktest") 자기들끼리는 일관돼 초록이다.
  //   경계가 어긋나면 캐시가 사용자·실행·백테스트를 섞는다.
  it("사용자·실행·백테스트 경계를 정확히 구분한다", () => {
    const USER_ID = "user_keys";
    const STRESS_TEST_ID = "22222222-2222-4222-8222-222222222222";
    const BACKTEST_ID = "11111111-1111-4111-8111-111111111111";

    expect(stressTestKeys.all(USER_ID)).toEqual(["stress_test", USER_ID]);
    expect(stressTestKeys.detail(USER_ID, STRESS_TEST_ID)).toEqual([
      "stress_test",
      USER_ID,
      "detail",
      STRESS_TEST_ID,
    ]);
    expect(stressTestKeys.byBacktest(USER_ID, BACKTEST_ID)).toEqual([
      "stress_test",
      USER_ID,
      "by_backtest",
      BACKTEST_ID,
    ]);
  });
});
