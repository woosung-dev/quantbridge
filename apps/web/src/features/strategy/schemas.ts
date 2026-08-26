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

// [ADR-040] Stage 1 — BE `InputDeclResponse` / `DeclarationResponse`.
// ★`var_name` 은 표시용 라벨이 아니라 **override 키**다 — Optimizer / Param-Stability 가
//   이 이름으로 파라미터를 스윕한다. 표에서 이름을 가공하지 마라.
export const InputDeclSchema = z.object({
  input_type: z.string(),
  var_name: z.string(),
  defval: z.string().nullable().default(null),
  title: z.string().nullable().default(null),
});
export type InputDecl = z.infer<typeof InputDeclSchema>;

export const DeclarationSchema = z.object({
  kind: z.enum(["strategy", "indicator", "library", "unknown"]),
  title: z.string().nullable().default(null),
  default_qty_type: z.string().nullable().default(null),
  default_qty_value: z.string().nullable().default(null),
  pyramiding: z.number().int().nullable().default(null),
});
export type Declaration = z.infer<typeof DeclarationSchema>;

// ★Optimizer 가 스윕할 수 있는 input_type 은 둘뿐이다 — BE `_validate_grid_search_pre`
//   (`optimizer/engine/grid_search.py`) 가 `int`/`float` 외를 422 로 거부한다(BL-225).
//   v4 무네임스페이스 `input(...)` 은 `generic` 이라 여기 안 든다.
export const SWEEPABLE_INPUT_TYPES = ["int", "float"] as const;
export function isSweepable(input: InputDecl): boolean {
  return (SWEEPABLE_INPUT_TYPES as readonly string[]).includes(input.input_type);
}

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
  // ★BE 는 이 필드를 보내는데(`coverage.dogfood_only_warning`) FE 스키마가 빠뜨려 버리고
  //   있었다 — heikinashi 등 Trust Layer 위반 경고라 브리핑이 반드시 보여야 한다.
  dogfood_only_warning: z.string().nullable().default(null),
  is_runnable: z.boolean().default(true),
  // [ADR-040] Stage 1 — 파싱 실패 시 BE 가 null/[] 를 보낸다. 구 응답도 통과해야 한다.
  declaration: DeclarationSchema.nullable().default(null),
  inputs: z.array(InputDeclSchema).default([]),
});
export type ParsePreviewResponse = z.infer<typeof ParsePreviewResponseSchema>;

// ── [ADR-040] 전략 브리핑 (결정론 층) ────────────────────────────────────────
// ★이 응답에 LLM 이 만든 값은 하나도 없다. 해설 층은 별 엔드포인트다.
export const BriefArgSchema = z.object({
  name: z.string().nullable().default(null),
  value: z.string(),
});

export const BriefOrderCallSchema = z.object({
  name: z.string(),
  line: z.number().int().nullable().default(null),
  args: z.array(BriefArgSchema).default([]),
});
export type BriefOrderCall = z.infer<typeof BriefOrderCallSchema>;

// [ADR-042] Pine AST 를 옮긴 **읽기 전용** Python 뷰. ★실행되는 코드가 아니다.
export const PythonViewSchema = z.object({
  code: z.string(),
  // `[python 줄, pine 줄]` 1-based. 대응을 모르는 줄은 등장하지 않는다 — 지어내지 않는다.
  source_map: z.array(z.tuple([z.number().int(), z.number().int()])).default([]),
  // 못 옮겨 원문을 주석으로 보존한 노드 수. >0 이면 화면이 그 사실을 말해야 한다.
  unrendered: z.number().int().default(0),
});
export type PythonView = z.infer<typeof PythonViewSchema>;

export const StrategyBriefSchema = z.object({
  strategy_id: z.string(),
  source_hash: z.string().nullable().default(null),
  track: z.enum(["S", "A", "M"]).nullable().default(null),
  parse: ParsePreviewResponseSchema,
  orders: z.array(BriefOrderCallSchema).default([]),
  // ★Track S 의 `if cond` 형태에서는 **비는 것이 정상**이다 — BE `SignalExtractor` 는
  //   `when=` · `plotshape` · `alertcondition` · `label.new(v ? ..)` 네 형태만 본다.
  //   비었을 때 이 절을 **그리지 마라**. 「신호 없음」으로 읽히면 거짓이다(`_KIT.md` §4.9).
  signals: z.array(z.string()).default([]),
  python_view: PythonViewSchema.nullable().default(null),
});
export type StrategyBrief = z.infer<typeof StrategyBriefSchema>;

// ── [ADR-040] 해설 층 (LLM) ─────────────────────────────────────────────────
// ★★**판정이 아니다.** 실행 가능/미지원/degraded/Track 은 결정론 층이 낸다.
//   화면은 이 층을 **시각적으로 격리**하고 「AI 해설 — 판정이 아닙니다」를 붙인다.
export const NarrativeNoteSchema = z.object({
  text: z.string(),
  // ★서버가 실재하지 않는 줄을 이미 버렸다. 그래도 비면 렌더하지 않는다(두 겹).
  pine_lines: z.array(z.number().int()).default([]),
});
export type NarrativeNote = z.infer<typeof NarrativeNoteSchema>;

export const NARRATIVE_STYLE_LABEL: Record<string, string> = {
  trend_following: "추세추종",
  mean_reversion: "평균회귀",
  breakout: "브레이크아웃",
  volatility: "변동성",
  other: "기타",
};

export const StrategyNarrativeSchema = z.object({
  source_hash: z.string(),
  provider: z.enum(["anthropic", "gemini"]),
  summary: z.string(),
  style: z.enum(["trend_following", "mean_reversion", "breakout", "volatility", "other"]),
  assumptions: z.array(NarrativeNoteSchema).default([]),
  risks: z.array(NarrativeNoteSchema).default([]),
  dropped_ungrounded: z.number().int().default(0),
});
export type StrategyNarrative = z.infer<typeof StrategyNarrativeSchema>;

// ── [ADR-041] 자연어 → 전략 생성 ─────────────────────────────────────────────
// ★**Pine 이 정본이다.** Python 은 사람이 읽는 뷰이고, 둘이 어긋나는 것을 **막을 수단이 없다** —
//   설계는 제거 대신 **가시화**한다([ADR-041] §트레이드오프).
export const DriftReportSchema = z.object({
  // 렌더러가 Pine 에서 뽑은 **정본** Python. 어긋나면 이쪽이 진실이다.
  rendered_python: z.string(),
  only_in_llm: z.array(z.string()).default([]),
  only_in_rendered: z.array(z.string()).default([]),
});
export type DriftReport = z.infer<typeof DriftReportSchema>;

export const GenerateStrategyResponseSchema = z.object({
  provider: z.enum(["anthropic", "gemini"]),
  pine_source: z.string(),
  llm_python: z.string(),
  notes: z.array(z.string()).default([]),
  // ★판정은 LLM 이 아니라 `analyze_coverage` 가 낸다.
  is_runnable: z.boolean(),
  unsupported: z.array(z.string()).default([]),
  drift: DriftReportSchema.nullable().default(null),
});
export type GenerateStrategyResponse = z.infer<typeof GenerateStrategyResponseSchema>;

export function hasDrift(d: DriftReport | null): boolean {
  return d !== null && (d.only_in_llm.length > 0 || d.only_in_rendered.length > 0);
}

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
export type UpdateStrategySettingsRequest = z.infer<typeof UpdateStrategySettingsRequestSchema>;

export const StrategyListQuerySchema = z.object({
  limit: z.number().int().min(1).max(100).default(20),
  offset: z.number().int().min(0).default(0),
  parse_status: ParseStatusSchema.optional(),
  is_archived: z.boolean().default(false),
  order_by: z.enum(["updated_at", "name", "total_return", "sharpe_ratio"]).default("updated_at"),
  order: z.enum(["asc", "desc"]).default("desc"),
});
export type StrategyListQuery = z.input<typeof StrategyListQuerySchema>;
