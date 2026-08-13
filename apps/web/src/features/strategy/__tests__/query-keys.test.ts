// Sprint FE-02: strategyKeys factory identity 검증.
// userId가 key에 포함되어 사용자별 cache 격리가 보장되는지 확인.

import { describe, expect, it } from "vitest";

import { strategyKeys } from "../query-keys";
import type { StrategyListQuery } from "../schemas";

describe("strategyKeys", () => {
  const q: StrategyListQuery = { limit: 20, offset: 0, is_archived: false };

  it("prepends userId to all root key", () => {
    expect(strategyKeys.all("user_abc")).toEqual(["strategies", "user_abc"]);
  });

  it("different userId produces different list keys for same query", () => {
    const a = strategyKeys.list("user_a", q);
    const b = strategyKeys.list("user_b", q);
    expect(a).not.toEqual(b);
    expect(a[1]).toBe("user_a");
    expect(b[1]).toBe("user_b");
  });

  it("same userId + same query → identical key reference contents", () => {
    const a = strategyKeys.list("user_a", q);
    const b = strategyKeys.list("user_a", { ...q });
    expect(a).toEqual(b);
  });

  it("detail key composes userId + 'detail' + id", () => {
    const key = strategyKeys.detail("user_x", "strategy-42");
    expect(key).toEqual(["strategies", "user_x", "detail", "strategy-42"]);
  });

  it("parsePreview key composes userId + 'parse' + 'preview' + source", () => {
    const key = strategyKeys.parsePreview("user_y", "//@version=5\nindicator('x')");
    expect(key[0]).toBe("strategies");
    expect(key[1]).toBe("user_y");
    expect(key[2]).toBe("parse");
    expect(key[3]).toBe("preview");
    expect(key[4]).toBe("//@version=5\nindicator('x')");
  });

  it("anon fallback and real user are isolated", () => {
    const anon = strategyKeys.lists("anon");
    const real = strategyKeys.lists("user_real");
    expect(anon).not.toEqual(real);
  });
});
