// 인증된 실시간 이벤트 연결의 재연결·heartbeat 수명을 관리하는 프레임워크 무관 클라이언트.
import { parseRealtimeEnvelope, type RealtimeEnvelope } from "@/features/realtime/schemas";

export type WsStatus = "idle" | "connecting" | "authed" | "closed";

export interface WebSocketLike {
  readyState: number;
  onopen: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent) => void) | null;
  onclose: ((event: CloseEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  send(data: string): void;
  close(code?: number): void;
}

export type WebSocketFactory = (url: string) => WebSocketLike;

export interface RealtimeWsClientOptions {
  url: string;
  getToken: () => Promise<string | null>;
  onEvent: (envelope: RealtimeEnvelope) => void;
  onStatusChange: (status: WsStatus) => void;
  webSocketFactory?: WebSocketFactory;
  random?: () => number;
  heartbeatMs?: number;
}

export interface RealtimeClient {
  ensureConnected(): void;
  getReconnectCount(): number;
  destroy(): void;
}

const INITIAL_RECONNECT_DELAY_MS = 1_000;
const MAX_RECONNECT_DELAY_MS = 30_000;
const DEFAULT_HEARTBEAT_MS = 30_000;
const AUTH_FAILED_CLOSE_CODE = 4401;
const OPEN_READY_STATE = 1;

export function reconnectDelayMs(attempt: number, random: () => number = Math.random): number {
  const base = Math.min(
    INITIAL_RECONNECT_DELAY_MS * 2 ** Math.max(0, attempt - 1),
    MAX_RECONNECT_DELAY_MS,
  );
  return Math.round(base * (0.8 + random() * 0.4));
}

export class RealtimeWsClient implements RealtimeClient {
  private readonly createSocket: WebSocketFactory;
  private readonly random: () => number;
  private readonly heartbeatMs: number;
  private socket: WebSocketLike | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private status: WsStatus = "idle";
  private reconnectCount = 0;
  private authFailureRetries = 0;
  private destroyed = false;
  private stopped = false;

  constructor(private readonly options: RealtimeWsClientOptions) {
    this.createSocket = options.webSocketFactory ?? ((url) => new WebSocket(url));
    this.random = options.random ?? Math.random;
    this.heartbeatMs = options.heartbeatMs ?? DEFAULT_HEARTBEAT_MS;

    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", this.handleVisibilityChange);
    }
    if (typeof window !== "undefined") {
      window.addEventListener("online", this.handleOnline);
    }
  }

  ensureConnected(): void {
    if (this.destroyed || this.stopped || this.status === "connecting" || this.status === "authed") {
      return;
    }
    this.clearReconnectTimer();
    this.connect();
  }

  getReconnectCount(): number {
    return this.reconnectCount;
  }

  destroy(): void {
    if (this.destroyed) return;
    this.destroyed = true;
    this.clearReconnectTimer();
    this.stopHeartbeat();
    if (typeof document !== "undefined") {
      document.removeEventListener("visibilitychange", this.handleVisibilityChange);
    }
    if (typeof window !== "undefined") {
      window.removeEventListener("online", this.handleOnline);
    }

    const socket = this.socket;
    this.socket = null;
    if (socket) {
      socket.onopen = null;
      socket.onmessage = null;
      socket.onclose = null;
      socket.onerror = null;
      socket.close();
    }
    this.setStatus("closed");
  }

  private connect(): void {
    this.setStatus("connecting");
    const socket = this.createSocket(this.options.url);
    this.socket = socket;
    socket.onopen = () => {
      void this.authenticate(socket);
    };
    socket.onmessage = (event) => {
      if (isReadyMessage(event.data)) {
        this.handleReady();
        return;
      }
      const parsed = parseRealtimeEnvelope(event.data);
      if (parsed) this.options.onEvent(parsed);
    };
    socket.onclose = (event) => {
      if (socket !== this.socket || this.destroyed) return;
      this.socket = null;
      this.stopHeartbeat();
      this.scheduleReconnect(event.code);
    };
    socket.onerror = () => {
      // close 이벤트가 재연결을 단일하게 소유한다.
    };
  }

  private async authenticate(socket: WebSocketLike): Promise<void> {
    try {
      const token = await this.options.getToken();
      if (socket !== this.socket || this.destroyed) return;
      if (!token) {
        socket.close(AUTH_FAILED_CLOSE_CODE);
        return;
      }
      socket.send(JSON.stringify({ type: "auth", token }));
    } catch {
      if (socket === this.socket && !this.destroyed) socket.close(AUTH_FAILED_CLOSE_CODE);
    }
  }

  private scheduleReconnect(closeCode: number): void {
    if (closeCode === AUTH_FAILED_CLOSE_CODE) {
      this.authFailureRetries += 1;
      if (this.authFailureRetries > 1) {
        this.stopped = true;
        this.setStatus("closed");
        return;
      }
    }

    this.reconnectCount += 1;
    this.setStatus("closed");
    const delay = reconnectDelayMs(this.reconnectCount, this.random);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.ensureConnected();
    }, delay);
  }

  private handleReady = (): void => {
    this.authFailureRetries = 0;
    this.reconnectCount = 0;
    this.setStatus("authed");
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.socket?.readyState === OPEN_READY_STATE) this.socket.send("ping");
    }, this.heartbeatMs);
  };

  private handleVisibilityChange = (): void => {
    if (document.visibilityState === "visible") this.ensureConnected();
  };

  private handleOnline = (): void => {
    this.ensureConnected();
  };

  private stopHeartbeat(): void {
    if (this.heartbeatTimer !== null) clearInterval(this.heartbeatTimer);
    this.heartbeatTimer = null;
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
  }

  private setStatus(status: WsStatus): void {
    if (this.status === status) return;
    this.status = status;
    this.options.onStatusChange(status);
  }
}

function isReadyMessage(value: string): boolean {
  try {
    return JSON.parse(value).type === "ready";
  } catch {
    return false;
  }
}

export function createRealtimeWsClient(options: RealtimeWsClientOptions): RealtimeWsClient {
  return new RealtimeWsClient(options);
}
