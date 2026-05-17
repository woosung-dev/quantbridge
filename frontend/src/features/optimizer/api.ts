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

// Sprint 55 — Bayesian executor submit (ADR-013 §6 #5).
// 별도 endpoint 결정 (단일 endpoint discriminated 분기 X) — Sprint 54 grid-search 패턴 mirror.
export async function postBayesianSearch(
  body: CreateOptimizationRunRequest,
  token: string | null,
): Promise<OptimizationRunResponse> {
  const parsed = CreateOptimizationRunRequestSchema.parse(body);
  const raw = await apiFetch<unknown>(`${OPTIMIZER_PATH}/runs/bayesian`, {
    method: "POST",
    token,
    body: parsed,
  });
  return OptimizationRunResponseSchema.parse(raw);
}

// Sprint 56 — Genetic executor submit (BL-233, Bayesian 패턴 mirror).
export async function postGeneticSearch(
  body: CreateOptimizationRunRequest,
  token: string | null,
): Promise<OptimizationRunResponse> {
  const parsed = CreateOptimizationRunRequestSchema.parse(body);
  const raw = await apiFetch<unknown>(`${OPTIMIZER_PATH}/runs/genetic`, {
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

  // Sprint 62 T-1 (BL-350/354): outer shape 만 strict parse, items 는 row-level safeParse 으로
  // schema-incompatible row (Sprint 50-52 retro-incorrect + 53-55 grammar tightening 합집합) 자동 skip.
  // 차단 효과: 1차 Multi-Agent QA 에서 Curious + Casual 가 본 raw Zod error JSON 도배 (★★★ 공통 P0).
  const outer = OptimizationRunListResponseSchema.parse(raw);
  const items: OptimizationRunResponse[] = [];
  let skippedCount = 0;
  for (const rawItem of outer.items) {
    const result = OptimizationRunResponseSchema.safeParse(rawItem);
    if (result.success) {
      items.push(result.data);
    } else {
      skippedCount += 1;
      if (process.env.NODE_ENV !== "production") {
        // dev 모드 진단 — production 무음. issues 첫 3개만 노출 (스택 도배 회피).
        console.warn(
          "[optimizer] listing row skipped (Zod parse fail):",
          result.error.issues.slice(0, 3),
        );
      }
    }
  }
  return {
    items,
    total: outer.total,
    limit: outer.limit,
    offset: outer.offset,
    skipped_count: skippedCount,
  };
}
