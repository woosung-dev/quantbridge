"use client";

// 인증 컨텍스트 공통 훅 — `userId ?? "anon"` sentinel(LESSON-005) 보일러플레이트의 SSOT.
// uid 는 string primitive 라 queryKey factory 첫 인자로 그대로 사용 가능.
// getToken 은 queryKey 에 절대 넣지 않는다(H-2) — queryFn 모듈 팩토리 인자로만 전달.
//
// ★2026-08-17 ADR-034 — 공급자가 Clerk 에서 Better Auth 로 바뀌었지만 **이 파일의 계약은
//   그대로다**. 앱 전체가 이 4필드만 소비하도록 모아 둔 덕에 교체가 이 한 파일에서 끝났다.

import { useMemo } from "react";

import { useServerIdentity } from "@/components/providers/server-identity-provider";
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
  const serverUserId = useServerIdentity();
  // ★세션 조회가 끝나기 **전에는** SSR 이 준 id 를 쓴다([BL-786]).
  //   이 한 줄이 없으면 `uid` 가 `anon` → 진짜 id 로 한 번 바뀌고, queryKey 가 `uid` 로 시작하는
  //   모든 쿼리가 같은 URL 을 두 번 친다. 세션이 도착한 뒤에는 세션이 정본이다 — 로그아웃 직후
  //   낡은 SSR 값이 살아남으면 안 된다.
  const userId = isPending ? serverUserId : (data?.user?.id ?? null);
  const signedIn = Boolean(data?.session);
  // ★참조를 고정한다 — 이 훅은 화면 곳곳에서 불리고, 매 렌더 새 객체를 내면 그것을 dependency
  //   로 쓰는 소비자가 생겼을 때 조용히 루프가 된다(`rerender-dependencies`). 원시값 두 개만
  //   dep 로 둔다. `getToken` 은 모듈 스코프 함수라 이미 안정적이다.
  return useMemo(
    () => ({
      uid: userId ?? ANON_USER_ID,
      userId,
      isSignedIn: isPending ? undefined : signedIn,
      getToken: getAuthToken,
    }),
    [userId, isPending, signedIn],
  );
}
