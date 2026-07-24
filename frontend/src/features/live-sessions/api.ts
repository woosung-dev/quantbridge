// Sprint 26 — Live Sessions API client (apiFetch + Clerk JWT).
// 토큰 주입은 hooks.ts 가 `useAuth().getToken()` 호출 — 본 모듈은 pure.

import { apiFetch } from "@/lib/api-client";

import {
  LiveSessionListResponseSchema,
  LiveSessionPositionsResponseSchema,
  LiveSessionSchema,
  LiveSignalEventListResponseSchema,
  LiveSignalStateSchema,
  type LiveSession,
  type LiveSessionPositions,
  type LiveSignalEvent,
  type LiveSignalState,
  type RegisterLiveSessionRequest,
} from "./schemas";

const LIVE_SESSIONS_PATH = "/api/v1/live-sessions";

export async function listLiveSessions(
  token: string | null,
): Promise<{ items: LiveSession[]; total: number }> {
  const raw = await apiFetch<unknown>(LIVE_SESSIONS_PATH, {
    method: "GET",
    token,
  });
  return LiveSessionListResponseSchema.parse(raw);
}

export async function registerLiveSession(
  req: RegisterLiveSessionRequest,
  token: string | null,
): Promise<LiveSession> {
  const raw = await apiFetch<unknown>(LIVE_SESSIONS_PATH, {
    method: "POST",
    token,
    body: req,
  });
  return LiveSessionSchema.parse(raw);
}

export async function deactivateLiveSession(id: string, token: string | null): Promise<void> {
  await apiFetch<void>(`${LIVE_SESSIONS_PATH}/${id}`, {
    method: "DELETE",
    token,
  });
}

export async function getLiveSessionState(
  sessionId: string,
  token: string | null,
): Promise<LiveSignalState | null> {
  try {
    const raw = await apiFetch<unknown>(`${LIVE_SESSIONS_PATH}/${sessionId}/state`, {
      method: "GET",
      token,
    });
    const parsed = LiveSignalStateSchema.parse(raw);
    return parsed.evaluated ? parsed : null;
  } catch (err) {
    // 세션 삭제 직후 폴링 race에서는 apiFetch의 404를 null로 흡수한다.
    if (err instanceof Error && /\b404\b/.test(err.message)) {
      return null;
    }
    throw err;
  }
}

export async function listLiveSessionEvents(
  sessionId: string,
  token: string | null,
): Promise<{ items: LiveSignalEvent[] }> {
  const raw = await apiFetch<unknown>(`${LIVE_SESSIONS_PATH}/${sessionId}/events`, {
    method: "GET",
    token,
  });
  return LiveSignalEventListResponseSchema.parse(raw);
}

export async function getLiveSessionPositions(
  sessionId: string,
  token: string | null,
): Promise<LiveSessionPositions> {
  const raw = await apiFetch<unknown>(`${LIVE_SESSIONS_PATH}/${sessionId}/positions`, {
    method: "GET",
    token,
  });
  return LiveSessionPositionsResponseSchema.parse(raw);
}
