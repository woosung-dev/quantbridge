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
  is_archived: z.boolean(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type StrategyResponse = z.infer<typeof StrategyResponseSchema>;

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

export const StrategyListQuerySchema = z.object({
  limit: z.number().int().min(1).max(100).default(20),
  offset: z.number().int().min(0).default(0),
  parse_status: ParseStatusSchema.optional(),
  is_archived: z.boolean().default(false),
});
export type StrategyListQuery = z.infer<typeof StrategyListQuerySchema>;
