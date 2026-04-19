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
  TradeListResponseSchema,
  type BacktestCancelResponse,
  type BacktestCreatedResponse,
  type BacktestDetail,
  type BacktestListResponse,
  type BacktestProgressResponse,
  type CreateBacktestRequest,
  type TradeListResponse,
} from "./schemas";

const BACKTESTS_PATH = "/api/v1/backtests";

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
