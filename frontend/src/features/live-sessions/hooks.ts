"use client";

// Sprint 26 — Live Sessions React Query hooks.
//
// LESSON-004 의무:
//  - H-1: useEffect dep array primitive only (`[data?.id, data?.is_active]`)
//  - H-2: queryFn = module-level factory 호출식 (`makeXxxFetcher(...)`),
//         queryKey factory userId 첫 인자.
// 폴링: state 는 active 시 5s / idle 시 30s, list 는 30s.

import { useAuth } from "@clerk/nextjs";
import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import { mergeCumulativeCurves, type CurvePoint } from "./aggregate";
import {
  deactivateLiveSession,
  getLiveSessionState,
  listLiveSessionEvents,
  listLiveSessions,
  registerLiveSession,
} from "./api";
import { liveSessionKeys } from "./query-keys";
import type {
  LiveSession,
  LiveSignalEvent,
  LiveSignalState,
  RegisterLiveSessionRequest,
} from "./schemas";
import {
  LIVE_SESSION_LIST_REFETCH_MS,
  computeLiveSessionStateRefetchInterval,
} from "./utils";

const ANON_USER_ID = "anon";

type TokenGetter = () => Promise<string | null>;

// ── queryFn factories (module-level — H-2 우회 패턴) ────────────────────

function makeListFetcher(getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return listLiveSessions(token);
  };
}

function makeStateFetcher(sessionId: string, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return getLiveSessionState(sessionId, token);
  };
}

function makeEventsFetcher(sessionId: string, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return listLiveSessionEvents(sessionId, token);
  };
}

// ── Hooks ──────────────────────────────────────────────────────────────

export function useLiveSessions(): UseQueryResult<
  { items: LiveSession[]; total: number },
  Error
> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: liveSessionKeys.list(uid),
    queryFn: makeListFetcher(getToken),
    refetchInterval: (q) =>
      q.state.status === "error" ? false : LIVE_SESSION_LIST_REFETCH_MS,
  });
}

export function useLiveSessionState(
  sessionId: string | null,
  isActive: boolean,
): UseQueryResult<LiveSignalState | null, Error> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: liveSessionKeys.state(uid, sessionId ?? ""),
    queryFn: makeStateFetcher(sessionId ?? "", getToken),
    enabled: Boolean(sessionId),
    refetchInterval: (q) => {
      if (q.state.status === "error") return false;
      return computeLiveSessionStateRefetchInterval(isActive);
    },
  });
}

export interface LiveSessionsAggregate {
  /** 활성 세션들의 합산 실현 손익 (point-in-time). */
  totalRealizedPnl: number;
  /** 합산 종료 거래 수. */
  totalClosedTrades: number;
  /** 세션별 누적 실현-PnL 곡선을 병합한 포트폴리오 곡선 (epoch seconds). */
  mergedEquityCurve: CurvePoint[];
  /** state 가 채워진(evaluate 된) 세션 수. */
  populatedSessions: number;
  /** 하나라도 로딩 중이면 true. */
  isLoading: boolean;
}

/**
 * 여러 라이브 세션의 state 를 useQueries 로 팬아웃 fetch 후 합산 집계.
 * 세션당 useLiveSessionState 와 동일 queryKey → 캐시 공유(추가 네트워크 최소).
 * MAX_LIVE_SESSIONS_PER_USER(=5) 상한이라 N+1 팬아웃 비용 제한적.
 */
export function useLiveSessionsAggregate(
  sessions: readonly LiveSession[],
): LiveSessionsAggregate {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const results = useQueries({
    queries: sessions.map((s) => ({
      queryKey: liveSessionKeys.state(uid, s.id),
      queryFn: makeStateFetcher(s.id, getToken),
      enabled: Boolean(s.id),
      refetchInterval: computeLiveSessionStateRefetchInterval(s.is_active),
    })),
  });

  let totalRealizedPnl = 0;
  let totalClosedTrades = 0;
  let populatedSessions = 0;
  const curves: CurvePoint[][] = [];

  for (const r of results) {
    const state = r.data;
    if (!state) continue;
    populatedSessions += 1;
    const pnl = Number(state.total_realized_pnl);
    if (Number.isFinite(pnl)) totalRealizedPnl += pnl;
    totalClosedTrades += state.total_closed_trades ?? 0;
    if (state.equity_curve && state.equity_curve.length > 0) {
      curves.push(
        state.equity_curve
          .map((p) => ({
            time: Math.floor(p.timestamp_ms / 1000),
            value: Number(p.cumulative_pnl),
          }))
          .filter((p) => Number.isFinite(p.value)),
      );
    }
  }

  return {
    totalRealizedPnl,
    totalClosedTrades,
    mergedEquityCurve: mergeCumulativeCurves(curves),
    populatedSessions,
    isLoading: results.some((r) => r.isLoading),
  };
}

export function useLiveSessionEvents(
  sessionId: string | null,
): UseQueryResult<{ items: LiveSignalEvent[] }, Error> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: liveSessionKeys.events(uid, sessionId ?? ""),
    queryFn: makeEventsFetcher(sessionId ?? "", getToken),
    enabled: Boolean(sessionId),
    refetchInterval: (q) =>
      q.state.status === "error" ? false : LIVE_SESSION_LIST_REFETCH_MS,
  });
}

export function useRegisterLiveSession(): UseMutationResult<
  LiveSession,
  Error,
  RegisterLiveSessionRequest
> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (req: RegisterLiveSessionRequest) => {
      const token = await getToken();
      return registerLiveSession(req, token);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: liveSessionKeys.list(uid) });
    },
  });
}

export function useDeactivateLiveSession(): UseMutationResult<
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
      return deactivateLiveSession(id, token);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: liveSessionKeys.list(uid) });
    },
  });
}
