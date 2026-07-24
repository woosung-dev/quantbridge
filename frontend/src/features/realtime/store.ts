"use client";

// 실시간 연결 진단 scalar와 WS push ticker 캐시를 보관하는 Zustand store.
//
// Selector 계약 (LESSON-004):
// - 반드시 scalar selector (`useRealtimeStore(s => s.status)`) 로만 구독한다.
// - 단일 심볼 ticker 소비는 string scalar selector (`s.tickers[symbol]?.markPrice ?? null`)를 쓴다.
// - 집계만 `useShallow` map selector를 쓴다. 서로 다른 심볼 갱신 때 선택 entry 참조는 불변이다.
// - RQ 폴링 데이터는 RQ 소유 / WS push 스트림 캐시(tickers)는 본 store 소유.
//   CLAUDE.md의 "실시간 데이터는 WS+Zustand" 규칙 첫 구현체다.
import { create } from "zustand";

import type { WsStatus } from "@/lib/ws-client";

export interface RealtimeState {
  status: WsStatus;
  lastEventTs: number | null;
  reconnectCount: number;
  tickers: Record<string, TickerEntry>;
  setConnection: (status: WsStatus, reconnectCount: number) => void;
  recordEvent: (ts: number) => void;
  applyTicker: (symbol: string, entry: TickerEntry) => void;
  clearTickers: () => void;
  reset: () => void;
}

export interface TickerEntry {
  markPrice: string;
  lastPrice: string | null;
  /** 서버 realtime envelope의 epoch milliseconds. */
  ts: number;
}

export function createInitialRealtimeState(): Pick<
  RealtimeState,
  "status" | "lastEventTs" | "reconnectCount" | "tickers"
> {
  return { status: "idle", lastEventTs: null, reconnectCount: 0, tickers: {} };
}

export const useRealtimeStore = create<RealtimeState>()((set) => ({
  ...createInitialRealtimeState(),
  setConnection: (status, reconnectCount) => set({ status, reconnectCount }),
  recordEvent: (lastEventTs) => set({ lastEventTs }),
  applyTicker: (symbol, entry) =>
    set((state) => ({ tickers: { ...state.tickers, [symbol]: entry } })),
  clearTickers: () => set({ tickers: {} }),
  reset: () => set(createInitialRealtimeState()),
}));

export const selectRealtimeStatus = (state: RealtimeState): WsStatus => state.status;
export const selectLastRealtimeEventTs = (state: RealtimeState): number | null =>
  state.lastEventTs;
export const selectReconnectCount = (state: RealtimeState): number => state.reconnectCount;
