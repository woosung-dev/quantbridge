"use client";

// 인증된 대시보드에서 실시간 연결을 시작하고 React Query 무효화만 수행하는 client leaf.
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { useAuthCtx } from "@/hooks/use-auth-ctx";
import { clearAuthTokenCache } from "@/lib/auth-client";
import {
  createRealtimeWsClient,
  type RealtimeClient,
  type RealtimeWsClientOptions,
} from "./ws-client";
import { liveSessionKeys } from "@/features/live-sessions/query-keys";
import { tradingKeys } from "@/features/trading/query-keys";

import { handleRealtimeEvent } from "./handlers";
import { useRealtimeStore } from "./store";

type RealtimeClientFactory = (options: RealtimeWsClientOptions) => RealtimeClient;

const defaultClientFactory: RealtimeClientFactory = createRealtimeWsClient;
export const REALTIME_WS_PATH = "/api/v1/realtime/ws";

export function realtimeWsUrl(origin: string): string {
  return `${origin.replace(/\/+$/, "")}${REALTIME_WS_PATH}`;
}

export function RealtimeBridge({
  clientFactory = defaultClientFactory,
}: {
  clientFactory?: RealtimeClientFactory;
}) {
  const { userId, isSignedIn, getToken } = useAuthCtx();
  const queryClient = useQueryClient();
  const getTokenRef = useRef(getToken);
  const queryClientRef = useRef(queryClient);
  const clientFactoryRef = useRef(clientFactory);
  const clientRef = useRef<RealtimeClient | null>(null);

  // H-1: 함수·객체는 effect dependency가 아니라 최신 ref로만 유지한다.
  useEffect(() => {
    getTokenRef.current = getToken;
    queryClientRef.current = queryClient;
    clientFactoryRef.current = clientFactory;
  });

  useEffect(() => {
    if (!isSignedIn || !userId) {
      useRealtimeStore.getState().reset();
      return;
    }

    const origin = process.env.NEXT_PUBLIC_WS_URL;
    if (!origin) return;

    let hasAuthedOnce = false;
    const client = clientFactoryRef.current({
      url: realtimeWsUrl(origin),
      getToken: () => getTokenRef.current(),
      onAuthFailure: clearAuthTokenCache,
      onEvent: (envelope) => {
        handleRealtimeEvent(queryClientRef.current, userId, envelope);
        useRealtimeStore.getState().recordEvent(envelope.ts);
      },
      onStatusChange: (status) => {
        useRealtimeStore
          .getState()
          .setConnection(status, clientRef.current?.getReconnectCount() ?? 0);
        if (status !== "authed") return;
        if (hasAuthedOnce) {
          void queryClientRef.current.invalidateQueries({
            queryKey: tradingKeys.all(userId),
          });
          void queryClientRef.current.invalidateQueries({
            queryKey: liveSessionKeys.all(userId),
          });
        }
        hasAuthedOnce = true;
      },
    });
    clientRef.current = client;
    client.ensureConnected();

    return () => {
      if (clientRef.current === client) clientRef.current = null;
      client.destroy();
    };
  }, [userId, isSignedIn]);

  return null;
}
