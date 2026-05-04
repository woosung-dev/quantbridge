// Sprint 7c: Strategy domain Zod 스키마 — Backend API 응답/요청 런타임 검증.
// 타입은 z.infer로 단일 소스화 (schema-first 원칙).

import { z } from "zod/v4";

export const ParseStatusSchema = z.enum(["ok", "unsupported", "error"]);
export type ParseStatus = z.infer<typeof ParseStatusSchema>;

export const PineVersionSchema = z.enum(["v4", "v5"]);
export type PineVersion = z.infer<typeof PineVersionSchema>;

export const ParseErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  line: z.number().int().nullable(),
});
export type ParseError = z.infer<typeof ParseErrorSchema>;

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
  is_runnable: z.boolean().default(true),
});
export type ParsePreviewResponse = z.infer<typeof ParsePreviewResponseSchema>;

export const TradingSessionSchema = z.enum(["asia", "london", "ny"]);
export type TradingSession = z.infer<typeof TradingSessionSchema>;

// Sprint 27 BL-137 — trading settings (Live Signal Auto-Trading 의 leverage/margin/size).
// Backend StrategySettings (backend/src/strategy/schemas.py:72-87) 와 동일 spec.
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
  })
  .strict();
export type StrategySettings = z.infer<typeof StrategySettingsSchema>;

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
});
export type StrategyListQuery = z.infer<typeof StrategyListQuerySchema>;
