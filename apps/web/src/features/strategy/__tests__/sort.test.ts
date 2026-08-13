import { describe, expect, it } from "vitest";

import { STRATEGY_SORT_OPTIONS, resolveStrategySort } from "../sort";

describe("resolveStrategySort", () => {
  it("keeps values inside the whitelist", () => {
    expect(resolveStrategySort("sharpe_ratio", "desc")).toEqual({
      order_by: "sharpe_ratio",
      order: "desc",
    });
    expect(resolveStrategySort("name", "asc")).toEqual({
      order_by: "name",
      order: "asc",
    });
  });

  it("normalizes values outside the whitelist to the defaults", () => {
    expect(resolveStrategySort("; DROP", "; DROP")).toEqual({
      order_by: "updated_at",
      order: "desc",
    });
  });

  it("normalizes null and undefined to the defaults", () => {
    expect(resolveStrategySort(null, undefined)).toEqual({
      order_by: "updated_at",
      order: "desc",
    });
  });

  it("round-trips every whitelisted option", () => {
    for (const option of STRATEGY_SORT_OPTIONS) {
      expect(resolveStrategySort(option.id, option.order)).toEqual({
        order_by: option.id,
        order: option.order,
      });
    }
  });
});
