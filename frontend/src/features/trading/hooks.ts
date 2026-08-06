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
//  LESSON-004 / H-1 (.claude/rules/frontend.md): useEffect dep 에 React Query data 객체 직접
//  사용 금지. H-1 의 공식 대안은 "dep array 없는 sync useEffect" — 매 commit 직후 실행되며,
//  prevStatesRef 로 실질 변경만 걸러내므로 중복 toast 위험 없음.

import { useEffect, useRef } from "react";
import {
  useQueries,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";
import { toast } from "sonner";

import { useAuthCtx, type TokenGetter } from "@/hooks/use-auth-ctx";
import { useInvalidatingMutation } from "@/hooks/use-invalidating-mutation";
import { ApiError } from "@/lib/api-client";
import { makeRefetchInterval } from "@/lib/query-poll";

import {
  cancelOrder,
  deleteExchangeAccount,
  getAccountBalance,
  getLiquidationInfo,
  listExchangeAccounts,
  listKillSwitchEvents,
  listOrders,
  registerExchangeAccount,
  resolveKillSwitchEvent,
  type LiquidationParams,
} from "./api";
import { tradingKeys } from "./query-keys";
import type {
  ExchangeAccount,
  AccountBalance,
  CancelOrderResponse,
  KillSwitchEvent,
  LiquidationInfoResponse,
  Order,
  RegisterAccountRequest,
} from "./schemas";

// Sprint 12 Phase C — test-public 상수 + helper export.
// useOrders refetchInterval 분기 로직 (active orders > 0 ? 5s : 30s) 단위 테스트용.
export const ORDERS_REFETCH_INTERVAL_ACTIVE_MS = 5_000;
export const ORDERS_REFETCH_INTERVAL_IDLE_MS = 30_000;
const KILL_SWITCH_REFETCH_INTERVAL_MS = 30_000;
const BALANCE_REFETCH_INTERVAL_MS = 30_000;

// "진행 중" 상태 — 이 상태가 존재할 때 빠른 폴링
export const ACTIVE_ORDER_STATES: ReadonlySet<Order["state"]> = new Set([
  "pending",
  "submitted",
]);
export const OPEN_ORDER_STATES = ["pending", "submitted"] as const;

/**
 * Sprint 12 Phase C — pure helper for unit testing.
 * orders 배열에 active state(`pending|submitted`) 가 1개라도 있으면 5s, 없으면 30s.
 */
export function computeOrdersRefetchInterval(
  orders: ReadonlyArray<Pick<Order, "state">>,
): number {
  const hasActive = orders.some((o) => ACTIVE_ORDER_STATES.has(o.state));
  return hasActive
    ? ORDERS_REFETCH_INTERVAL_ACTIVE_MS
    : ORDERS_REFETCH_INTERVAL_IDLE_MS;
}

// LESSON-004 가드 내장 폴링 — 진행 중 주문이 있으면 빠른 폴링, 없으면 느린 폴링.
const ordersRefetchInterval = makeRefetchInterval<{ items: Order[]; total: number }>(
  (data) => computeOrdersRefetchInterval(data?.items ?? []),
);

const killSwitchRefetchInterval = makeRefetchInterval<{
  items: KillSwitchEvent[];
}>(() => KILL_SWITCH_REFETCH_INTERVAL_MS);

const balanceRefetchInterval = makeRefetchInterval<AccountBalance>(
  () => BALANCE_REFETCH_INTERVAL_MS,
);

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

export { tradingKeys };

// --- queryFn factories (module-level) ---------------------------------------

function makeOrdersFetcher(
  limit: number,
  getToken: TokenGetter,
  states: readonly Order["state"][] | undefined,
) {
  return async () => {
    const token = await getToken();
    return listOrders(limit, token, { states });
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

function makeAccountBalanceFetcher(accountId: string, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return getAccountBalance(accountId, token);
  };
}

function makeLiquidationFetcher(
  params: LiquidationParams | null,
  getToken: TokenGetter,
) {
  return async () => {
    if (params === null) {
      throw new Error("liquidation params required");
    }
    const token = await getToken();
    return getLiquidationInfo(params, token);
  };
}

// --- Hooks -------------------------------------------------------------------

export function useOrders(
  limit = 50,
  // 셸 nav 배지처럼 count 만 필요한 소비처는 notifyTransitions:false 로 전환 toast 를 끈다.
  // (기본 true = 기존 동작 불변. limit 이 다른 인스턴스마다 prevStatesRef 가 분리돼
  //  같은 주문 전환에 toast 가 중복 발화하던 문제를 count 전용 경로에서 차단한다.)
  options?: { notifyTransitions?: boolean; states?: readonly Order["state"][] },
): UseQueryResult<{ items: Order[]; total: number }, Error> {
  const notifyTransitions = options?.notifyTransitions ?? true;
  const { uid, getToken } = useAuthCtx();

  // 이전 주문 state 추적 — Map<orderId, state>
  // useRef 사용: 렌더 트리거 없이 mutable reference 유지
  const prevStatesRef = useRef<Map<string, Order["state"]>>(new Map());
  // 마지막으로 전환 감지를 수행한 폴링 응답의 dataUpdatedAt — 커밋마다 재순회 방지 가드.
  const processedAtRef = useRef(0);

  const query = useQuery({
    queryKey: tradingKeys.orders(uid, limit, options?.states),
    queryFn: makeOrdersFetcher(limit, getToken, options?.states),
    refetchInterval: ordersRefetchInterval,
  });

  // C-3: 주문 상태 전환 감지 + toast.
  // H-1 준수: dep array 없는 sync useEffect — 매 commit 후 실행하되,
  // dataUpdatedAt 스칼라 가드로 새 폴링 응답이 있을 때만 orders 를 순회한다.
  useEffect(() => {
    if (!notifyTransitions) return;
    if (query.dataUpdatedAt === processedAtRef.current) return;
    processedAtRef.current = query.dataUpdatedAt;

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
  });

  return query;
}

export function useOpenOrdersCount(): number | undefined {
  const { data } = useOrders(1, {
    notifyTransitions: false,
    states: OPEN_ORDER_STATES,
  });
  return data?.total;
}

export function useCancelOrder(): UseMutationResult<CancelOrderResponse, Error, string> {
  const { uid } = useAuthCtx();
  const queryClient = useQueryClient();
  return useInvalidatingMutation(
    {
      mutationFn: (orderId: string, token) => cancelOrder(orderId, token),
      invalidateKeys: (userId) => [tradingKeys.ordersPrefix(userId)],
    },
    {
      onSuccess: (result) => {
        if ("order_id" in result) toast.info("거래소에 취소를 요청했습니다");
      },
      onError: (error) => {
        if (error instanceof ApiError && error.status === 409) {
          toast.error("이미 진행된 주문이라 취소할 수 없습니다.");
          void queryClient.invalidateQueries({ queryKey: tradingKeys.ordersPrefix(uid) });
          return;
        }
        toast.error("주문 취소에 실패했습니다. 잠시 후 다시 시도해주세요.");
      },
    },
  );
}

export function useKillSwitchEvents(): UseQueryResult<
  { items: KillSwitchEvent[] },
  Error
> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: tradingKeys.killSwitch(uid),
    queryFn: makeKillSwitchFetcher(getToken),
    refetchInterval: killSwitchRefetchInterval,
  });
}

export function useResolveKillSwitchEvent(): UseMutationResult<
  void,
  Error,
  string
> {
  return useInvalidatingMutation({
    mutationFn: (id: string, token) => resolveKillSwitchEvent(id, token),
    invalidateKeys: (uid) => [tradingKeys.killSwitch(uid)],
  });
}

export function useExchangeAccounts(): UseQueryResult<ExchangeAccount[], Error> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: tradingKeys.exchangeAccounts(uid),
    queryFn: makeExchangeAccountsFetcher(getToken),
    // Sprint 14 Phase B-2 — dogfood 지연 회피용 retry: 1.
    retry: 1,
  });
}

/** 활성 세션이 참조하는 계정의 잔고를 계정별로 폴링한다. */
export function useAccountBalances(
  accounts: readonly Pick<ExchangeAccount, "id">[],
): UseQueryResult<AccountBalance, Error>[] {
  const { uid, getToken } = useAuthCtx();
  return useQueries({
    queries: accounts.map((account) => ({
      queryKey: tradingKeys.balance(uid, account.id),
      queryFn: makeAccountBalanceFetcher(account.id, getToken),
      enabled: Boolean(account.id),
      refetchInterval: balanceRefetchInterval,
    })),
  });
}

export function useRegisterExchangeAccount(): UseMutationResult<
  ExchangeAccount,
  Error,
  RegisterAccountRequest
> {
  return useInvalidatingMutation({
    mutationFn: (req: RegisterAccountRequest, token) =>
      registerExchangeAccount(req, token),
    invalidateKeys: (uid) => [tradingKeys.exchangeAccounts(uid)],
  });
}

export function useDeleteExchangeAccount(): UseMutationResult<void, Error, string> {
  return useInvalidatingMutation({
    mutationFn: (id: string, token) => deleteExchangeAccount(id, token),
    invalidateKeys: (uid) => [tradingKeys.exchangeAccounts(uid)],
  });
}

// Wave 2 — 청산가 조회 hook (W-B 계약 소비). LESSON-005: queryKey userId 첫 인자.
// graceful: params 완비(symbol/entry_price 존재 + leverage>0) 시에만 enabled →
// W-B 미머지 상태에선 호출부가 params 를 비워두면 미발사 → 콘솔에러 0. 발사되더라도
// 404/연결거부는 error 상태로 흡수되어 호출부가 graceful-empty 렌더. retry 0 (premature noise 회피).
export function useLiquidationInfo(
  params: LiquidationParams | null,
): UseQueryResult<LiquidationInfoResponse, Error> {
  const { uid, getToken } = useAuthCtx();
  const enabled =
    params !== null &&
    params.symbol.length > 0 &&
    params.entry_price.length > 0 &&
    params.leverage > 0;
  return useQuery({
    queryKey: tradingKeys.liquidation(
      uid,
      params ?? { symbol: "", side: "buy", entry_price: "", leverage: 0 },
    ),
    queryFn: makeLiquidationFetcher(params, getToken),
    enabled,
    retry: false,
  });
}

// Sprint 13 Phase B: KillSwitch active 시 주문 진입 차단 helper.
// 기존 useKillSwitchEvents 를 재사용 — resolved_at == null 인 이벤트가 1개라도 있으면 true.
// Test Order Dialog 와 향후 manual 주문 UI 에서 button disabled 판단에 사용.
export function useIsOrderDisabledByKs(): boolean {
  const { data } = useKillSwitchEvents();
  if (!data) return false;
  return data.items.some((e) => !e.resolved_at);
}
