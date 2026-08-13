"use client";

// Clerk 인증 컨텍스트 공통 훅 — `userId ?? "anon"` sentinel(LESSON-005) 보일러플레이트의 SSOT.
// uid 는 string primitive 라 queryKey factory 첫 인자로 그대로 사용 가능.
// getToken 은 queryKey 에 절대 넣지 않는다(H-2) — queryFn 모듈 팩토리 인자로만 전달.

import { useAuth } from "@clerk/nextjs";

/** 로그아웃/미인증 상태의 queryKey sentinel — 5개 feature hooks 에 중복 정의돼 있던 값. */
export const ANON_USER_ID = "anon";

export type TokenGetter = () => Promise<string | null>;

export interface AuthCtx {
  /** queryKey 용 안정 식별자 — `userId ?? ANON_USER_ID`. */
  uid: string;
  userId: string | null | undefined;
  isSignedIn: boolean | undefined;
  getToken: TokenGetter;
}

export function useAuthCtx(): AuthCtx {
  const { userId, isSignedIn, getToken } = useAuth();
  return { uid: userId ?? ANON_USER_ID, userId, isSignedIn, getToken };
}
