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
  // [BL-413] 주문 상세 드로어가 쓰는 표시 전용 필드. BE `OrderResponse` 와 1:1 이고
  // `strategy_id`·`exchange_account_id`·`type` 은 BE 에서 **non-null 이다**
  // (`apps/api/src/trading/schemas.py:92-99`).
  // ★그런데도 `.nullable().default(null)` 인 이유는 Wave 1~3 필드와 **같은 계약**이다 —
  //   표시 전용 필드 하나가 빠졌다고 파싱이 죽으면 **주문 목록 전체가 빈 화면이 된다.**
  //   실측(2026-08-15): 이 셋을 non-nullable 로 두자 `e2e/trading-ui.spec.ts:171` 등
  //   route mock 4곳이 그 필드를 안 보내 authed e2e **4건**이 「행이 아예 없다」로 죽었다.
  //   BE 응답과의 정합은 스키마가 아니라 **드로어의 EMPTY_CELL fallback** 으로 감당한다.
  strategy_id: z.uuid().nullable().default(null),
  exchange_account_id: z.uuid().nullable().default(null),
  type: z.enum(["market", "limit"]).nullable().default(null),
  price: z.string().nullable().default(null),
  idempotency_key: z.string().nullable().default(null),
  submitted_at: z.string().nullable().default(null),
  filled_at: z.string().nullable().default(null),
  leverage: z.number().int().nullable().default(null),
  margin_mode: z.enum(["cross", "isolated"]).nullable().default(null),
  // Wave 1 (TP/SL order primitives) — BE OrderResponse 와 1:1. Decimal→string 직렬화.
  // `.default()` = 구(舊) 응답/fixture 회귀 방지 (BE 는 항상 전송, default False/None).
  reduce_only: z.boolean().default(false),
  trigger_price: z.string().nullable().default(null),
  trigger_by: z.string().nullable().default(null),
  take_profit: z.string().nullable().default(null),
  stop_loss: z.string().nullable().default(null),
  // Wave 2 (TP/SL placement) — BE OrderResponse 와 1:1. trigger_direction 은 정수(1/2),
  // trailing_stop 은 Decimal→string. 동일 default(null) 로 구 fixture 회귀 방지.
  trigger_direction: z.number().int().nullable().default(null),
  oco_group_id: z.string().nullable().default(null),
  trailing_stop: z.string().nullable().default(null),
  // Wave 3 (체결 수량·실현 손익) — BE OrderResponse 와 1:1. realized_pnl_synced_at 은
  // 거래소 확정 손익인지 pine_v2 추정값인지 밝히는 출처 마커이며 구 fixture 는 null 로 둔다.
  filled_quantity: z.string().nullable().default(null),
  realized_pnl: z.string().nullable().default(null),
  realized_pnl_synced_at: z.string().nullable().default(null),
});
export type Order = z.infer<typeof OrderSchema>;

export const OrderListResponseSchema = z.object({
  items: z.array(OrderSchema),
  total: z.number(),
});
export type OrderListResponse = z.infer<typeof OrderListResponseSchema>;

export const CancelOrderAcknowledgementSchema = z.object({
  order_id: z.uuid(),
  state: z.literal("submitted"),
  detail: z.literal("exchange cancel requested"),
});
export const CancelOrderResponseSchema = z.union([OrderSchema, CancelOrderAcknowledgementSchema]);
export type CancelOrderResponse = z.infer<typeof CancelOrderResponseSchema>;

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
  exchange_uid: z.string().nullable().default(null),
  read_only: z.boolean().nullable().default(null),
  created_at: z.string(),
});
export type ExchangeAccount = z.infer<typeof ExchangeAccountSchema>;

export const ExchangeAccountListResponseSchema = z.object({
  items: z.array(ExchangeAccountSchema),
});
export type ExchangeAccountListResponse = z.infer<typeof ExchangeAccountListResponseSchema>;

export const AccountBalanceSchema = z.object({
  account_id: z.uuid(),
  asset: z.string(),
  supported: z.boolean(),
  reason: z.string().nullable(),
  total: z.string().nullable(),
  free: z.string().nullable(),
  fetched_at: z.string().nullable(),
});
export type AccountBalance = z.infer<typeof AccountBalanceSchema>;

// C 이식(W3-F): 연결된 거래소는 Bybit 하나뿐이라 FE 등록 폼에서 OKX 를 제거했다(캐논 §4.8).
// OKX 전용 passphrase superRefine 도 함께 걷어냈다. passphrase 필드는 BE 계약(항상 전송, 기본
// null)을 위해 nullable 로 남기되 폼은 항상 null 을 보낸다. 백엔드 enum·마케팅 로드맵은 불변.
export const RegisterAccountRequestSchema = z.object({
  exchange: z.enum(["bybit"]),
  mode: z.enum(["demo", "live"]),
  label: z.string().nullable(),
  api_key: z.string().min(1, "API Key를 입력해주세요"),
  api_secret: z.string().min(1, "API Secret을 입력해주세요"),
  passphrase: z.string().nullable(),
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
