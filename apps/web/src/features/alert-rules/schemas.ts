// 세션 알림 규칙 API 계약을 Zod v4로 미러한다.
import { z } from "zod/v4";

export const AlertRuleTypeSchema = z.enum(["loss_limit", "watchdog"]);
export type AlertRuleType = z.infer<typeof AlertRuleTypeSchema>;

export const AlertChannelSchema = z.enum(["slack", "telegram", "both"]);
export type AlertChannel = z.infer<typeof AlertChannelSchema>;

export const AlertRuleSchema = z.object({
  id: z.uuid(),
  session_id: z.uuid(),
  rule_type: AlertRuleTypeSchema,
  threshold_percent: z.string().nullable(),
  channel: AlertChannelSchema,
  is_active: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type AlertRule = z.infer<typeof AlertRuleSchema>;

export const AlertRuleListResponseSchema = z.object({
  items: z.array(AlertRuleSchema),
  total: z.number(),
});
export type AlertRuleListResponse = z.infer<typeof AlertRuleListResponseSchema>;

export const AlertRuleCreateRequestSchema = z
  .object({
    rule_type: AlertRuleTypeSchema,
    threshold_percent: z
      .string()
      .regex(/^\d+(?:\.\d+)?$/, "손실 한도는 0보다 큰 숫자여야 합니다.")
      .refine((value) => Number(value) > 0, "손실 한도는 0보다 커야 합니다.")
      .refine((value) => Number(value) <= 100, "손실 한도는 100% 이하여야 합니다.")
      .optional(),
    channel: AlertChannelSchema,
  })
  .superRefine((value, ctx) => {
    if (value.rule_type === "loss_limit" && !value.threshold_percent) {
      ctx.addIssue({
        code: "custom",
        path: ["threshold_percent"],
        message: "손실 한도를 입력해주세요.",
      });
    }
    if (value.rule_type === "watchdog" && value.threshold_percent) {
      ctx.addIssue({
        code: "custom",
        path: ["threshold_percent"],
        message: "워치독 규칙에는 손실 한도를 설정할 수 없습니다.",
      });
    }
  });
export type AlertRuleCreateRequest = z.infer<
  typeof AlertRuleCreateRequestSchema
>;
