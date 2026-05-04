// Sprint 7c: Strategy CRUD API — apiFetch + Clerk JWT + Zod 런타임 검증.
// Clerk getToken()은 hooks.ts에서 주입하여 이 모듈을 pure function 유지.

import { apiFetch } from "@/lib/api-client";

import {
  CreateStrategyRequestSchema,
  ParsePreviewResponseSchema,
  StrategyCreateResponseSchema,
  StrategyListQuerySchema,
  StrategyListResponseSchema,
  StrategyResponseSchema,
  UpdateStrategyRequestSchema,
  UpdateStrategySettingsRequestSchema,
  WebhookRotateResponseSchema,
  type CreateStrategyRequest,
  type ParsePreviewResponse,
  type StrategyCreateResponse,
  type StrategyListQuery,
  type StrategyListResponse,
  type StrategyResponse,
  type UpdateStrategyRequest,
  type UpdateStrategySettingsRequest,
  type WebhookRotateResponse,
} from "./schemas";

const STRATEGIES_PATH = "/api/v1/strategies";
const PARSE_PATH = "/api/v1/strategies/parse";

export async function listStrategies(
  query: StrategyListQuery,
  token: string | null,
): Promise<StrategyListResponse> {
  const parsed = StrategyListQuerySchema.parse(query);
  const raw = await apiFetch<unknown>(STRATEGIES_PATH, {
    method: "GET",
    token,
    params: {
      limit: parsed.limit,
      offset: parsed.offset,
      parse_status: parsed.parse_status,
      is_archived: parsed.is_archived,
    },
  });
  return StrategyListResponseSchema.parse(raw);
}

export async function getStrategy(
  id: string,
  token: string | null,
): Promise<StrategyResponse> {
  const raw = await apiFetch<unknown>(`${STRATEGIES_PATH}/${id}`, {
    method: "GET",
    token,
  });
  return StrategyResponseSchema.parse(raw);
}

export async function createStrategy(
  body: CreateStrategyRequest,
  token: string | null,
): Promise<StrategyCreateResponse> {
  // Sprint 13 Phase A.1.4: response 에 webhook_secret plaintext 1회 포함.
  // 호출자 (useCreateStrategy onSuccess) 가 sessionStorage 에 캐시 (TTL 30분).
  const parsed = CreateStrategyRequestSchema.parse(body);
  const raw = await apiFetch<unknown>(STRATEGIES_PATH, {
    method: "POST",
    token,
    body: parsed,
  });
  return StrategyCreateResponseSchema.parse(raw);
}

// Sprint 13 Phase A.2: webhook secret rotate (Sprint 6 broken bug fix 후 정상 동작).
// plaintext 는 응답에서 1회만 받음 — 호출자가 sessionStorage 캐시.
export async function rotateWebhookSecret(
  strategyId: string,
  token: string | null,
): Promise<WebhookRotateResponse> {
  const raw = await apiFetch<unknown>(
    `${STRATEGIES_PATH}/${strategyId}/rotate-webhook-secret`,
    {
      method: "POST",
      token,
    },
  );
  return WebhookRotateResponseSchema.parse(raw);
}

export async function updateStrategy(
  id: string,
  body: UpdateStrategyRequest,
  token: string | null,
): Promise<StrategyResponse> {
  const parsed = UpdateStrategyRequestSchema.parse(body);
  const raw = await apiFetch<unknown>(`${STRATEGIES_PATH}/${id}`, {
    method: "PUT",
    token,
    body: parsed,
  });
  return StrategyResponseSchema.parse(raw);
}

// Sprint 27 BL-137 — PUT /strategies/{id}/settings (trading params).
export async function updateStrategySettings(
  id: string,
  body: UpdateStrategySettingsRequest,
  token: string | null,
): Promise<StrategyResponse> {
  const parsed = UpdateStrategySettingsRequestSchema.parse(body);
  const raw = await apiFetch<unknown>(`${STRATEGIES_PATH}/${id}/settings`, {
    method: "PUT",
    token,
    body: parsed,
  });
  return StrategyResponseSchema.parse(raw);
}

export async function deleteStrategy(
  id: string,
  token: string | null,
): Promise<void> {
  await apiFetch<void>(`${STRATEGIES_PATH}/${id}`, {
    method: "DELETE",
    token,
  });
}

export async function parseStrategy(
  pine_source: string,
  token: string | null,
): Promise<ParsePreviewResponse> {
  const raw = await apiFetch<unknown>(PARSE_PATH, {
    method: "POST",
    token,
    body: { pine_source },
  });
  return ParsePreviewResponseSchema.parse(raw);
}
