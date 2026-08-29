"use client";

import { usePreviewParse, useStrategy } from "@/features/strategy/hooks";
import type { InputDecl } from "@/features/strategy/schemas";

export interface StrategyInputsResult {
  inputs: InputDecl[];
  isLoading: boolean;
  error: Error | null;
}

/** strategyId → pine_source 조회 → Pine input 선언 목록을 파싱한다. */
export function useStrategyInputs(strategyId: string | undefined): StrategyInputsResult {
  const strategyQuery = useStrategy(strategyId);
  const previewQuery = usePreviewParse(strategyQuery.data?.pine_source ?? "");

  return {
    inputs: previewQuery.data?.inputs ?? [],
    isLoading: strategyQuery.isLoading || previewQuery.isLoading,
    error: strategyQuery.error ?? previewQuery.error,
  };
}
