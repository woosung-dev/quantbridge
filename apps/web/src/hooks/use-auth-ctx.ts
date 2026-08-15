"use client";

// 인증 컨텍스트 공통 훅 — `userId ?? "anon"` sentinel(LESSON-005) 보일러플레이트의 SSOT.
// uid 는 string primitive 라 queryKey factory 첫 인자로 그대로 사용 가능.
// getToken 은 queryKey 에 절대 넣지 않는다(H-2) — queryFn 모듈 팩토리 인자로만 전달.
//
// ★2026-08-17 ADR-034 — 공급자가 Clerk 에서 Better Auth 로 바뀌었지만 **이 파일의 계약은
//   그대로다**. 앱 전체가 이 4필드만 소비하도록 모아 둔 덕에 교체가 이 한 파일에서 끝났다.

import { getAuthToken, useSession } from "@/lib/auth-client";

/** 로그아웃/미인증 상태의 queryKey sentinel — 5개 feature hooks 에 중복 정의돼 있던 값. */
export const ANON_USER_ID = "anon";

export type TokenGetter = () => Promise<string | null>;

export interface AuthCtx {
  /** queryKey 용 안정 식별자 — `userId ?? ANON_USER_ID`. */
  uid: string;
  userId: string | null | undefined;
  /** 로딩 중에는 `undefined` — 「아직 모른다」와 「로그아웃」을 구분한다. */
  isSignedIn: boolean | undefined;
  getToken: TokenGetter;
}

export function useAuthCtx(): AuthCtx {
  const { data, isPending } = useSession();
  const userId = data?.user?.id ?? null;
  return {
    uid: userId ?? ANON_USER_ID,
    userId,
    isSignedIn: isPending ? undefined : Boolean(data?.session),
    // 모듈 스코프 함수라 참조가 안정적이다 — H-1 ref 패턴이 매 렌더 갱신을 강요하지 않는다.
    getToken: getAuthToken,
  };
}
