// Sprint FE-04: 백테스트 REST 클라이언트 — apiFetch + Clerk JWT + Zod 런타임 파싱으로
// /api/v1/backtests(CRUD·진행률·거래 내역·공유 링크)와 /api/v1/stress-tests(몬테카를로·
// 워크포워드·비용가정·파라미터 안정성 민감도 분석), 지표 변환(convert-indicator) 엔드포인트를 감싼다.

import { apiFetch } from "@/lib/api-client";

import type { BacktestListQuery, BacktestTradesQuery } from "./query-keys";
import {
  BacktestCancelResponseSchema,
  BacktestCreatedResponseSchema,
  BacktestDetailSchema,
  BacktestListResponseSchema,
  BacktestProgressResponseSchema,
  ConvertIndicatorResponseSchema,
  CreateBacktestRequestSchema,
  CreateCostAssumptionRequestSchema,
  CreateMonteCarloRequestSchema,
  CreateParamStabilityRequestSchema,
  CreateWalkForwardRequestSchema,
  ShareTokenResponseSchema,
  StressTestCreatedResponseSchema,
  StressTestDetailSchema,
  StressTestListResponseSchema,
  TradeOhlcvResponseSchema,
  TradeListResponseSchema,
  type BacktestCancelResponse,
  type BacktestCreatedResponse,
  type BacktestDetail,
  type BacktestListResponse,
  type BacktestProgressResponse,
  type ConvertIndicatorRequest,
  type ConvertIndicatorResponse,
  type CreateBacktestRequest,
  type CreateCostAssumptionRequest,
  type CreateMonteCarloRequest,
  type CreateParamStabilityRequest,
  type CreateWalkForwardRequest,
  type ShareTokenResponse,
  type StressTestCreatedResponse,
  type StressTestDetail,
  type StressTestListResponse,
  type TradeOhlcvResponse,
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
    params: {
      limit: query.limit,
      offset: query.offset,
      order_by: query.order_by,
      order: query.order,
    },
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

export async function getTradeOhlcv(
  _userId: string,
  backtestId: string,
  tradeIndex: number,
  getToken: () => Promise<string | null>,
): Promise<TradeOhlcvResponse> {
  const raw = await apiFetch<unknown>(
    `${BACKTESTS_PATH}/${backtestId}/trades/${tradeIndex}/ohlcv`,
    {
      method: "GET",
      token: await getToken(),
    },
  );
  return TradeOhlcvResponseSchema.parse(raw);
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

// Sprint 50 — Cost Assumption Sensitivity (fees x slippage 9-cell grid).
export async function postCostAssumption(
  body: CreateCostAssumptionRequest,
  token: string | null,
): Promise<StressTestCreatedResponse> {
  const parsed = CreateCostAssumptionRequestSchema.parse(body);
  const raw = await apiFetch<unknown>(
    `${STRESS_TESTS_PATH}/cost-assumption-sensitivity`,
    {
      method: "POST",
      token,
      body: parsed,
    },
  );
  return StressTestCreatedResponseSchema.parse(raw);
}

// Sprint 52 BL-223 — Param Stability (pine input_overrides 9-cell grid).
export async function postParamStability(
  body: CreateParamStabilityRequest,
  token: string | null,
): Promise<StressTestCreatedResponse> {
  const parsed = CreateParamStabilityRequestSchema.parse(body);
  const raw = await apiFetch<unknown>(
    `${STRESS_TESTS_PATH}/param-stability`,
    {
      method: "POST",
      token,
      body: parsed,
    },
  );
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

export async function listStressTests(
  backtestId: string,
  limit: number,
  token: string | null,
): Promise<StressTestListResponse> {
  const raw = await apiFetch<unknown>(STRESS_TESTS_PATH, {
    method: "GET",
    token,
    params: { backtest_id: backtestId, limit, offset: 0 },
  });
  return StressTestListResponseSchema.parse(raw);
}

// --- Indicator Convert -------------------------------------------------------

export async function convertIndicator(
  req: ConvertIndicatorRequest,
  token: string | null,
): Promise<ConvertIndicatorResponse> {
  const raw = await apiFetch<unknown>("/api/v1/strategies/convert-indicator", {
    method: "POST",
    token,
    body: req,
  });
  return ConvertIndicatorResponseSchema.parse(raw);
}
