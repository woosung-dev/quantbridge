// `@/lib/auth-client` 의 수동 mock — `tests/setup.ts` 가 전역으로 물린다(ADR-034).
// ★종전에는 같은 내용의 `vi.mock("@clerk/nextjs", …)` 이 **26개 테스트 파일에 인라인 복붙**돼
//   있었다. 전부 「로그인된 사용자 + 토큰 하나」였다 — 26벌이 필요했던 것이 아니라 둘 자리가 없었다.
//
// 기본값을 바꾸고 싶은 테스트는 `authMockState` 를 직접 수정하고 `afterEach` 에서
// `resetAuthMock()` 을 불러라. 스파이(`getAuthToken` 등)는 `@/lib/auth-client` 에서
// 평소처럼 import 하면 이 파일의 것이 온다.

import { vi } from "vitest";

export interface AuthMockState {
  userId: string | null;
  name: string | null;
  email: string | null;
  isPending: boolean;
  token: string | null;
}

const DEFAULTS: AuthMockState = {
  userId: "user-1",
  name: "테스터",
  email: "test@example.com",
  isPending: false,
  token: "test-token",
};

export const authMockState: AuthMockState = { ...DEFAULTS };

export function resetAuthMock(): void {
  Object.assign(authMockState, DEFAULTS);
  getAuthToken.mockClear();
  clearAuthTokenCache.mockClear();
  signOut.mockClear();
  signIn.email.mockClear();
  signUp.email.mockClear();
}

export const getAuthToken = vi.fn(async (): Promise<string | null> => authMockState.token);
export const clearAuthTokenCache = vi.fn();
export const signOut = vi.fn(async () => ({ data: null, error: null }));
export const signIn = { email: vi.fn(async () => ({ data: null, error: null })) };
export const signUp = { email: vi.fn(async () => ({ data: null, error: null })) };

export function useSession() {
  const signedIn = authMockState.userId !== null;
  return {
    data: signedIn
      ? {
          user: {
            id: authMockState.userId,
            name: authMockState.name,
            email: authMockState.email,
          },
          session: { id: "session-1" },
        }
      : null,
    error: null,
    isPending: authMockState.isPending,
    isRefetching: false,
    refetch: vi.fn(),
  };
}

export const authClient = { useSession, signIn, signUp, signOut };
