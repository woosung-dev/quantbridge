"use client";

// RealtimeBridge가 인증 직후 연결을 시작하고 unmount에 클라이언트를 정리하는지 검증한다.
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { liveSessionKeys } from "@/features/live-sessions/query-keys";
import { tradingKeys } from "@/features/trading/query-keys";
import { clearAuthTokenCache } from "@/lib/auth-client";
import type { RealtimeClient, RealtimeWsClientOptions } from "./ws-client";

import { RealtimeBridge, realtimeWsUrl } from "./realtime-bridge";

afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
});

describe("RealtimeBridge", () => {
  it("origin의 끝 슬래시와 무관하게 서버 WebSocket 경로를 결합한다", () => {
    expect(realtimeWsUrl("ws://test/")).toBe("ws://test/api/v1/realtime/ws");
  });

  it("렌더 시 연결을 시작하고 unmount 시 destroy한다", () => {
    vi.stubEnv("NEXT_PUBLIC_WS_URL", "ws://test");
    const client: RealtimeClient = {
      ensureConnected: vi.fn(),
      getReconnectCount: () => 0,
      destroy: vi.fn(),
    };
    const clientFactory = vi.fn((_options: RealtimeWsClientOptions) => client);
    const queryClient = new QueryClient();
    const view = render(
      <QueryClientProvider client={queryClient}>
        <RealtimeBridge clientFactory={clientFactory} />
      </QueryClientProvider>,
    );

    expect(clientFactory).toHaveBeenCalledWith(
      expect.objectContaining({ url: "ws://test/api/v1/realtime/ws" }),
    );
    expect(client.ensureConnected).toHaveBeenCalledOnce();
    view.unmount();
    expect(client.destroy).toHaveBeenCalledOnce();
  });

  it("4401 의 onAuthFailure 를 토큰 캐시 무효화에 배선한다 (BL-844)", () => {
    vi.stubEnv("NEXT_PUBLIC_WS_URL", "ws://test");
    const client: RealtimeClient = {
      ensureConnected: vi.fn(),
      getReconnectCount: () => 0,
      destroy: vi.fn(),
    };
    const optionsRef: { current: RealtimeWsClientOptions | null } = { current: null };
    const clientFactory = vi.fn((nextOptions: RealtimeWsClientOptions) => {
      optionsRef.current = nextOptions;
      return client;
    });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <RealtimeBridge clientFactory={clientFactory} />
      </QueryClientProvider>,
    );

    optionsRef.current?.onAuthFailure?.();
    expect(clearAuthTokenCache).toHaveBeenCalledOnce();
  });

  it("authed 재진입 시 트레이딩·세션 전체 키를 무효화한다", () => {
    vi.stubEnv("NEXT_PUBLIC_WS_URL", "ws://test");
    const client: RealtimeClient = {
      ensureConnected: vi.fn(),
      getReconnectCount: () => 1,
      destroy: vi.fn(),
    };
    const optionsRef: { current: RealtimeWsClientOptions | null } = {
      current: null,
    };
    const clientFactory = vi.fn((nextOptions: RealtimeWsClientOptions) => {
      optionsRef.current = nextOptions;
      return client;
    });
    const queryClient = new QueryClient();
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    render(
      <QueryClientProvider client={queryClient}>
        <RealtimeBridge clientFactory={clientFactory} />
      </QueryClientProvider>,
    );

    optionsRef.current?.onStatusChange("authed");
    expect(invalidateQueries).not.toHaveBeenCalled();
    optionsRef.current?.onStatusChange("closed");
    optionsRef.current?.onStatusChange("authed");

    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: tradingKeys.all("user-1"),
    });
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: liveSessionKeys.all("user-1"),
    });
  });
});
