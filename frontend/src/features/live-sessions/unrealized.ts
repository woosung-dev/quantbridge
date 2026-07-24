// 활성 라이브 세션의 WS 마크가격 기반 미실현 손익 추정치를 계산한다.
import { useMemo } from "react";
import { useQueries, type UseQueryResult } from "@tanstack/react-query";
import { useShallow } from "zustand/shallow";
import { z } from "zod/v4";

import { toBybitTickerSymbol } from "@/features/realtime/symbols";
import { useRealtimeStore, type TickerEntry } from "@/features/realtime/store";
import { useAuthCtx, type TokenGetter } from "@/hooks/use-auth-ctx";

import { getLiveSessionState } from "./api";
import { liveSessionKeys } from "./query-keys";
import type { LiveSession, LiveSignalState } from "./schemas";
import { liveStateRefetchInterval } from "./hooks";

export const OpenTradeSchema = z.object({
  direction: z.enum(["long", "short"]),
  qty: z.number(),
  entry_price: z.number(),
});
export type OpenTrade = z.infer<typeof OpenTradeSchema>;

function makeStateFetcher(sessionId: string, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return getLiveSessionState(sessionId, token);
  };
}

function parseOpenTrades(state: LiveSignalState | null | undefined): OpenTrade[] | null {
  const result = z.array(OpenTradeSchema).safeParse(
    state?.last_strategy_state_report.open_trades,
  );
  return result.success ? result.data : null;
}

export function computeUnrealizedPnl(
  trades: readonly OpenTrade[],
  markPrice: string,
): number | null {
  if (markPrice.trim() === "") return null;
  const mark = Number(markPrice);
  if (!Number.isFinite(mark)) return null;

  const parsedTrades = z.array(OpenTradeSchema).safeParse(trades);
  if (!parsedTrades.success) return null;

  let total = 0;
  for (const trade of parsedTrades.data) {
    if (
      !Number.isFinite(trade.qty) ||
      !Number.isFinite(trade.entry_price)
    ) {
      return null;
    }
    total += (mark - trade.entry_price) * trade.qty * (trade.direction === "long" ? 1 : -1);
  }
  return total;
}

export interface UnrealizedPnlEstimate {
  total: number | null;
  /** 하나라도 ticker를 아직 받지 못한 활성 세션이 있으면 true. */
  isEstimating: boolean;
  /** 활성 세션 ticker 중 가장 최근 서버 epoch-ms 시각. */
  latestTs: number | null;
}

function deriveUnrealizedPnl(
  activeSessions: readonly LiveSession[],
  states: readonly (LiveSignalState | null | undefined)[],
  tickerBySessionId: Readonly<Record<string, TickerEntry | undefined>>,
): UnrealizedPnlEstimate {
  if (activeSessions.length === 0) {
    return { total: 0, isEstimating: false, latestTs: null };
  }

  let total = 0;
  let isEstimating = false;
  let latestTs: number | null = null;

  for (let index = 0; index < activeSessions.length; index += 1) {
    const session = activeSessions[index]!;
    const ticker = tickerBySessionId[session.id];
    if (!ticker) {
      isEstimating = true;
      continue;
    }
    latestTs = latestTs === null ? ticker.ts : Math.max(latestTs, ticker.ts);

    const trades = parseOpenTrades(states[index]);
    if (trades === null) return { total: null, isEstimating, latestTs };
    const pnl = computeUnrealizedPnl(trades, ticker.markPrice);
    if (pnl === null) return { total: null, isEstimating, latestTs };
    total += pnl;
  }

  return isEstimating ? { total: null, isEstimating, latestTs } : { total, isEstimating, latestTs };
}

function combineStates(
  results: UseQueryResult<LiveSignalState | null, Error>[],
): readonly (LiveSignalState | null | undefined)[] {
  return results.map((result) => result.data);
}

/**
 * 기존 useLiveSessionsAggregate와 같은 state queryKey·polling 계약을 재사용한다.
 * 새로운 endpoint나 별도 polling source는 만들지 않고 React Query cache를 공유한다.
 */
export function useUnrealizedPnlEstimate(
  activeSessions: readonly LiveSession[],
): UnrealizedPnlEstimate {
  const { uid, getToken } = useAuthCtx();
  const states = useQueries({
    queries: activeSessions.map((session) => ({
      queryKey: liveSessionKeys.state(uid, session.id),
      queryFn: makeStateFetcher(session.id, getToken),
      enabled: Boolean(session.id),
      refetchInterval: liveStateRefetchInterval(session.is_active),
    })),
    combine: combineStates,
  });

  // Selector의 object map은 집계 예외다. 다른 symbol update에는 선택한 entry 참조가 같아
  // useShallow가 이전 map identity를 유지한다 (store identity regression test로 고정).
  const tickerBySessionId = useRealtimeStore(
    useShallow((state) => {
      const selected: Record<string, TickerEntry | undefined> = {};
      for (const session of activeSessions) {
        selected[session.id] = state.tickers[toBybitTickerSymbol(session.symbol)];
      }
      return selected;
    }),
  );

  return useMemo(
    () => deriveUnrealizedPnl(activeSessions, states, tickerBySessionId),
    [activeSessions, states, tickerBySessionId],
  );
}
