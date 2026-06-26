// Trading 도메인 API — apiFetch + Clerk JWT 주입 일원화 (Strategy 모듈과 동일).
// 토큰 주입은 hooks.ts에서 `useAuth().getToken()`으로 담당하여 이 모듈은 pure.

import { apiFetch } from "@/lib/api-client";

import {
  ExchangeAccountListResponseSchema,
  ExchangeAccountSchema,
  KillSwitchListResponseSchema,
  LiquidationInfoResponseSchema,
  OrderListResponseSchema,
  type ExchangeAccount,
  type KillSwitchEvent,
  type LiquidationInfoResponse,
  type Order,
  type RegisterAccountRequest,
} from "./schemas";

const ORDERS_PATH = "/api/v1/orders";
const KILL_SWITCH_PATH = "/api/v1/kill-switch/events";
const EXCHANGE_ACCOUNTS_PATH = "/api/v1/exchange-accounts";
// Wave 2 청산가 미리보기 — BE `POST /api/v1/liquidation/preview` (Wave 2 머지 완료).
const LIQUIDATION_PATH = "/api/v1/liquidation/preview";

export type LiquidationParams = {
  symbol: string;
  side: "buy" | "sell";
  entry_price: string;
  leverage: number;
};

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

export async function registerExchangeAccount(
  req: RegisterAccountRequest,
  token: string | null,
): Promise<ExchangeAccount> {
  const raw = await apiFetch<unknown>(EXCHANGE_ACCOUNTS_PATH, {
    method: "POST",
    token,
    body: req,
  });
  return ExchangeAccountSchema.parse(raw);
}

export async function deleteExchangeAccount(
  id: string,
  token: string | null,
): Promise<void> {
  await apiFetch<void>(`${EXCHANGE_ACCOUNTS_PATH}/${id}`, {
    method: "DELETE",
    token,
  });
}

// Wave 2 — 청산가 on-the-fly 조회. BE 는 POST + JSON body (LiquidationPreviewRequest).
// 인증만 게이트하는 순수 계산 → 네트워크/권한 실패 시 apiFetch 가 throw → 호출부
// (useLiquidationInfo, retry:false)는 graceful-empty 로 렌더.
export async function getLiquidationInfo(
  params: LiquidationParams,
  token: string | null,
): Promise<LiquidationInfoResponse> {
  const raw = await apiFetch<unknown>(LIQUIDATION_PATH, {
    method: "POST",
    token,
    body: {
      symbol: params.symbol,
      side: params.side,
      entry_price: params.entry_price,
      leverage: params.leverage,
    },
  });
  return LiquidationInfoResponseSchema.parse(raw);
}
