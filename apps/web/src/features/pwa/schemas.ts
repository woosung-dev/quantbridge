// 웹 푸시 API 계약 — `docs/architecture/pwa.md` §3.2 (BE `src/notifications/schemas.py` 의 소비자).
import { z } from "zod/v4";

/** `GET /api/v1/push/config` — VAPID 키가 하나라도 없으면 `enabled: false, public_key: null`. */
export const PushConfigSchema = z.object({
  enabled: z.boolean(),
  public_key: z.string().nullable(),
});
export type PushConfig = z.infer<typeof PushConfigSchema>;

/**
 * `POST /api/v1/push/subscriptions` 본문 — `subscription.toJSON()` + `user_agent`.
 * ★endpoint 는 https 만(서버가 non-https 를 422 로 끊는다). 제약은 OpenAPI 와 같은 값이다 —
 *   `__tests__/push-openapi-contract.test.ts` 가 대조한다.
 */
export const CreatePushSubscriptionRequestSchema = z.object({
  endpoint: z
    .string()
    .min(9)
    .max(2048)
    .regex(/^https:\/\//),
  keys: z.object({
    p256dh: z.string().min(1).max(512),
    auth: z.string().min(1).max(512),
  }),
  user_agent: z.string().max(512).nullable().optional(),
});
export type CreatePushSubscriptionRequest = z.infer<typeof CreatePushSubscriptionRequestSchema>;

/** `POST /api/v1/push/subscriptions` 응답 — 201 생성 / 200 기존(upsert) 동일 모양. */
export const PushSubscriptionSchema = z.object({
  id: z.string(),
  endpoint: z.string(),
  created_at: z.string(),
});
export type PushSubscriptionRecord = z.infer<typeof PushSubscriptionSchema>;

/** `POST /api/v1/push/test` — 성공 발송 수 · 만료(404/410)로 지운 구독 수. */
export const PushTestResultSchema = z.object({
  sent: z.number().int(),
  removed: z.number().int(),
});
export type PushTestResult = z.infer<typeof PushTestResultSchema>;
