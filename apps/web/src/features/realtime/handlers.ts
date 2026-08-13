// 실시간 이벤트를 React Query 무효화 힌트로만 변환하는 핸들러.
import type { QueryClient } from "@tanstack/react-query";

import { liveSessionKeys } from "@/features/live-sessions/query-keys";
import { tradingKeys } from "@/features/trading/query-keys";

import type { RealtimeEnvelope } from "./schemas";
import { useRealtimeStore } from "./store";

export function handleRealtimeEvent(
  queryClient: QueryClient,
  userId: string,
  envelope: RealtimeEnvelope,
): void {
  switch (envelope.type) {
    case "order_update":
      void queryClient.invalidateQueries({
        queryKey: tradingKeys.ordersPrefix(userId),
      });
      return;
    case "kill_switch":
    case "kill_switch_resolved":
      void queryClient.invalidateQueries({
        queryKey: tradingKeys.killSwitch(userId),
      });
      return;
    case "session_state":
      void queryClient.invalidateQueries({
        queryKey: liveSessionKeys.state(userId, envelope.payload.session_id),
      });
      void queryClient.invalidateQueries({
        queryKey: liveSessionKeys.list(userId),
      });
      return;
    case "position_update":
      void queryClient.invalidateQueries({
        queryKey: liveSessionKeys.positionsPrefix(userId),
      });
      return;
    case "ticker":
      // ticker는 RQ 서버 스냅샷이 아닌 WS push cache만 갱신한다.
      useRealtimeStore.getState().applyTicker(envelope.payload.symbol, {
        markPrice: envelope.payload.mark_price,
        lastPrice: envelope.payload.last_price ?? null,
        ts: envelope.ts,
      });
      return;
  }
}
