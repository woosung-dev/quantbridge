"use client";

// 실시간 연결 진단 scalar만 보관하는 Zustand store.
//
// Selector 계약 (LESSON-004):
// - 반드시 scalar selector (`useRealtimeStore(s => s.status)`) 로만 구독한다.
// - 서버 데이터는 React Query가 소유하며 여기에는 저장하지 않는다.
import { create } from "zustand";

import type { WsStatus } from "@/lib/ws-client";

export interface RealtimeState {
  status: WsStatus;
  lastEventTs: number | null;
  reconnectCount: number;
  setConnection: (status: WsStatus, reconnectCount: number) => void;
  recordEvent: (ts: number) => void;
  reset: () => void;
}

export function createInitialRealtimeState(): Pick<
  RealtimeState,
  "status" | "lastEventTs" | "reconnectCount"
> {
  return { status: "idle", lastEventTs: null, reconnectCount: 0 };
}

export const useRealtimeStore = create<RealtimeState>()((set) => ({
  ...createInitialRealtimeState(),
  setConnection: (status, reconnectCount) => set({ status, reconnectCount }),
  recordEvent: (lastEventTs) => set({ lastEventTs }),
  reset: () => set(createInitialRealtimeState()),
}));

export const selectRealtimeStatus = (state: RealtimeState): WsStatus => state.status;
export const selectLastRealtimeEventTs = (state: RealtimeState): number | null =>
  state.lastEventTs;
export const selectReconnectCount = (state: RealtimeState): number => state.reconnectCount;
