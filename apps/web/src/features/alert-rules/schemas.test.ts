// 알림 규칙 Zod 계약과 사용자 우선 쿼리 키를 검증한다.
import { describe, expect, test } from "vitest";

import { alertRuleKeys } from "./query-keys";
import {
  AlertRuleCreateRequestSchema,
  AlertRuleListResponseSchema,
} from "./schemas";

describe("alert rules schemas", () => {
  test("백엔드 활성 규칙 응답을 round-trip 한다", () => {
    const response = AlertRuleListResponseSchema.parse({
      items: [
        {
          id: "a0000000-0000-4000-8000-000000000001",
          session_id: "a0000000-0000-4000-8000-000000000002",
          rule_type: "loss_limit",
          threshold_percent: "5",
          channel: "telegram",
          is_active: true,
          created_at: "2026-07-24T00:00:00Z",
          updated_at: "2026-07-24T00:00:00Z",
        },
      ],
      total: 1,
    });
    expect(response.items[0]!.threshold_percent).toBe("5");
  });

  test("loss_limit에는 threshold_percent가 필요하다", () => {
    expect(() =>
      AlertRuleCreateRequestSchema.parse({
        rule_type: "loss_limit",
        channel: "telegram",
      }),
    ).toThrow();
  });

  test("조회 훅 키는 userId를 첫 식별자로 둔다", () => {
    expect(alertRuleKeys.list("user-1", "session-1")).toEqual([
      "alert-rules",
      "user-1",
      "list",
      "session-1",
    ]);
  });
});
