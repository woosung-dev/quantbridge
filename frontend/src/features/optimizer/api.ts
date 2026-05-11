// Optimizer REST client — apiFetch + Clerk JWT + Zod runtime parse.

import { apiFetch } from "@/lib/api-client";

import type { OptimizationRunListQuery } from "./query-keys";
import {
  CreateOptimizationRunRequestSchema,
  OptimizationRunListResponseSchema,
  OptimizationRunResponseSchema,
  type CreateOptimizationRunRequest,
  type OptimizationRunListResponse,
  type OptimizationRunResponse,
} from "./schemas";

const OPTIMIZER_PATH = "/api/v1/optimizer";

export async function postGridSearch(
  body: CreateOptimizationRunRequest,
  token: string | null,
): Promise<OptimizationRunResponse> {
  const parsed = CreateOptimizationRunRequestSchema.parse(body);
  const raw = await apiFetch<unknown>(`${OPTIMIZER_PATH}/runs/grid-search`, {
    method: "POST",
    token,
    body: parsed,
  });
  return OptimizationRunResponseSchema.parse(raw);
}

export async function getOptimizationRun(
  id: string,
  token: string | null,
): Promise<OptimizationRunResponse> {
  const raw = await apiFetch<unknown>(`${OPTIMIZER_PATH}/runs/${id}`, {
    method: "GET",
    token,
  });
  return OptimizationRunResponseSchema.parse(raw);
}

export async function listOptimizationRuns(
  query: OptimizationRunListQuery,
  token: string | null,
): Promise<OptimizationRunListResponse> {
  const params: Record<string, string | number> = {
    limit: query.limit,
    offset: query.offset,
  };
  if (query.backtest_id) {
    params.backtest_id = query.backtest_id;
  }
  const raw = await apiFetch<unknown>(`${OPTIMIZER_PATH}/runs`, {
    method: "GET",
    token,
    params,
  });
  return OptimizationRunListResponseSchema.parse(raw);
}
