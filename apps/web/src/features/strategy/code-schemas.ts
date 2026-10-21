import { z } from "zod/v4";

import { StrategySettingsSchema } from "./schemas";

export const CodeLanguageSchema = z.enum(["python", "typescript", "pine"]);
export type CodeLanguage = z.infer<typeof CodeLanguageSchema>;
export const CODE_LANGUAGE_LABELS: Record<CodeLanguage, string> = {
  python: "Python",
  typescript: "TypeScript",
  pine: "Pine Script",
};
export const CodeTimeframeSchema = z.enum(["1h", "4h", "1d"]);
const JsonObjectSchema = z.record(z.string(), z.json());

export const CodeSnapshotSchema = z.object({
  schema_version: z.literal(1),
  execution_policy: z.literal("code_v1"),
  language: CodeLanguageSchema,
  source_code: z
    .string()
    .min(1)
    .max(131072)
    .refine((value) => value.trim().length > 0),
  warmup_bars: z.number().int().min(1).max(10000),
  params: JsonObjectSchema,
  provenance: JsonObjectSchema,
});
export const SaveCodeStrategySchema = z.object({
  name: z.string().trim().min(1).max(120),
  symbol: z.string().trim().min(3).max(32),
  timeframe: CodeTimeframeSchema,
  code: CodeSnapshotSchema,
  settings: StrategySettingsSchema,
});
export type SaveCodeStrategy = z.infer<typeof SaveCodeStrategySchema>;
export const CodeStrategySchema = z.object({
  id: z.uuid(),
  name: z.string(),
  description: z.string().nullable(),
  symbol: z.string().nullable(),
  timeframe: z.string().nullable(),
  is_archived: z.boolean(),
  settings: StrategySettingsSchema.nullable(),
  version: CodeSnapshotSchema.extend({
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
};
