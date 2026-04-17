"use client";

// Trading React Query 훅 — Clerk JWT 자동 주입.
// 폴링은 ADR-010 기준 ≥30초로 완화. 에러 시 자동 일시 정지(error 상태에서 false 반환).

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

export { tradingKeys };

export function useOrders(
  limit = 50,
): UseQueryResult<{ items: Order[]; total: number }, Error> {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: tradingKeys.orders(limit),
    queryFn: async () => {
      const token = await getToken();
      return listOrders(limit, token);
    },
    refetchInterval: (q) =>
      q.state.status === "error" ? false : ORDERS_REFETCH_INTERVAL_MS,
  });
}

export function useKillSwitchEvents(): UseQueryResult<
  { items: KillSwitchEvent[] },
  Error
> {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: tradingKeys.killSwitch(),
    queryFn: async () => {
      const token = await getToken();
      return listKillSwitchEvents(token);
    },
    refetchInterval: (q) =>
      q.state.status === "error" ? false : KILL_SWITCH_REFETCH_INTERVAL_MS,
  });
}

export function useResolveKillSwitchEvent(): UseMutationResult<
  void,
  Error,
  string
> {
  const { getToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      return resolveKillSwitchEvent(id, token);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: tradingKeys.killSwitch() });
    },
  });
}

export function useExchangeAccounts(): UseQueryResult<ExchangeAccount[], Error> {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: tradingKeys.exchangeAccounts(),
    queryFn: async () => {
      const token = await getToken();
      return listExchangeAccounts(token);
    },
  });
}
