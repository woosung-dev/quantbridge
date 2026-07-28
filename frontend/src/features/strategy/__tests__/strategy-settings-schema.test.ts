import { describe, expect, it } from "vitest";

import {
  StrategyResponseSchema,
  StrategySettingsSchema,
} from "@/features/strategy/schemas";

const baseSettings = {
  schema_version: 1,
  leverage: 2,
  margin_mode: "cross" as const,
  position_size_pct: 10,
};

const baseStrategyResponse = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  name: "Test strategy",
  description: null,
  pine_source: "strategy('Test')",
  pine_version: "v5" as const,
  parse_status: "ok" as const,
  parse_errors: null,
  timeframe: "1h",
  symbol: "BTC/USDT",
  tags: [],
  trading_sessions: [],
  is_archived: false,
  created_at: "2026-07-28T00:00:00Z",
  updated_at: "2026-07-28T00:00:00Z",
};

describe("StrategySettingsSchema", () => {
  it("설정 응답에 신규 두 키가 있어도 파싱된다", () => {
    const parsed = StrategyResponseSchema.parse({
      ...baseStrategyResponse,
      settings: {
        ...baseSettings,
        max_trigger_breach_pct: 0.5,
        fill_timing: "next_bar_open",
      },
    });

    expect(parsed.settings).toMatchObject({
      max_trigger_breach_pct: 0.5,
      fill_timing: "next_bar_open",
    });
  });

  it("max_trigger_breach_pct 가 없으면 null 로 파싱된다", () => {
    const parsed = StrategySettingsSchema.parse(baseSettings);

    expect(parsed.max_trigger_breach_pct).toBeNull();
  });

  it.each([0, -0.5])("max_trigger_breach_pct 가 %s 이면 거부된다", (value) => {
    const result = StrategySettingsSchema.safeParse({
      ...baseSettings,
      max_trigger_breach_pct: value,
    });

    expect(result.success).toBe(false);
  });

  it("fill_timing 미지정 시 bar_close 로 파싱된다", () => {
    const parsed = StrategySettingsSchema.parse(baseSettings);

    expect(parsed.fill_timing).toBe("bar_close");
  });
});
