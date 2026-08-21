// 실시간 WebSocket 클라이언트의 인증·재연결 수명 계약을 검증한다.
import { afterEach, describe, expect, it, vi } from "vitest";

import { RealtimeWsClient, reconnectDelayMs, type WebSocketLike } from "./ws-client";

class FakeSocket implements WebSocketLike {
  readyState = 0;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  readonly sent: string[] = [];

  send(data: string): void {
    this.sent.push(data);
  }

  close(code = 1000): void {
    this.readyState = 3;
    this.onclose?.({ code } as CloseEvent);
  }

  open(): void {
    this.readyState = 1;
    this.onopen?.(new Event("open"));
  }

  receive(data: string): void {
    this.onmessage?.({ data } as MessageEvent<string>);
  }
}

function makeClient() {
  const sockets: FakeSocket[] = [];
  const statuses: string[] = [];
  const getToken = vi.fn().mockResolvedValue("fresh-token");
  const client = new RealtimeWsClient({
    url: "ws://test/realtime/ws",
    getToken,
    onEvent: vi.fn(),
    onStatusChange: (status) => statuses.push(status),
    webSocketFactory: () => {
      const socket = new FakeSocket();
      sockets.push(socket);
      return socket;
    },
    random: () => 0.5,
    heartbeatMs: 100,
  });
  return { client, sockets, statuses, getToken };
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("RealtimeWsClient", () => {
  it("첫 open 뒤 fresh token auth를 보내고 ready 뒤 heartbeat를 시작한다", async () => {
    vi.useFakeTimers();
    const { client, sockets, statuses } = makeClient();

    client.ensureConnected();
    sockets[0]?.open();
    await Promise.resolve();
    expect(sockets[0]?.sent).toEqual(['{"type":"auth","token":"fresh-token"}']);

    sockets[0]?.receive('{"type":"ready"}');
    vi.advanceTimersByTime(100);
    expect(statuses).toEqual(["connecting", "authed"]);
    expect(sockets[0]?.sent).toContain("ping");
    client.destroy();
  });

  it("실패마다 1→2→4초 backoff를 적용하고 30초에서 상한을 둔다", () => {
    vi.useFakeTimers();
    const { client, sockets } = makeClient();
    client.ensureConnected();

    sockets[0]?.close();
    vi.advanceTimersByTime(999);
    expect(sockets).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(sockets).toHaveLength(2);

    sockets[1]?.close();
    vi.advanceTimersByTime(1_999);
    expect(sockets).toHaveLength(2);
    vi.advanceTimersByTime(1);
    expect(sockets).toHaveLength(3);

    sockets[2]?.close();
    vi.advanceTimersByTime(4_000);
    expect(sockets).toHaveLength(4);
    expect(reconnectDelayMs(6, () => 0.5)).toBe(30_000);
    client.destroy();
  });

  it("4401은 fresh token으로 한 번만 재시도하고 이후 중단한다", async () => {
    vi.useFakeTimers();
    const { client, sockets, getToken } = makeClient();
    client.ensureConnected();
    sockets[0]?.open();
    await Promise.resolve();
    sockets[0]?.close(4401);
    vi.advanceTimersByTime(1_000);
    expect(sockets).toHaveLength(2);

    sockets[1]?.open();
    await Promise.resolve();
    expect(getToken).toHaveBeenCalledTimes(2);
    sockets[1]?.close(4401);
    vi.advanceTimersByTime(30_000);
    expect(sockets).toHaveLength(2);
    client.destroy();
  });

  it("visible 복귀는 대기 중인 재연결을 즉시 보장한다", () => {
    vi.useFakeTimers();
    const { client, sockets } = makeClient();
    client.ensureConnected();
    sockets[0]?.close();

    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });
    document.dispatchEvent(new Event("visibilitychange"));
    expect(sockets).toHaveLength(2);
    client.destroy();
  });

  it("online 이벤트는 대기 중인 재연결을 즉시 보장한다", () => {
    vi.useFakeTimers();
    const { client, sockets } = makeClient();
    client.ensureConnected();
    sockets[0]?.close();

    window.dispatchEvent(new Event("online"));
    expect(sockets).toHaveLength(2);
    client.destroy();
  });

  it("destroy 뒤 visibilitychange·online은 재연결을 만들지 않는다", () => {
    vi.useFakeTimers();
    const { client, sockets } = makeClient();
    client.ensureConnected();
    sockets[0]?.close();
    client.destroy();

    document.dispatchEvent(new Event("visibilitychange"));
    window.dispatchEvent(new Event("online"));
    vi.advanceTimersByTime(30_000);
    expect(sockets).toHaveLength(1);
  });
});
