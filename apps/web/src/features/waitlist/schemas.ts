// Sprint 11 Phase C: Waitlist domain Zod v4 schemas — BE API 응답/요청 런타임 검증.

import { z } from "zod/v4";

// Literal 값은 BE schemas.py 와 동일.
export const TVSubscriptionSchema = z.enum(["pro", "pro_plus", "premium"]);
export type TVSubscription = z.infer<typeof TVSubscriptionSchema>;

export const ExchangeCapitalSchema = z.enum([
  "under_1k",
  "1k_to_10k",
  "10k_to_100k",
  "over_100k",
]);
export type ExchangeCapital = z.infer<typeof ExchangeCapitalSchema>;

export const PineExperienceSchema = z.enum([
  "none",
  "beginner",
  "intermediate",
  "expert",
]);
export type PineExperience = z.infer<typeof PineExperienceSchema>;

export const WaitlistStatusSchema = z.enum([
  "pending",
  "invited",
  "joined",
  "rejected",
]);
export type WaitlistStatus = z.infer<typeof WaitlistStatusSchema>;

// BE EmailStr 대신 regex — email-validator 의존 회피.
const emailPattern = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export const CreateWaitlistApplicationSchema = z.object({
  email: z
    .string()
    .min(3)
    .max(320)
    .regex(emailPattern, "Enter a valid email address"),
  tv_subscription: TVSubscriptionSchema,
  exchange_capital: ExchangeCapitalSchema,
  pine_experience: PineExperienceSchema,
  existing_tool: z.string().max(120).nullable().optional(),
  pain_point: z
    .string()
    .trim()
    .min(3, "Please describe your pain point (≥3 chars)")
    .max(1000, "Maximum 1000 characters"),
});
export type CreateWaitlistApplication = z.infer<
  typeof CreateWaitlistApplicationSchema
>;

export const WaitlistApplicationAcceptedResponseSchema = z.object({
  id: z.uuid(),
  status: WaitlistStatusSchema,
});
export type WaitlistApplicationAcceptedResponse = z.infer<
  typeof WaitlistApplicationAcceptedResponseSchema
>;

export const WaitlistApplicationResponseSchema = z.object({
  id: z.uuid(),
  email: z.string(),
  tv_subscription: z.string(),
  exchange_capital: z.string(),
  pine_experience: z.string(),
  existing_tool: z.string().nullable(),
  pain_point: z.string(),
  status: WaitlistStatusSchema,
  invite_sent_at: z.iso.datetime({ offset: true }).nullable(),
  invited_at: z.iso.datetime({ offset: true }).nullable(),
  joined_at: z.iso.datetime({ offset: true }).nullable(),
  created_at: z.iso.datetime({ offset: true }),
});
export type WaitlistApplicationResponse = z.infer<
  typeof WaitlistApplicationResponseSchema
>;

export const AdminWaitlistListResponseSchema = z.object({
  items: z.array(WaitlistApplicationResponseSchema),
  total: z.number().int(),
});
export type AdminWaitlistListResponse = z.infer<
  typeof AdminWaitlistListResponseSchema
>;

export const AdminApproveResponseSchema = z.object({
  id: z.uuid(),
  status: WaitlistStatusSchema,
  email: z.string(),
  invite_sent_at: z.iso.datetime({ offset: true }).nullable(),
});
export type AdminApproveResponse = z.infer<typeof AdminApproveResponseSchema>;
