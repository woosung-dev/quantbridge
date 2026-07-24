// 백엔드 실시간 이벤트 envelope를 런타임 검증하는 Zod 미러.
import { z } from "zod";

const EnvelopeFields = {
  v: z.literal(1),
  ts: z.number().int(),
};

export const OrderUpdateEnvelopeSchema = z.object({
  ...EnvelopeFields,
  type: z.literal("order_update"),
  payload: z.object({
    order_id: z.string(),
    state: z.string(),
    symbol: z.string(),
    side: z.string(),
    source: z.string(),
  }),
});

export const KillSwitchEnvelopeSchema = z.object({
  ...EnvelopeFields,
  type: z.literal("kill_switch"),
  payload: z.object({
    event_id: z.string(),
    trigger_type: z.string(),
  }),
});

export const KillSwitchResolvedEnvelopeSchema = z.object({
  ...EnvelopeFields,
  type: z.literal("kill_switch_resolved"),
  payload: z.object({
    event_id: z.string(),
    trigger_type: z.string(),
  }),
});

export const SessionStateEnvelopeSchema = z.object({
  ...EnvelopeFields,
  type: z.literal("session_state"),
  payload: z.object({
    session_id: z.string(),
  }),
});

export const RealtimeEnvelopeSchema = z.discriminatedUnion("type", [
  OrderUpdateEnvelopeSchema,
  KillSwitchEnvelopeSchema,
  KillSwitchResolvedEnvelopeSchema,
  SessionStateEnvelopeSchema,
]);

export type RealtimeEnvelope = z.infer<typeof RealtimeEnvelopeSchema>;

export function parseRealtimeEnvelope(value: unknown): RealtimeEnvelope | null {
  if (typeof value !== "string") return null;
  try {
    const raw: unknown = JSON.parse(value);
    const result = RealtimeEnvelopeSchema.safeParse(raw);
    return result.success ? result.data : null;
  } catch {
    return null;
  }
}
