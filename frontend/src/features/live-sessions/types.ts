// Sprint 26 — Live Signal Auto-Trading types.
// 모든 타입은 schemas.ts 에서 z.infer 로 추출 — 중복 선언 금지.

export type {
  LiveSession,
  LiveSessionForm,
  LiveSessionListResponse,
  LiveSignalEvent,
  LiveSignalEventListResponse,
  LiveSignalEventStatus,
  LiveSignalInterval,
  LiveSignalState,
  RegisterLiveSessionRequest,
} from "./schemas";

// PnL chart datapoint — utils.ts 에서 buildPnlSeries 가 생성.
export type EquityPoint = {
  timestamp: string; // ISO 8601 UTC
  cumulative_pnl: number;
};
