// Sprint 7c: Strategy domain Zod 스키마 — Backend API 응답/요청 런타임 검증.
// 타입은 z.infer로 단일 소스화 (schema-first 원칙).

import { z } from "zod/v4";

import { BacktestMetricsSummarySchema } from "@/features/backtest/schemas";

export const ParseStatusSchema = z.enum(["ok", "unsupported", "error"]);
export type ParseStatus = z.infer<typeof ParseStatusSchema>;

export const StrategyLifecycleSchema = z.enum(["draft", "validated", "deployed"]);
export type StrategyLifecycle = z.infer<typeof StrategyLifecycleSchema>;

export const PineVersionSchema = z.enum(["v4", "v5"]);
export type PineVersion = z.infer<typeof PineVersionSchema>;

export const ParseErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  line: z.number().int().nullable(),
});
export type ParseError = z.infer<typeof ParseErrorSchema>;

export const UnsupportedCallSchema = z.object({
  name: z.string(),
  // BE가 아직 이 필드를 보내지 않은 구 parse 응답도 목록 전체를 비우지 않아야 한다.
  line: z.number().int().nullable().default(null),
  col: z.number().int().nullable().default(null),
  workaround: z.string().nullable().default(null),
  category: z.enum(["drawing", "data", "syntax", "math", "other"]).nullable().default(null),
});
export type UnsupportedCall = z.infer<typeof UnsupportedCallSchema>;

export const ParsePreviewResponseSchema = z.object({
  status: ParseStatusSchema,
  pine_version: PineVersionSchema,
  warnings: z.array(z.string()).default([]),
  errors: z.array(ParseErrorSchema).default([]),
  entry_count: z.number().int().default(0),
  exit_count: z.number().int().default(0),
  // Sprint 7b ISSUE-004: BE ParseOutcome.supported_feature_report["functions_used"] 반영.
  functions_used: z.array(z.string()).default([]),
  // Sprint Y1: pre-flight coverage analyzer — 미지원 built-in 명시 (whack-a-mole 종식)
  unsupported_builtins: z.array(z.string()).default([]),
  // BE UnsupportedCallResponse의 코드 위치와 우회안. 배열이 없던 구 응답도 허용한다.
  unsupported_calls: z.array(UnsupportedCallSchema).default([]),
  is_runnable: z.boolean().default(true),
});
export type ParsePreviewResponse = z.infer<typeof ParsePreviewResponseSchema>;

export const TradingSessionSchema = z.enum(["asia", "london", "ny"]);
export type TradingSession = z.infer<typeof TradingSessionSchema>;

// Sprint 27 BL-137 — trading settings (Live Signal Auto-Trading 의 leverage/margin/size).
// Backend StrategySettings (apps/api/src/strategy/schemas.py:72-87) 와 동일 spec.
export const MarginModeSchema = z.enum(["cross", "isolated"]);
export type MarginMode = z.infer<typeof MarginModeSchema>;

// codex G.2 P1 #1 — BE extra='forbid' 정합. FE 가 unknown key 통과시키면
// 백엔드에서 422, 또는 FE schema 가 silent strip → BE 와 mismatch.
export const StrategySettingsSchema = z
  .object({
    schema_version: z.number().int().default(1),
    leverage: z.number().int().min(1).max(125),
    margin_mode: MarginModeSchema,
    position_size_pct: z.number().gt(0).max(100),
    max_trigger_breach_pct: z.number().gt(0).nullable().optional().default(null),
    // BL-516 — BE `StrategySettings` 가 default None 으로 emit 한다. `update_settings` 가
    // `model_dump()` 를 그대로 저장하므로 설정을 한 번만 저장해도 JSONB 에 이 키가 박힌다.
    // `.strict()` 라 여기 없으면 그 전략의 이후 파싱이 **영구히** 실패한다 (codex 적대 리뷰 MAJOR).
    max_reversal_overshoot_ratio: z.number().gt(0).nullable().optional().default(null),
    fill_timing: z.enum(["bar_close", "next_bar_open"]).default("bar_close"),
  })
  .strict();
export type StrategySettings = z.infer<typeof StrategySettingsSchema>;

// Sprint 38 BL-188 v3 D — Pine declaration optional. StrategyResponseSchema 가
// strategy detail 응답의 pine_declared_qty 를 직접 보존해 form 이 4-state 의
// "pine" tier 로 분기한다. BE 미emit 시 undefined.
export const PineDeclaredQtySchema = z.object({
  type: z.string().nullable().optional(),
  value: z.number().nullable().optional(),
});

export const StrategyResponseSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  description: z.string().nullable(),
  pine_source: z.string(),
  pine_version: PineVersionSchema,
  parse_status: ParseStatusSchema,
  parse_errors: z.array(z.record(z.string(), z.unknown())).nullable(),
  timeframe: z.string().nullable(),
  symbol: z.string().nullable(),
  tags: z.array(z.string()).default([]),
  trading_sessions: z.array(z.string()).default([]),
  // Sprint 27 BL-137 — settings JSONB. null = unset (Live Session 시작 차단).
  settings: StrategySettingsSchema.nullable().optional(),
  // Sprint 38 BL-188 v3 D — Pine declaration optional (BE emit 시 4-state pine tier).
  pine_declared_qty: PineDeclaredQtySchema.nullable().optional(),
  is_archived: z.boolean(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type StrategyResponse = z.infer<typeof StrategyResponseSchema>;

// Sprint 13 Phase A.1.4: Strategy create 응답에만 webhook_secret plaintext 1회 포함.
// GET / list 응답은 StrategyResponse 유지 — webhook_secret 노출 X.
export const StrategyCreateResponseSchema = StrategyResponseSchema.extend({
  webhook_secret: z.string().nullable().optional(),
});
export type StrategyCreateResponse = z.infer<typeof StrategyCreateResponseSchema>;

// Sprint 13 Phase A.2: rotate-webhook-secret 응답 (Sprint 6 broken bug fix 후).
export const WebhookRotateResponseSchema = z.object({
  secret: z.string(),
  webhook_url: z.string(),
});
export type WebhookRotateResponse = z.infer<typeof WebhookRotateResponseSchema>;

export const StrategyListItemSchema = StrategyResponseSchema.omit({
  pine_source: true,
  description: true,
}).extend({
  backtest_count: z.number().int().optional(),
  param_count: z.number().int().default(0),
  lifecycle: StrategyLifecycleSchema.default("draft"),
  latest_backtest: z
    .object({
      backtest_id: z.uuid(),
      completed_at: z.iso.datetime({ offset: true }).nullable(),
      metrics: BacktestMetricsSummarySchema.nullable(),
    })
    .nullable()
    .optional(),
});
export type StrategyListItem = z.infer<typeof StrategyListItemSchema>;

export const StrategyListResponseSchema = z.object({
  items: z.array(StrategyListItemSchema),
  total: z.number().int(),
  page: z.number().int(),
  limit: z.number().int(),
  total_pages: z.number().int(),
});
export type StrategyListResponse = z.infer<typeof StrategyListResponseSchema>;

export const CreateStrategyRequestSchema = z.object({
  name: z.string().min(1).max(120),
  description: z.string().max(2000).nullable().optional(),
  pine_source: z.string().min(1),
  timeframe: z.string().max(16).nullable().optional(),
  symbol: z.string().max(32).nullable().optional(),
  tags: z.array(z.string()).default([]),
});
export type CreateStrategyRequest = z.infer<typeof CreateStrategyRequestSchema>;

export const UpdateStrategyRequestSchema = z.object({
  name: z.string().min(1).max(120).optional(),
  description: z.string().max(2000).nullable().optional(),
  pine_source: z.string().min(1).optional(),
  timeframe: z.string().max(16).nullable().optional(),
  symbol: z.string().max(32).nullable().optional(),
  tags: z.array(z.string()).optional(),
  trading_sessions: z.array(z.string()).optional(),
  is_archived: z.boolean().optional(),
});
export type UpdateStrategyRequest = z.infer<typeof UpdateStrategyRequestSchema>;

// Sprint 27 BL-137 — PUT /strategies/{id}/settings request body. Backend
// UpdateStrategySettingsRequest (extra="forbid") 와 동일 spec.
export const UpdateStrategySettingsRequestSchema = StrategySettingsSchema;
export type UpdateStrategySettingsRequest = z.infer<
  typeof UpdateStrategySettingsRequestSchema
>;

export const StrategyListQuerySchema = z.object({
  limit: z.number().int().min(1).max(100).default(20),
  offset: z.number().int().min(0).default(0),
  parse_status: ParseStatusSchema.optional(),
  is_archived: z.boolean().default(false),
  order_by: z.enum(["updated_at", "name", "total_return", "sharpe_ratio"]).default("updated_at"),
  order: z.enum(["asc", "desc"]).default("desc"),
});
export type StrategyListQuery = z.input<typeof StrategyListQuerySchema>;
