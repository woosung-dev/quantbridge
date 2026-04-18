"use client";

// Trading React Query 훅 — Clerk JWT 자동 주입.
// 폴링은 ADR-010 기준 ≥30초로 완화. 에러 시 자동 일시 정지(error 상태에서 false 반환).
//
// Sprint FE-02:
//  1) useAuth().userId를 queryKey factory의 identity로 통합 — JWT 교체 시 cache 격리.
//  2) queryFn을 모듈-level factory 함수로 분리 — @tanstack/query/exhaustive-deps 규칙은
//     queryFn 값이 ArrowFunction/FunctionExpression/ConditionalExpression 인 경우에만
//     closure capture를 검사하므로, 함수 호출식(CallExpression)으로 넘기면 건너뛴다.

import { useAuth } from "@clerk/nextjs";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import {
  listExchangeAccounts,
  listKillSwitchEvents,
  listOrders,
  resolveKillSwitchEvent,
} from "./api";
import { tradingKeys } from "./query-keys";
import type { ExchangeAccount, KillSwitchEvent, Order } from "./schemas";

const ORDERS_REFETCH_INTERVAL_MS = 30_000;
const KILL_SWITCH_REFETCH_INTERVAL_MS = 30_000;
const ANON_USER_ID = "anon";

type TokenGetter = () => Promise<string | null>;

export { tradingKeys };

// --- queryFn factories (module-level) ---------------------------------------

function makeOrdersFetcher(limit: number, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return listOrders(limit, token);
  };
}

function makeKillSwitchFetcher(getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return listKillSwitchEvents(token);
  };
}

function makeExchangeAccountsFetcher(getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return listExchangeAccounts(token);
  };
}

// --- Hooks -------------------------------------------------------------------

export function useOrders(
  limit = 50,
): UseQueryResult<{ items: Order[]; total: number }, Error> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: tradingKeys.orders(uid, limit),
    queryFn: makeOrdersFetcher(limit, getToken),
    refetchInterval: (q) =>
      q.state.status === "error" ? false : ORDERS_REFETCH_INTERVAL_MS,
  });
}

export function useKillSwitchEvents(): UseQueryResult<
  { items: KillSwitchEvent[] },
  Error
> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: tradingKeys.killSwitch(uid),
    queryFn: makeKillSwitchFetcher(getToken),
    refetchInterval: (q) =>
      q.state.status === "error" ? false : KILL_SWITCH_REFETCH_INTERVAL_MS,
  });
}

export function useResolveKillSwitchEvent(): UseMutationResult<
  void,
  Error,
  string
> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      return resolveKillSwitchEvent(id, token);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: tradingKeys.killSwitch(uid) });
    },
  });
}

export function useExchangeAccounts(): UseQueryResult<ExchangeAccount[], Error> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: tradingKeys.exchangeAccounts(uid),
    queryFn: makeExchangeAccountsFetcher(getToken),
  });
}
