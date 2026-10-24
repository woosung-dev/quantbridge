"use client";

import { useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { alertRuleKeys } from "@/features/alert-rules/query-keys";
import { useLiveSessions } from "@/features/live-sessions/hooks";
import { liveSessionKeys } from "@/features/live-sessions/query-keys";
import type { LiveSession } from "@/features/live-sessions/schemas";
import { codeStrategyKeys } from "@/features/strategy/code-schemas";
import { useStrategies } from "@/features/strategy/hooks";
import { strategyKeys } from "@/features/strategy/query-keys";
import type { StrategyListItem } from "@/features/strategy/schemas";
import { useCodeStrategies } from "@/features/strategy/use-code-strategies";
import { useAuthCtx } from "@/hooks/use-auth-ctx";

import { isBybitDemoAccount } from "./account-policy";
import { useExchangeAccounts, useKillSwitchEvents } from "./hooks";
import { tradingKeys } from "./query-keys";
import type { ExchangeAccount, KillSwitchEvent } from "./schemas";

const STRATEGY_FETCH_LIMIT = 100;

type SessionSelection =
  | { status: "selected"; session: LiveSession }
  | { status: "none" | "loading" | "error" | "missing" };

/** 코크핏의 조회 대상·표시 입력·새로고침을 소유한다. URL과 ticker는 caller·leaf에 둔다. */
export function useTradingCockpitData(selectedId: string | null) {
  const queryClient = useQueryClient();
  const { uid } = useAuthCtx();
  // BL-423 — LiveSessionList와 같은 키로 비활성 세션까지 조회해 캐시를 공유한다.
  const sessionsQ = useLiveSessions(true);
  const accountsQ = useExchangeAccounts();
  const ksQ = useKillSwitchEvents();
  const strategyListQ = useStrategies({
    limit: STRATEGY_FETCH_LIMIT,
    offset: 0,
    is_archived: false,
  });
  const codeStrategiesQ = useCodeStrategies();

  const sessionItems = useMemo<readonly LiveSession[]>(
    () => sessionsQ.data?.items ?? [],
    [sessionsQ.data?.items],
  );
  // BL-533 — 별도 미러 state 없이 최근 종료된 세션도 같은 목록에서 선택한다.
  const selected = useMemo(
    () => sessionItems.find((session) => session.id === selectedId) ?? null,
    [sessionItems, selectedId],
  );
  const accountItems = useMemo<readonly ExchangeAccount[]>(
    () => accountsQ.data ?? [],
    [accountsQ.data],
  );
  const operatingAccountItems = useMemo(
    () => accountItems.filter(isBybitDemoAccount),
    [accountItems],
  );
  const ksItems = useMemo<readonly KillSwitchEvent[]>(
    () => ksQ.data?.items ?? [],
    [ksQ.data?.items],
  );
  const strategyItems = useMemo<readonly StrategyListItem[]>(
    () => strategyListQ.data?.items ?? [],
    [strategyListQ.data?.items],
  );
  const activeSessions = useMemo(() => sessionItems.filter((s) => s.is_active), [sessionItems]);
  const operatingSessionIds = useMemo(() => {
    const operatingAccountIds = new Set(operatingAccountItems.map((account) => account.id));
    return new Set(
      activeSessions
        .filter((session) => operatingAccountIds.has(session.exchange_account_id))
        .map((session) => session.id),
    );
  }, [operatingAccountItems, activeSessions]);
  const operatingActiveSessions = useMemo(
    () => activeSessions.filter((session) => operatingSessionIds.has(session.id)),
    [activeSessions, operatingSessionIds],
  );
  const strategyNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of strategyItems) map.set(s.id, s.name);
    for (const s of codeStrategiesQ.data?.items ?? []) map.set(s.id, s.name);
    return map;
  }, [strategyItems, codeStrategiesQ.data?.items]);
  const accountLabelById = useMemo(() => {
    const map = new Map<string, string>();
    for (const a of accountItems) map.set(a.id, a.label ?? `${a.exchange} ${a.mode}`);
    return map;
  }, [accountItems]);
  const activeAccountTargets = useMemo(() => {
    const ids = new Set(
      operatingActiveSessions
        .map((session) => session.exchange_account_id)
        .filter((id): id is string => typeof id === "string" && id.length > 0),
    );
    return [...ids].map((id) => ({
      id,
      label: accountLabelById.get(id) ?? id.slice(0, 8),
    }));
  }, [accountLabelById, operatingActiveSessions]);
  // 세션이 없어도 모든 Demo 계정의 잔여 포지션을 조회한다. legacy는 private 조회 대상이 아니다.
  const allAccountTargets = useMemo(
    () =>
      operatingAccountItems.map((account) => ({
        id: account.id,
        label: accountLabelById.get(account.id) ?? account.id.slice(0, 8),
        exchangeUid: account.exchange_uid,
        readOnly: account.read_only,
      })),
    [operatingAccountItems, accountLabelById],
  );
  const strategyNameBySessionId = useMemo(() => {
    const map = new Map<string, string>();
    for (const session of activeSessions) {
      const strategyId = session.strategy_id;
      map.set(
        session.id,
        typeof strategyId === "string"
          ? (strategyNameById.get(strategyId) ?? strategyId.slice(0, 8))
          : session.id.slice(0, 8),
      );
    }
    return map;
  }, [activeSessions, strategyNameById]);
  const formStrategies = useMemo(
    () => strategyItems.map((s) => ({ id: s.id, name: s.name })),
    [strategyItems],
  );
  const formAccounts = useMemo(
    () =>
      operatingAccountItems.map((a) => ({
        id: a.id,
        exchange: a.exchange,
        mode: a.mode,
        label: a.label,
        read_only: a.read_only,
      })),
    [operatingAccountItems],
  );
  const selection: SessionSelection = selected
    ? { status: "selected", session: selected }
    : !selectedId
      ? { status: "none" }
      : sessionsQ.isPending || sessionsQ.isFetching
        ? { status: "loading" }
        : sessionsQ.isError
          ? { status: "error" }
          : { status: "missing" };

  // BL-664 — 자식의 alert-rules까지 갱신하되 다른 화면의 캐시는 무효화하지 않는다.
  const refresh = () => {
    for (const queryKey of [
      tradingKeys.all(uid),
      liveSessionKeys.all(uid),
      strategyKeys.all(uid),
      codeStrategyKeys.list(uid),
      alertRuleKeys.all(uid),
    ]) {
      void queryClient.invalidateQueries({ queryKey });
    }
  };

  return {
    overview: {
      accounts: {
        count: accountItems.length,
        isError: accountsQ.isError,
        isPending: accountsQ.isPending,
      },
      sessions: {
        count: activeSessions.length,
        isError: sessionsQ.isError,
        isPending: sessionsQ.isPending,
      },
      killSwitch: {
        unresolvedCount: ksItems.filter((e) => e.resolved_at == null).length,
        isError: ksQ.isError,
        isPending: ksQ.isPending,
      },
    },
    positions: {
      balanceAccounts: activeAccountTargets,
      accounts: allAccountTargets,
      sessions: operatingActiveSessions,
      demoSessionIds: operatingSessionIds,
      resolveStrategyName: (sessionId: string, fallback: string) =>
        strategyNameBySessionId.get(sessionId) ?? fallback,
    },
    sessionTable: {
      sessions: sessionItems,
      resolveStrategyName: (id: string) => strategyNameById.get(id) ?? id.slice(0, 8),
      resolveExchangeLabel: (id: string) => accountLabelById.get(id) ?? id.slice(0, 8),
    },
    registration: {
      strategies: formStrategies,
      exchangeAccounts: formAccounts,
      activeSessionsCount: operatingActiveSessions.length,
    },
    selection,
    refresh,
  };
}
