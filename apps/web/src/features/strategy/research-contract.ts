import { z } from "zod/v4";

export const CodeExecutionPolicySchema = z.enum(["code_v1", "code_research_v1"]);
export type CodeExecutionPolicy = z.infer<typeof CodeExecutionPolicySchema>;

export const ResearchExecutionSchema = z.strictObject({
  contract_version: z.literal(1),
  exit_policy: z.enum(["signal_only_v1", "swing_two_bar_v1"]),
  reentry_policy: z.literal("close_then_reenter_v1"),
  signal_mode: z.enum(["shared_events", "position_feedback"]),
  signal_mapping_hash: z.string().regex(/^[a-f0-9]{64}$/),
});
export type ResearchExecution = z.infer<typeof ResearchExecutionSchema>;

export function researchPolicyLabel(policy: ResearchExecution): string {
  return policy.exit_policy === "signal_only_v1" ? "A · 신호 청산" : "B · 손절·반익절·추적";
}
