// Sprint FE-04: Backtest REST client — apiFetch + Clerk JWT + Zod runtime parse.

import { apiFetch } from "@/lib/api-client";

import type { BacktestListQuery, BacktestTradesQuery } from "./query-keys";
import {
  BacktestCancelResponseSchema,
  BacktestCreatedResponseSchema,
  BacktestDetailSchema,
  BacktestListResponseSchema,
  BacktestProgressResponseSchema,
  CreateBacktestRequestSchema,
  CreateMonteCarloRequestSchema,
  CreateWalkForwardRequestSchema,
  ShareTokenResponseSchema,
  StressTestCreatedResponseSchema,
  StressTestDetailSchema,
  TradeListResponseSchema,
  type BacktestCancelResponse,
  type BacktestCreatedResponse,
  type BacktestDetail,
  type BacktestListResponse,
  type BacktestProgressResponse,
  type CreateBacktestRequest,
  type CreateMonteCarloRequest,
  type CreateWalkForwardRequest,
  type ShareTokenResponse,
  type StressTestCreatedResponse,
  type StressTestDetail,
  type TradeListResponse,
} from "./schemas";

const BACKTESTS_PATH = "/api/v1/backtests";
const STRESS_TESTS_PATH = "/api/v1/stress-tests";

export async function listBacktests(
  query: BacktestListQuery,
  token: string | null,
): Promise<BacktestListResponse> {
  const raw = await apiFetch<unknown>(BACKTESTS_PATH, {
    method: "GET",
    token,
    params: { limit: query.limit, offset: query.offset },
  });
  return BacktestListResponseSchema.parse(raw);
}

export async function getBacktest(
  id: string,
  token: string | null,
): Promise<BacktestDetail> {
  const raw = await apiFetch<unknown>(`${BACKTESTS_PATH}/${id}`, {
    method: "GET",
    token,
  });
  return BacktestDetailSchema.parse(raw);
}

export async function createBacktest(
  body: CreateBacktestRequest,
  token: string | null,
): Promise<BacktestCreatedResponse> {
  const parsed = CreateBacktestRequestSchema.parse(body);
  const raw = await apiFetch<unknown>(BACKTESTS_PATH, {
    method: "POST",
    token,
    body: parsed,
  });
  return BacktestCreatedResponseSchema.parse(raw);
}

export async function getBacktestProgress(
  id: string,
  token: string | null,
): Promise<BacktestProgressResponse> {
  const raw = await apiFetch<unknown>(`${BACKTESTS_PATH}/${id}/progress`, {
    method: "GET",
    token,
  });
  return BacktestProgressResponseSchema.parse(raw);
}

export async function listBacktestTrades(
  id: string,
  query: BacktestTradesQuery,
  token: string | null,
): Promise<TradeListResponse> {
  const raw = await apiFetch<unknown>(`${BACKTESTS_PATH}/${id}/trades`, {
    method: "GET",
    token,
    params: { limit: query.limit, offset: query.offset },
  });
  return TradeListResponseSchema.parse(raw);
}

export async function cancelBacktest(
  id: string,
  token: string | null,
): Promise<BacktestCancelResponse> {
  const raw = await apiFetch<unknown>(`${BACKTESTS_PATH}/${id}/cancel`, {
    method: "POST",
    token,
  });
  return BacktestCancelResponseSchema.parse(raw);
}

export async function deleteBacktest(
  id: string,
  token: string | null,
): Promise<void> {
  await apiFetch<void>(`${BACKTESTS_PATH}/${id}`, {
    method: "DELETE",
    token,
  });
}

// --- Sprint 41 Worker H — share link (public read-only + revoke) ----------

export async function createBacktestShare(
  id: string,
  token: string | null,
): Promise<ShareTokenResponse> {
  const raw = await apiFetch<unknown>(`${BACKTESTS_PATH}/${id}/share`, {
    method: "POST",
    token,
  });
  return ShareTokenResponseSchema.parse(raw);
}

export async function revokeBacktestShare(
  id: string,
  token: string | null,
): Promise<void> {
  await apiFetch<void>(`${BACKTESTS_PATH}/${id}/share`, {
    method: "DELETE",
    token,
  });
}

export async function viewBacktestShare(
  shareToken: string,
): Promise<BacktestDetail> {
  // public — Clerk JWT 미사용. apiFetch 가 token=null 시 Authorization header 미부착.
  const raw = await apiFetch<unknown>(
    `${BACKTESTS_PATH}/share/${shareToken}`,
    {
      method: "GET",
      token: null,
    },
  );
  return BacktestDetailSchema.parse(raw);
}

// --- Stress Test (Phase C) -----------------------------------------------

export async function postMonteCarlo(
  body: CreateMonteCarloRequest,
  token: string | null,
): Promise<StressTestCreatedResponse> {
  const parsed = CreateMonteCarloRequestSchema.parse(body);
  const raw = await apiFetch<unknown>(`${STRESS_TESTS_PATH}/monte-carlo`, {
    method: "POST",
    token,
    body: parsed,
  });
  return StressTestCreatedResponseSchema.parse(raw);
}

export async function postWalkForward(
  body: CreateWalkForwardRequest,
  token: string | null,
): Promise<StressTestCreatedResponse> {
  const parsed = CreateWalkForwardRequestSchema.parse(body);
  const raw = await apiFetch<unknown>(`${STRESS_TESTS_PATH}/walk-forward`, {
    method: "POST",
    token,
    body: parsed,
  });
  return StressTestCreatedResponseSchema.parse(raw);
}

export async function getStressTest(
  id: string,
  token: string | null,
): Promise<StressTestDetail> {
  const raw = await apiFetch<unknown>(`${STRESS_TESTS_PATH}/${id}`, {
    method: "GET",
    token,
  });
  return StressTestDetailSchema.parse(raw);
}
