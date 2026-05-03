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
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

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
