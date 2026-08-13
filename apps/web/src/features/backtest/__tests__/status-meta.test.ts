// Sprint FE-04: status → badge meta mapping 검증 (UI regression 방지).
// C 이식 S4: 라벨은 용어 SSOT(BACKTEST_STATUS_LABEL)로 이관, variant 만 배지 표현 계층에 남음.

import { describe, expect, it } from "vitest";

import { STATUS_VARIANT } from "@/app/(dashboard)/backtests/_components/status-badge";
import { BACKTEST_STATUS_LABEL } from "../labels";
import { BacktestStatusSchema } from "../schemas";

describe("BacktestStatusBadge status mapping", () => {
  it("STATUS_VARIANT covers every BacktestStatus enum value", () => {
    const enumValues = BacktestStatusSchema.options;
    for (const v of enumValues) {
      expect(STATUS_VARIANT[v]).toBeDefined();
    }
  });

  it("BACKTEST_STATUS_LABEL(용어 SSOT) covers every enum with a string label", () => {
    const enumValues = BacktestStatusSchema.options;
    for (const v of enumValues) {
      expect(typeof BACKTEST_STATUS_LABEL[v].label).toBe("string");
    }
  });

  it("completed uses outline variant (calm)", () => {
    expect(STATUS_VARIANT.completed).toBe("outline");
  });

  it("failed uses destructive variant (alarm)", () => {
    expect(STATUS_VARIANT.failed).toBe("destructive");
  });

  it("running uses default variant", () => {
    expect(STATUS_VARIANT.running).toBe("default");
  });
});
