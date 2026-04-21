// Trading 도메인 Zod 스키마 — Decimal 필드는 string 직렬화 유지 (backend Decimal → JSON string).
// ADR-006 F4: KillSwitchEvent.trigger_type rename.

import { z } from "zod";

export const OrderSchema = z.object({
  id: z.uuid(),
  symbol: z.string(),
  side: z.enum(["buy", "sell"]),
  state: z.enum(["pending", "submitted", "filled", "rejected", "cancelled"]),
  quantity: z.string(),
  filled_price: z.string().nullable(),
  exchange_order_id: z.string().nullable(),
  error_message: z.string().nullable(),
  created_at: z.string(),
});
export type Order = z.infer<typeof OrderSchema>;

export const OrderListResponseSchema = z.object({
  items: z.array(OrderSchema),
  total: z.number(),
});
export type OrderListResponse = z.infer<typeof OrderListResponseSchema>;

export const KillSwitchEventSchema = z.object({
  id: z.uuid(),
  trigger_type: z.enum(["cumulative_loss", "daily_loss", "api_error"]),
  trigger_value: z.string(),
  threshold: z.string(),
  triggered_at: z.string(),
  resolved_at: z.string().nullable(),
});
export type KillSwitchEvent = z.infer<typeof KillSwitchEventSchema>;

export const KillSwitchListResponseSchema = z.object({
  items: z.array(KillSwitchEventSchema),
});
export type KillSwitchListResponse = z.infer<typeof KillSwitchListResponseSchema>;

export const ExchangeAccountSchema = z.object({
  id: z.uuid(),
  exchange: z.string(),
  mode: z.string(),
  label: z.string().nullable(),
  api_key_masked: z.string(),
  created_at: z.string(),
});
export type ExchangeAccount = z.infer<typeof ExchangeAccountSchema>;

export const ExchangeAccountListResponseSchema = z.object({
  items: z.array(ExchangeAccountSchema),
});
export type ExchangeAccountListResponse = z.infer<typeof ExchangeAccountListResponseSchema>;

export const RegisterAccountRequestSchema = z.object({
  exchange: z.enum(["bybit", "okx"]),
  mode: z.enum(["testnet", "live"]),
  label: z.string().nullable(),
  api_key: z.string().min(1, "API Key를 입력해주세요"),
  api_secret: z.string().min(1, "API Secret을 입력해주세요"),
  passphrase: z.string().nullable(),
});
export type RegisterAccountRequest = z.infer<typeof RegisterAccountRequestSchema>;
