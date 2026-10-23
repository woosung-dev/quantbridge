import { apiFetch } from "@/lib/api-client";
import { CodeStrategySchema, type CodeStrategy } from "./code-schemas";

export async function getCodeResultStrategy(
  id: string,
  token: string | null,
): Promise<CodeStrategy> {
  return CodeStrategySchema.parse(
    await apiFetch<unknown>(`/api/v1/strategies/code/${id}`, { token }),
  );
}
