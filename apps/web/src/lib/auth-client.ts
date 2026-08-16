// Better Auth 브라우저 클라이언트 — 세션 훅과 로그인/가입/로그아웃 액션의 SSOT(ADR-034).
// ★토큰 캐시가 여기 있다. FastAPI 로 보내는 것은 세션 쿠키가 아니라 **JWT** 이고,
//   그 JWT 는 기본 15분짜리라 매 요청 발급하면 왕복이 두 배가 된다.
"use client";

import { createAuthClient } from "better-auth/react";

export const authClient = createAuthClient({
  // 브라우저↔Next 는 동일 오리진이므로 baseURL 을 지정하지 않는다(상대 경로 `/api/auth`).
});

export const { useSession, signIn, signUp, signOut, deleteUser } = authClient;

interface CachedToken {
  token: string;
  /** epoch ms. 이 시각 전에는 재사용한다. */
  expiresAt: number;
}

let cached: CachedToken | null = null;
let inFlight: Promise<string | null> | null = null;

/** 만료 여유 — 서버 왕복과 시계 오차를 흡수한다. */
const SKEW_MS = 60_000;

function decodeExpMs(token: string): number | null {
  // JWT payload 의 `exp` 만 읽는다 — **서명은 검증하지 않는다.** 이 값은 캐시 수명에만 쓰이고
  // 권한 판정에는 쓰이지 않는다(판정은 FastAPI 가 JWKS 로 한다).
  const part = token.split(".")[1];
  if (!part) return null;
  try {
    const json = JSON.parse(
      atob(part.replace(/-/g, "+").replace(/_/g, "/")),
    ) as unknown as { exp?: number };
    return typeof json.exp === "number" ? json.exp * 1000 : null;
  } catch {
    return null;
  }
}

async function fetchToken(): Promise<string | null> {
  const res = await fetch("/api/auth/token", { credentials: "include" });
  if (!res.ok) return null;
  const body = (await res.json()) as { token?: string };
  const token = body.token ?? null;
  if (token) {
    const expMs = decodeExpMs(token);
    // `exp` 를 못 읽으면 보수적으로 5분만 캐시한다.
    cached = { token, expiresAt: expMs ?? Date.now() + 5 * 60_000 };
  }
  return token;
}

/**
 * FastAPI 호출용 Bearer JWT 를 준다. 만료 1분 전까지 캐시를 재사용한다.
 *
 * ★동시 호출을 하나로 접는다 — 대시보드 첫 렌더에서 React Query 가 여러 쿼리를 동시에 띄우면
 * `/api/auth/token` 이 그 수만큼 나간다.
 */
export async function getAuthToken(): Promise<string | null> {
  if (cached && Date.now() < cached.expiresAt - SKEW_MS) return cached.token;
  if (inFlight) return inFlight;
  inFlight = fetchToken().finally(() => {
    inFlight = null;
  });
  return inFlight;
}

/** 로그아웃·계정 전환 시 호출 — 캐시된 JWT 가 남아 다음 사용자로 새지 않게 한다. */
export function clearAuthTokenCache(): void {
  cached = null;
  inFlight = null;
}

/**
 * 계정 삭제 — 인증 사용자를 지우고, 그 **전에** 서버가 라이브 세션·웹훅 시크릿을 닫는다.
 *
 * ★순서를 여기서 지키지 않는다. `lib/auth.ts` 의 `deleteUser.beforeDelete` 가
 * `DELETE /api/v1/auth/me` 를 부르고 **실패하면 삭제를 중단**한다(fail-closed).
 * 클라이언트가 순서를 지키는지에 「돈이 멈추는가」를 걸지 않기 위해서다.
 */
export async function deleteAccount(): Promise<{ error: { message?: string } | null }> {
  clearAuthTokenCache();
  const result = await deleteUser({});
  return { error: result.error ?? null };
}
