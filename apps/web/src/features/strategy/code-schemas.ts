import { z } from "zod/v4";

import { StrategySettingsSchema } from "./schemas";
import { CodeExecutionPolicySchema, ResearchExecutionSchema } from "./research-contract";

export const CodeLanguageSchema = z.enum(["python", "typescript", "pine"]);
export type CodeLanguage = z.infer<typeof CodeLanguageSchema>;
export const CODE_LANGUAGE_LABELS: Record<CodeLanguage, string> = {
  python: "Python",
  typescript: "TypeScript",
  pine: "Pine Script",
};
export const CodeTimeframeSchema = z.enum(["1h", "4h", "1d"]);
const JsonObjectSchema = z.record(z.string(), z.json());

export const CodeSnapshotSchema = z
  .object({
    schema_version: z.literal(1),
    execution_policy: CodeExecutionPolicySchema,
    language: CodeLanguageSchema,
    source_code: z
      .string()
      .min(1)
      .max(131072)
      .refine((value) => value.trim().length > 0),
    warmup_bars: z.number().int().min(1).max(10000),
    params: JsonObjectSchema,
    provenance: JsonObjectSchema,
  })
  .superRefine((code, context) => {
    if (
      code.execution_policy === "code_research_v1" &&
      !ResearchExecutionSchema.safeParse(code.provenance.research_execution).success
    ) {
      context.addIssue({
        code: "custom",
        path: ["provenance", "research_execution"],
        message: "엄격한 연구 실행 계약이 필요합니다.",
      });
    }
  });
export type CodeSnapshot = z.infer<typeof CodeSnapshotSchema>;
export const GenerateCodeStrategyRequestSchema = z.object({
  prompt: z.string().trim().min(10).max(2000),
  warmup_bars: z.number().int().min(1).max(10000),
  params: JsonObjectSchema,
});
export type GenerateCodeStrategyRequest = z.infer<typeof GenerateCodeStrategyRequestSchema>;
const ReportedTokensSchema = z.number().int().nonnegative().nullable();
export const GenerateCodeStrategyResponseSchema = z.object({
  status: z.literal("preview"),
  code: CodeSnapshotSchema.safeExtend({ language: z.literal("python") }),
  assumptions: z.array(z.string()),
  provider: z.literal("gemini"),
  requested_model: z.string().min(1),
  actual_model: z.string().nullable(),
  usage: z
    .object({
      input_tokens: ReportedTokensSchema,
      output_tokens: ReportedTokensSchema,
      thinking_tokens: ReportedTokensSchema,
      total_tokens: ReportedTokensSchema,
    })
    .nullable(),
});
export type GenerateCodeStrategyResponse = z.infer<typeof GenerateCodeStrategyResponseSchema>;
export const SaveCodeStrategySchema = z.object({
  name: z.string().trim().min(1).max(120),
  symbol: z.string().trim().min(3).max(32),
  timeframe: CodeTimeframeSchema,
  code: CodeSnapshotSchema,
  settings: StrategySettingsSchema,
});
export type SaveCodeStrategy = z.infer<typeof SaveCodeStrategySchema>;
export const CodeDemoRequestSchema = z.object({
  strategy_id: z.uuid(),
  strategy_version_id: z.uuid(),
  exchange_account_id: z.uuid(),
  source_policy: z.literal("code_v1"),
  symbol: z.string().min(3).max(32),
  interval: z.literal("1h"),
});
export type CodeDemoRequest = z.infer<typeof CodeDemoRequestSchema>;
export const CodeStrategySchema = z.object({
  id: z.uuid(),
  name: z.string(),
  description: z.string().nullable(),
  symbol: z.string().nullable(),
  timeframe: z.string().nullable(),
  is_archived: z.boolean(),
  settings: StrategySettingsSchema.nullable(),
  version: CodeSnapshotSchema.safeExtend({
    id: z.uuid(),
    source_hash: z.string().regex(/^[a-f0-9]{64}$/),
    execution_hash: z.string().regex(/^[a-f0-9]{64}$/),
    created_at: z.iso.datetime({ offset: true }),
  }),
});
export type CodeStrategy = z.infer<typeof CodeStrategySchema>;
export const CodeStrategyListSchema = z.object({
  items: z.array(CodeStrategySchema),
  total: z.number().int().nonnegative(),
});

export const CodePeriodSchema = z
  .object({
    start: z.iso.date(),
    end: z.iso.date(),
    capital: z
      .string()
      .regex(/^\d+(\.\d{1,8})?$/)
      .refine((v) => Number(v) > 0),
  })
  .refine((v) => v.end > v.start, { message: "종료일은 시작일 뒤여야 합니다." });

export const codeStrategyKeys = {
  list: (userId: string) => ["code-strategies", userId, "list"] as const,
  page: (userId: string, offset: number, selectedId?: string) =>
    offset === 0 && !selectedId
      ? codeStrategyKeys.list(userId)
      : ([...codeStrategyKeys.list(userId), offset, selectedId ?? null] as const),
};
