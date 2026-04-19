// Sprint FE-04: status → badge meta mapping 검증 (UI regression 방지).

import { describe, expect, it } from "vitest";

import { STATUS_META } from "@/app/(dashboard)/backtests/_components/status-badge";
import { BacktestStatusSchema } from "../schemas";

describe("STATUS_META", () => {
  it("covers every BacktestStatus enum value", () => {
    const enumValues = BacktestStatusSchema.options;
    for (const v of enumValues) {
      expect(STATUS_META[v]).toBeDefined();
      expect(typeof STATUS_META[v].label).toBe("string");
    }
  });

  it("completed uses outline variant (calm)", () => {
    expect(STATUS_META.completed.variant).toBe("outline");
  });

  it("failed uses destructive variant (alarm)", () => {
    expect(STATUS_META.failed.variant).toBe("destructive");
  });

  it("running uses default variant", () => {
    expect(STATUS_META.running.variant).toBe("default");
  });
});
