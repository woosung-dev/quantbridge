"use client";

// Trading React Query 훅 — Clerk JWT 자동 주입.
// 폴링은 ADR-010 기준 ≥30초로 완화. 에러 시 자동 일시 정지(error 상태에서 false 반환).
//
// Sprint FE-02:
//  1) useAuth().userId를 queryKey factory의 identity로 통합 — JWT 교체 시 cache 격리.
//  2) queryFn을 모듈-level factory 함수로 분리 — @tanstack/query/exhaustive-deps 규칙은
//     queryFn 값이 ArrowFunction/FunctionExpression/ConditionalExpression 인 경우에만
//     closure capture를 검사하므로, 함수 호출식(CallExpression)으로 넘기면 건너뛴다.
//
// C-3 (H2 Sprint 1):
//  - useOrders: submitted/pending 상태 주문 존재 시 5000ms, 없으면 30000ms 조건부 폴링
//  - useRef<Map<string, Order["state"]>> 로 이전 state 추적 → toast 전환 알림
//    - submitted/pending → filled  → toast.success
//    - submitted/pending → cancelled → toast.warning
//    - submitted/pending → rejected  → toast.error
//  LESSON-004: react-hooks/exhaustive-deps disable 금지.
//              [query.data] dep는 RQ structural sharing으로 동일 객체 유지 → 안전.

import { useEffect, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";
import { toast } from "sonner";

import {
  deleteExchangeAccount,
  listExchangeAccounts,
  listKillSwitchEvents,
  listOrders,
  registerExchangeAccount,
  resolveKillSwitchEvent,
} from "./api";
import { tradingKeys } from "./query-keys";
import type {
  ExchangeAccount,
  KillSwitchEvent,
  Order,
  RegisterAccountRequest,
} from "./schemas";

const ORDERS_REFETCH_INTERVAL_ACTIVE_MS = 5_000;
const ORDERS_REFETCH_INTERVAL_IDLE_MS = 30_000;
const KILL_SWITCH_REFETCH_INTERVAL_MS = 30_000;
const ANON_USER_ID = "anon";

// "진행 중" 상태 — 이 상태가 존재할 때 빠른 폴링
const ACTIVE_ORDER_STATES: ReadonlySet<Order["state"]> = new Set([
  "pending",
  "submitted",
]);

// 이전 상태가 "진행 중"이었고 새 상태로 전환될 때 toast 알림
type TransitionRule = {
  toState: Order["state"] | Order["state"][];
  toastFn: (symbol: string) => void;
};

const STATE_TRANSITION_RULES: TransitionRule[] = [
  {
    toState: "filled",
    toastFn: (symbol) => toast.success(`${symbol} 주문 체결 완료`),
  },
  {
    toState: "cancelled",
    toastFn: (symbol) => toast.warning(`${symbol} 주문 취소됨`),
  },
  {
    toState: "rejected",
    toastFn: (symbol) => toast.error(`${symbol} 주문 거부됨`),
  },
];

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

  // 이전 주문 state 추적 — Map<orderId, state>
  // useRef 사용: 렌더 트리거 없이 mutable reference 유지
  const prevStatesRef = useRef<Map<string, Order["state"]>>(new Map());

  const query = useQuery({
    queryKey: tradingKeys.orders(uid, limit),
    queryFn: makeOrdersFetcher(limit, getToken),
    refetchInterval: (q) => {
      if (q.state.status === "error") return false;
      // 진행 중 주문이 있으면 빠른 폴링, 없으면 느린 폴링
      const items = q.state.data?.items ?? [];
      const hasActive = items.some((o) => ACTIVE_ORDER_STATES.has(o.state));
      return hasActive
        ? ORDERS_REFETCH_INTERVAL_ACTIVE_MS
        : ORDERS_REFETCH_INTERVAL_IDLE_MS;
    },
  });

  // C-3: 주문 상태 전환 감지 + toast.
  // LESSON-004: dep 배열에 query.data 객체 직접 사용.
  // RQ structural sharing 덕분에 데이터가 실제로 변경된 경우에만 새 참조 발행.
  useEffect(() => {
    const items = query.data?.items;
    if (!items) return;

    const prevMap = prevStatesRef.current;
    const currentIds = new Set<string>();

    for (const order of items) {
      currentIds.add(order.id);
      const prevState = prevMap.get(order.id);

      if (prevState && ACTIVE_ORDER_STATES.has(prevState)) {
        // 이전에 진행 중이었던 주문이 새 상태로 전환
        if (prevState !== order.state) {
          for (const rule of STATE_TRANSITION_RULES) {
            const targets = Array.isArray(rule.toState)
              ? rule.toState
              : [rule.toState];
            if (targets.includes(order.state)) {
              rule.toastFn(order.symbol);
              break;
            }
          }
        }
      }

      // 현재 state 저장
      prevMap.set(order.id, order.state);
    }

    // stale entry 정리 — 더 이상 목록에 없는 주문 id 제거 (메모리 누수 방지)
    for (const id of prevMap.keys()) {
      if (!currentIds.has(id)) {
        prevMap.delete(id);
      }
    }
  }, [query.data]);

  return query;
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

export function useRegisterExchangeAccount(): UseMutationResult<
  ExchangeAccount,
  Error,
  RegisterAccountRequest
> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (req: RegisterAccountRequest) => {
      const token = await getToken();
      return registerExchangeAccount(req, token);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: tradingKeys.exchangeAccounts(uid) });
    },
  });
}

export function useDeleteExchangeAccount(): UseMutationResult<void, Error, string> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      return deleteExchangeAccount(id, token);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: tradingKeys.exchangeAccounts(uid) });
    },
  });
}
