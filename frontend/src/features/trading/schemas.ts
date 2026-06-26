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
  // Wave 1 (TP/SL order primitives) — BE OrderResponse 와 1:1. Decimal→string 직렬화.
  // `.default()` = 구(舊) 응답/fixture 회귀 방지 (BE 는 항상 전송, default False/None).
  reduce_only: z.boolean().default(false),
  trigger_price: z.string().nullable().default(null),
  trigger_by: z.string().nullable().default(null),
  take_profit: z.string().nullable().default(null),
  stop_loss: z.string().nullable().default(null),
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

// P1-1/11 (S7-A): OKX 계정은 passphrase 필수. superRefine 으로 cross-field 검증.
// 이전엔 클라 검증 부재 → 서버 422 만 신뢰 → S7-A 의 onError 표시 도달 전까지 무피드백.
export const RegisterAccountRequestSchema = z
  .object({
    exchange: z.enum(["bybit", "okx"]),
    mode: z.enum(["demo", "live"]),
    label: z.string().nullable(),
    api_key: z.string().min(1, "API Key를 입력해주세요"),
    api_secret: z.string().min(1, "API Secret을 입력해주세요"),
    passphrase: z.string().nullable(),
  })
  .superRefine((data, ctx) => {
    if (
      data.exchange === "okx" &&
      (data.passphrase === null || data.passphrase.length === 0)
    ) {
      ctx.addIssue({
        code: "custom",
        path: ["passphrase"],
        message: "OKX 계정은 Passphrase 가 필수입니다",
      });
    }
  });
export type RegisterAccountRequest = z.infer<typeof RegisterAccountRequestSchema>;

// Wave 2 크로스도메인 계약 (W-B liquidation, 미머지) — 청산가 on-the-fly 계산 응답.
// Decimal 필드는 string 직렬화. BE LiquidationInfoResponse 와 1:1. 최종 wire-up = Phase 3.
export const LiquidationInfoResponseSchema = z.object({
  symbol: z.string(),
  entry_price: z.string(),
  side: z.enum(["buy", "sell"]),
  leverage: z.number(),
  liquidation_price: z.string(),
  maintenance_margin_rate: z.string(),
  distance_pct: z.string(),
});
export type LiquidationInfoResponse = z.infer<typeof LiquidationInfoResponseSchema>;
