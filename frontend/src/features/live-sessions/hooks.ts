"use client";

// Sprint 26 — Live Sessions React Query hooks.
//
// LESSON-004 의무:
//  - H-1: useEffect dep array primitive only (`[data?.id, data?.is_active]`)
//  - H-2: queryFn = module-level factory 호출식 (`makeXxxFetcher(...)`),
//         queryKey factory userId 첫 인자.
// 폴링: state 는 active 시 5s / idle 시 30s, list 는 30s.

import {
  useQueries,
  useQuery,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import { useAuthCtx, type TokenGetter } from "@/hooks/use-auth-ctx";
import { useInvalidatingMutation } from "@/hooks/use-invalidating-mutation";
import { makeRefetchInterval, type RefetchIntervalFn } from "@/lib/query-poll";

import { mergeCumulativeCurves, type CurvePoint } from "./aggregate";
import {
  closePosition,
  deactivateLiveSession,
  getLiveSessionPositions,
  getLiveSessionState,
  listLiveSessionEvents,
  listLiveSessions,
  registerLiveSession,
} from "./api";
import { liveSessionKeys } from "./query-keys";
import type {
  ClosePositionResponse,
  LiveSession,
  LiveSessionPositions,
  ExchangePosition,
  LiveSignalEvent,
  LiveSignalState,
  RegisterLiveSessionRequest,
} from "./schemas";
import {
  LIVE_SESSION_LIST_REFETCH_MS,
  computeLiveSessionStateRefetchInterval,
} from "./utils";


// ── refetchInterval (module-level — LESSON-004 error→false 가드) ────────

const listRefetchInterval = makeRefetchInterval<{
  items: LiveSession[];
  total: number;
}>(() => LIVE_SESSION_LIST_REFETCH_MS);

const eventsRefetchInterval = makeRefetchInterval<{
  items: LiveSignalEvent[];
}>(() => LIVE_SESSION_LIST_REFETCH_MS);

const positionsRefetchInterval = makeRefetchInterval<LiveSessionPositions>(
  () => LIVE_SESSION_LIST_REFETCH_MS,
);

export interface LiveSessionPositionRow {
  sessionId: string;
  sessionLabel: string;
  symbol: string;
  verdict: LiveSessionPositions["diff"]["verdict"];
  position: ExchangePosition;
  fetchedAt: string | null;
}

export interface UnsupportedLiveSessionPosition {
  sessionId: string;
  sessionLabel: string;
  symbol: string;
  reason: string | null;
  fetchedAt: string | null;
}

/** 전략이 들고 있다고 보고한 미청산 거래. 백엔드가 느슨한 record 로 주므로 가드해서 읽는다. */
export interface LocalOpenTradeSummary {
  id: string | null;
  direction: string | null;
  qty: string | null;
}

/**
 * BL-480 — 거래소 포지션이 0인데 전략은 들고 있다고 보는 상태.
 *
 * 행(`rows`)은 거래소 포지션을 펼쳐서 만들기 때문에, `positions` 가 비어 있는 것이
 * 곧 정의인 `local_only` 는 **정확히 그 순간에만** 행이 하나도 안 만들어졌다.
 * 그래서 표가 "열린 포지션이 없습니다" 로 떨어지며 발산을 은폐했다.
 */
export interface LiveSessionPositionDivergence {
  sessionId: string;
  sessionLabel: string;
  symbol: string;
  verdict: LiveSessionPositions["diff"]["verdict"];
  localOpenTrades: LocalOpenTradeSummary[];
  fetchedAt: string | null;
}

export interface LiveSessionsPositionsAggregate {
  rows: LiveSessionPositionRow[];
  unsupported: UnsupportedLiveSessionPosition[];
  divergences: LiveSessionPositionDivergence[];
  latestFetchedAt: string | null;
  isLoading: boolean;
  isError: boolean;
  isPending: boolean;
  isEmpty: boolean;
  refetch: () => Promise<unknown[]>;
}

function readTradeField(trade: Record<string, unknown>, key: string): string | null {
  const raw = trade[key];
  if (typeof raw === "string") return raw;
  if (typeof raw === "number" && Number.isFinite(raw)) return String(raw);
  return null;
}

function summarizeLocalOpenTrades(
  snapshot: readonly Record<string, unknown>[] | undefined,
): LocalOpenTradeSummary[] {
  if (!snapshot) return [];
  return snapshot.map((trade) => ({
    id: readTradeField(trade, "id"),
    direction: readTradeField(trade, "direction"),
    qty: readTradeField(trade, "qty"),
  }));
}

/**
 * 세션 state 폴링 간격 — active 여부에 따라 5s/30s, error 시 중단.
 * useLiveSessionState(단건)와 useLiveSessionsAggregate(팬아웃) 공용.
 * (기존 aggregate 는 상수 interval 을 그대로 넘겨 error 가드가 빠져 있었다 — LESSON-004 위반 수정.)
 */
export function liveStateRefetchInterval(
  isActive: boolean,
): RefetchIntervalFn<LiveSignalState | null> {
  return makeRefetchInterval(() =>
    computeLiveSessionStateRefetchInterval(isActive),
  );
}

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

function makePositionsFetcher(sessionId: string, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return getLiveSessionPositions(sessionId, token);
  };
}

/** 활성 세션별 거래소 포지션을 행으로 펼친다. 같은 계정·심볼도 세션 단위로 보존한다. */
export function combineLiveSessionPositions(
  sessions: readonly Pick<LiveSession, "id" | "strategy_id">[],
  results: readonly UseQueryResult<LiveSessionPositions, Error>[],
): LiveSessionsPositionsAggregate {
  const rows: LiveSessionPositionRow[] = [];
  const unsupported: UnsupportedLiveSessionPosition[] = [];
  const divergences: LiveSessionPositionDivergence[] = [];
  let latestFetchedAt: string | null = null;

  for (const [index, result] of results.entries()) {
    const session = sessions[index];
    const positions = result.data;
    if (!session || !positions) continue;
    if (positions.fetched_at && (!latestFetchedAt || positions.fetched_at > latestFetchedAt)) {
      latestFetchedAt = positions.fetched_at;
    }
    const sessionLabel = session.strategy_id.slice(0, 8);
    if (!positions.supported) {
      unsupported.push({
        sessionId: session.id,
        sessionLabel,
        symbol: positions.symbol,
        reason: positions.reason,
        fetchedAt: positions.fetched_at,
      });
      continue;
    }
    // BL-480 — 거래소 포지션이 0이면 행이 만들어지지 않는다. 그런데 그게 곧
    // `local_only` 의 정의라, 발산을 뜻하는 판정이 하필 그때만 화면에서 사라졌다.
    // 여기서 세션 단위로 건져 올린다.
    if (positions.positions.length === 0) {
      if (isDivergentWithoutExchangePosition(positions.diff)) {
        divergences.push({
          sessionId: session.id,
          sessionLabel,
          symbol: positions.symbol,
          verdict: positions.diff.verdict,
          localOpenTrades: summarizeLocalOpenTrades(positions.local_open_trades_snapshot),
          fetchedAt: positions.fetched_at,
        });
      }
      continue;
    }
    for (const position of positions.positions) {
      rows.push({
        sessionId: session.id,
        sessionLabel,
        symbol: positions.symbol,
        verdict: positions.diff.verdict,
        position,
        fetchedAt: positions.fetched_at,
      });
    }
  }

  return {
    rows,
    unsupported,
    divergences,
    latestFetchedAt,
    isLoading: results.some((result) => result.isLoading),
    isError: results.some((result) => result.isError),
    isPending: results.some((result) => result.isPending),
    isEmpty:
      results.length === 0 ||
      (rows.length === 0 && unsupported.length === 0 && divergences.length === 0),
    refetch: () => Promise.all(results.map((result) => result.refetch())),
  };
}

/**
 * 거래소 포지션이 0인 상태에서 "숨기면 안 되는" 판정만 고른다.
 *
 * - `local_only` — 전략은 들고 있다고 보는데 거래소는 비었다. 발산 그 자체.
 * - `unknown` + 전략 상태 있음 — 상태 보고는 있는데 대조에 실패했다는 뜻이라 알아야 한다.
 * - `unknown` + 전략 상태 없음(`none`) — 아직 평가 전. 숨길 것이 없으므로 조용히 둔다.
 * - `match` — 양쪽 다 비었다. 정상.
 *
 * `exchange_only` 는 정의상 거래소 포지션이 있어야 하므로 이 분기에 도달하지 않는다.
 */
function isDivergentWithoutExchangePosition(diff: LiveSessionPositions["diff"]): boolean {
  if (diff.verdict === "local_only") return true;
  return diff.verdict === "unknown" && diff.local_source === "strategy_state_report";
}

// ── Hooks ──────────────────────────────────────────────────────────────

export function useLiveSessions(): UseQueryResult<
  { items: LiveSession[]; total: number },
  Error
> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: liveSessionKeys.list(uid),
    queryFn: makeListFetcher(getToken),
    refetchInterval: listRefetchInterval,
  });
}

export function useLiveSessionState(
  sessionId: string | null,
  isActive: boolean,
): UseQueryResult<LiveSignalState | null, Error> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: liveSessionKeys.state(uid, sessionId ?? ""),
    queryFn: makeStateFetcher(sessionId ?? "", getToken),
    enabled: Boolean(sessionId),
    refetchInterval: liveStateRefetchInterval(isActive),
  });
}

export interface LiveSessionsAggregate {
  /** 활성 세션들의 합산 실현 손익 (point-in-time). */
  totalRealizedPnl: number;
  /** 합산 종료 거래 수. */
  totalClosedTrades: number;
  /**
   * BL-458 — 합산 손익 중 거래소가 확정한 몫. `null` = 채워진 세션 중 하나라도
   * 소계를 보고하지 않아 분할을 신뢰할 수 없다는 뜻이다. **0 과 구분해야 한다.**
   */
  confirmedRealizedPnl: number | null;
  /** 합산 손익 중 pine_v2 추정 몫. `null` 의 의미는 위와 같다. */
  estimatedRealizedPnl: number | null;
  /** 세션별 누적 실현-PnL 곡선을 병합한 포트폴리오 곡선 (epoch seconds). */
  mergedEquityCurve: CurvePoint[];
  /** state 가 채워진(evaluate 된) 세션 수. */
  populatedSessions: number;
  /** 하나라도 로딩 중이면 true. */
  isLoading: boolean;
  /** 하나라도 state 조회에 실패하면 true — 합산 손익이 불완전하다는 신호. */
  isError: boolean;
  /** 하나라도 첫 응답을 아직 못 받았으면 true. */
  isPending: boolean;
}

/**
 * useQueries combine — 팬아웃 결과를 렌더 바디 밖에서 합산 집계 (module-level).
 * 렌더 바디에서 mergeCumulativeCurves 직행 호출은 매 렌더 새 identity 를 반환해
 * 하위 차트의 data effect(setData + fitContent)를 폴링마다 재실행시켰다(줌 리셋).
 * combine 결과는 RQ 가 structural sharing(replaceEqualDeep) 으로 memoize 하므로
 * 데이터 불변 시 mergedEquityCurve 등 하위 참조 identity 가 유지된다.
 * (단순 useMemo([results]) 는 useQueries 가 매 렌더 새 배열이라 불충분.)
 */
function combineLiveSessionStates(
  results: UseQueryResult<LiveSignalState | null, Error>[],
): LiveSessionsAggregate {
  let totalRealizedPnl = 0;
  let totalClosedTrades = 0;
  let populatedSessions = 0;
  const curves: CurvePoint[][] = [];
  // BL-458 — 출처 소계는 **모든** 채워진 세션이 보고했을 때만 합산한다. 부분 분할은
  // 없는 것보다 나쁘다("확정 −2" 가 실제로는 세션 하나만의 확정일 수 있다).
  let confirmedRealizedPnl = 0;
  let estimatedRealizedPnl = 0;
  let splitReportedSessions = 0;

  for (const r of results) {
    const state = r.data;
    if (!state) continue;
    populatedSessions += 1;
    const pnl = Number(state.total_realized_pnl);
    if (Number.isFinite(pnl)) totalRealizedPnl += pnl;
    totalClosedTrades += state.total_closed_trades ?? 0;
    const confirmed = Number(state.confirmed_realized_pnl);
    const estimated = Number(state.estimated_realized_pnl);
    if (
      state.confirmed_realized_pnl !== undefined &&
      state.estimated_realized_pnl !== undefined &&
      Number.isFinite(confirmed) &&
      Number.isFinite(estimated)
    ) {
      confirmedRealizedPnl += confirmed;
      estimatedRealizedPnl += estimated;
      splitReportedSessions += 1;
    }
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

  const splitComplete =
    populatedSessions > 0 && splitReportedSessions === populatedSessions;

  return {
    totalRealizedPnl,
    totalClosedTrades,
    // 하나라도 소계를 안 보고했으면 null — 반쪽 분할을 그리지 않는다.
    confirmedRealizedPnl: splitComplete ? confirmedRealizedPnl : null,
    estimatedRealizedPnl: splitComplete ? estimatedRealizedPnl : null,
    mergedEquityCurve: mergeCumulativeCurves(curves),
    populatedSessions,
    isLoading: results.some((r) => r.isLoading),
    // 합산은 모든 세션 state 를 더한 값이라, 하나라도 실패/미수신이면 손익이 불완전하다.
    // 소비처(대시보드 kpi-pnl)가 성공-0 과 구분해 "확인 불가"/"불러오는 중"으로 표기한다.
    isError: results.some((r) => r.isError),
    isPending: results.some((r) => r.isPending),
  };
}

/**
 * 여러 라이브 세션의 state 를 useQueries 로 팬아웃 fetch 후 합산 집계.
 * 세션당 useLiveSessionState 와 동일 queryKey → 캐시 공유(추가 네트워크 최소).
 * MAX_LIVE_SESSIONS_PER_USER(=5) 상한이라 N+1 팬아웃 비용 제한적.
 * 집계는 combine 옵션 (combineLiveSessionStates) — 반환 identity 안정화.
 */
export function useLiveSessionsAggregate(
  sessions: readonly LiveSession[],
): LiveSessionsAggregate {
  const { uid, getToken } = useAuthCtx();
  return useQueries({
    queries: sessions.map((s) => ({
      queryKey: liveSessionKeys.state(uid, s.id),
      queryFn: makeStateFetcher(s.id, getToken),
      enabled: Boolean(s.id),
      refetchInterval: liveStateRefetchInterval(s.is_active),
    })),
    combine: combineLiveSessionStates,
  });
}

export function useLiveSessionEvents(
  sessionId: string | null,
): UseQueryResult<{ items: LiveSignalEvent[] }, Error> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: liveSessionKeys.events(uid, sessionId ?? ""),
    queryFn: makeEventsFetcher(sessionId ?? "", getToken),
    enabled: Boolean(sessionId),
    refetchInterval: eventsRefetchInterval,
  });
}

export function useLiveSessionPositions(
  sessionId: string | null,
): UseQueryResult<LiveSessionPositions, Error> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: liveSessionKeys.positions(uid, sessionId ?? ""),
    queryFn: makePositionsFetcher(sessionId ?? "", getToken),
    enabled: Boolean(sessionId),
    refetchInterval: positionsRefetchInterval,
  });
}

/** 활성 세션의 포지션 대조를 같은 query cache에서 팬아웃해 세션별 행으로 합친다. */
export function useLiveSessionsPositions(
  sessions: readonly LiveSession[],
): LiveSessionsPositionsAggregate {
  const { uid, getToken } = useAuthCtx();
  return useQueries({
    queries: sessions.map((session) => ({
      queryKey: liveSessionKeys.positions(uid, session.id),
      queryFn: makePositionsFetcher(session.id, getToken),
      enabled: Boolean(session.id),
      refetchInterval: positionsRefetchInterval,
    })),
    combine: (results) => combineLiveSessionPositions(sessions, results),
  });
}

export function useRegisterLiveSession(): UseMutationResult<
  LiveSession,
  Error,
  RegisterLiveSessionRequest
> {
  return useInvalidatingMutation({
    mutationFn: (req: RegisterLiveSessionRequest, token) =>
      registerLiveSession(req, token),
    invalidateKeys: (uid) => [liveSessionKeys.list(uid)],
  });
}

export function useDeactivateLiveSession(): UseMutationResult<
  void,
  Error,
  string
> {
  return useInvalidatingMutation({
    mutationFn: (id: string, token) => deactivateLiveSession(id, token),
    invalidateKeys: (uid) => [liveSessionKeys.list(uid)],
  });
}

export interface ClosePositionVariables {
  sessionId: string;
  symbol: string;
}

export function useClosePosition(): UseMutationResult<
  ClosePositionResponse,
  Error,
  ClosePositionVariables
> {
  return useInvalidatingMutation({
    mutationFn: ({ sessionId }, token) => closePosition(sessionId, token),
    invalidateKeys: (uid) => [liveSessionKeys.positionsPrefix(uid)],
  });
}
