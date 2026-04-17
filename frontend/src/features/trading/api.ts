// Trading 도메인 API — apiFetch + Clerk JWT 주입 일원화 (Strategy 모듈과 동일).
// 토큰 주입은 hooks.ts에서 `useAuth().getToken()`으로 담당하여 이 모듈은 pure.

import { apiFetch } from "@/lib/api-client";

import {
  ExchangeAccountListResponseSchema,
  KillSwitchListResponseSchema,
  OrderListResponseSchema,
  type ExchangeAccount,
  type KillSwitchEvent,
  type Order,
} from "./schemas";

const ORDERS_PATH = "/api/v1/orders";
const KILL_SWITCH_PATH = "/api/v1/kill-switch/events";
const EXCHANGE_ACCOUNTS_PATH = "/api/v1/exchange-accounts";

export async function listOrders(
  limit: number,
  token: string | null,
): Promise<{ items: Order[]; total: number }> {
  const raw = await apiFetch<unknown>(ORDERS_PATH, {
    method: "GET",
    token,
    params: { limit, offset: 0 },
  });
  return OrderListResponseSchema.parse(raw);
}

export async function listKillSwitchEvents(
  token: string | null,
  limit = 20,
): Promise<{ items: KillSwitchEvent[] }> {
  const raw = await apiFetch<unknown>(KILL_SWITCH_PATH, {
    method: "GET",
    token,
    params: { limit },
  });
  return KillSwitchListResponseSchema.parse(raw);
}

export async function resolveKillSwitchEvent(
  id: string,
  token: string | null,
  note = "manual unlock from dashboard",
): Promise<void> {
  await apiFetch<void>(`${KILL_SWITCH_PATH}/${id}/resolve`, {
    method: "POST",
    token,
    body: { note },
  });
}

export async function listExchangeAccounts(
  token: string | null,
): Promise<ExchangeAccount[]> {
  const raw = await apiFetch<unknown>(EXCHANGE_ACCOUNTS_PATH, {
    method: "GET",
    token,
  });
  return ExchangeAccountListResponseSchema.parse(raw).items;
}
