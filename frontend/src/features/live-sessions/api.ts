// Sprint 26 — Live Sessions API client (apiFetch + Clerk JWT).
// 토큰 주입은 hooks.ts 가 `useAuth().getToken()` 호출 — 본 모듈은 pure.

import { apiFetch } from "@/lib/api-client";

import {
  LiveSessionListResponseSchema,
  LiveSessionSchema,
  LiveSignalEventListResponseSchema,
  LiveSignalStateSchema,
  type LiveSession,
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

export async function deactivateLiveSession(
  id: string,
  token: string | null,
): Promise<void> {
  await apiFetch<void>(`${LIVE_SESSIONS_PATH}/${id}`, {
    method: "DELETE",
    token,
  });
}

export async function getLiveSessionState(
  sessionId: string,
  token: string | null,
): Promise<LiveSignalState | null> {
  // BE 응답이 비어있을 수 있음 (아직 1번도 evaluate 안된 session). 404 → null.
  try {
    const raw = await apiFetch<unknown>(
      `${LIVE_SESSIONS_PATH}/${sessionId}/state`,
      { method: "GET", token },
    );
    return LiveSignalStateSchema.parse(raw);
  } catch (err) {
    // apiFetch 가 status >= 400 throw — 404 는 null 반환
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
  const raw = await apiFetch<unknown>(
    `${LIVE_SESSIONS_PATH}/${sessionId}/events`,
    { method: "GET", token },
  );
  return LiveSignalEventListResponseSchema.parse(raw);
}
