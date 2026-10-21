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

export const TickerEnvelopeSchema = z.object({
  ...EnvelopeFields,
  type: z.literal("ticker"),
  payload: z.object({
    symbol: z.string(),
    mark_price: z.string(),
    last_price: z.string().nullable().optional(),
  }),
});

export const PositionUpdateEnvelopeSchema = z.object({
  ...EnvelopeFields,
  type: z.literal("position_update"),
  payload: z.object({
    symbol: z.string(),
    side: z.enum(["long", "short", "flat"]),
    size: z.string(),
  }),
});

export const RealtimeEnvelopeSchema = z.discriminatedUnion("type", [
  OrderUpdateEnvelopeSchema,
  KillSwitchEnvelopeSchema,
  KillSwitchResolvedEnvelopeSchema,
  SessionStateEnvelopeSchema,
  TickerEnvelopeSchema,
  PositionUpdateEnvelopeSchema,
]);

export type RealtimeEnvelope = z.infer<typeof RealtimeEnvelopeSchema>;

export function parseRealtimeEnvelope(value: unknown): RealtimeEnvelope | null {
  if (typeof value !== "string") return null;
  try {
    return validateRealtimeEnvelope(JSON.parse(value));
  } catch {
    return null;
  }
}

/** 이미 `JSON.parse` 한 값을 검증한다 — ws-client 가 프레임당 한 번만 파싱하도록 분리했다. */
export function validateRealtimeEnvelope(raw: unknown): RealtimeEnvelope | null {
  const result = RealtimeEnvelopeSchema.safeParse(raw);
  return result.success ? result.data : null;
}
